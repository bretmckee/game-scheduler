<!-- markdownlint-disable-file -->
# Task Research Notes: Discord User Validation Timing Options

## Research Executed

### File Analysis
- `frontend/src/components/EditableParticipantList.tsx`
  - Current implementation uses 500ms debounced validation as user types
  - `handleMentionChange` sets timer on each keystroke
  - `validateMention` calls API endpoint after debounce period
  - Visual feedback with loading spinner, checkmark, and error states
- `.copilot-tracking/research/20251114-discord-game-scheduling-system-research.md`
  - Original research mentioned "Validate @mentions on submit, show errors with disambiguation UI"
  - Indicated validation happens during game save
- `.copilot-tracking/details/20251114-discord-game-scheduling-system-details.md`
  - Specified "Real-time validation with 500ms debounce per field"
  - Noted validation is "not blocking, just visual feedback"

### Current Implementation Details

**Implemented Approach: Real-time Validation (As-You-Type with Debounce)**

Located in `EditableParticipantList.tsx` (lines 51-122):
```typescript
const validateMention = useCallback(
  async (id: string, mention: string) => {
    // ... validation logic via API call
  },
  [guildId, onChange]
);

const handleMentionChange = (id: string, newMention: string) => {
  // Clear validation state immediately
  onChange(
    participantsRef.current.map((p) =>
      p.id === id ? { ...p, mention: newMention, isValid: null, validationError: undefined } : p
    )
  );

  // Debounce validation
  const timer = validationTimers.get(id);
  if (timer) {
    clearTimeout(timer);
  }

  const newTimer = setTimeout(() => {
    validateMention(id, newMention);
  }, 500);

  const newTimers = new Map(validationTimers);
  newTimers.set(id, newTimer);
  setValidationTimers(newTimers);
};
```

**Backend Endpoint**: `POST /api/v1/guilds/{guildId}/validate-mention`
- Validates mention exists in guild
- Returns `{ valid: true }` or `{ valid: false, error: "message" }`
- Rate limited to 10 requests/second per user
- Validation-only (does not resolve user details)

## Key Discoveries

### Implementation Tension

Original research suggested **validation on submit** with disambiguation UI, but implementation chose **real-time validation** with debounce. This creates a hybrid approach:

1. **Visual validation** happens as user types (after 500ms pause)
2. **Actual resolution** happens on form submission
3. User gets early feedback but validation is not blocking

### Trade-offs Identified

**Current Approach Benefits:**
- Immediate user feedback reduces submission errors
- Users know about problems before clicking submit
- Visual indicators (spinner, checkmark, X) guide user
- Debounce prevents excessive API calls

**Current Approach Drawbacks:**
- Many API calls during typing (every 500ms pause)
- Rate limiting concerns with multiple participants
- Network overhead for validation-only checks
- Validation happens twice (preview + final resolution on submit)
- User might fix mentions that would resolve correctly on submit
- Doesn't handle disambiguation (multiple matches) well in real-time

## Alternative Validation Timing Approaches

### Option 1: Validation on Blur (Field Exit)

**How It Works:**
- User types @mention in field
- No validation until user clicks away (onBlur event)
- API call made when field loses focus
- Visual feedback updates after blur

**Implementation Pattern:**
```typescript
const handleBlur = (id: string, mention: string) => {
  if (mention.trim()) {
    validateMention(id, mention);
  }
};

<TextField
  onBlur={(e) => handleBlur(participant.id, e.target.value)}
/>
```

**Benefits:**
- Significantly fewer API calls (only when leaving field)
- User completes thought before validation interrupts
- Natural validation timing that matches form conventions
- Still provides early feedback before submission
- Reduces server load and rate limiting concerns

**Drawbacks:**
- No feedback during typing
- User must explicitly leave field to see validation
- Might not notice validation until clicking submit
- Less "modern" feel than real-time validation

**Best For:**
- Forms with many participants
- Rate-limited APIs
- Users familiar with traditional form validation

### Option 2: Validation on Form Submit Only

**How It Works:**
- User types all @mentions without validation
- No API calls during form entry
- All validation happens when clicking "Create Game" or "Update Game"
- Backend performs full validation and returns errors
- Form displays errors with disambiguation UI

**Implementation Pattern:**
```typescript
const handleSubmit = async (formData: GameFormData) => {
  try {
    await apiClient.post('/api/v1/games', {
      ...formData,
      participants: participants.map(p => ({ mention: p.mention }))
    });
  } catch (error) {
    if (error.response?.status === 422) {
      // Display validation errors with suggestions
      setValidationErrors(error.response.data);
    }
  }
};
```

**Benefits:**
- Zero API calls during form entry
- No rate limiting concerns
- Backend handles all validation logic (single source of truth)
- Better for disambiguation (can show all matches at once)
- Form preserves data on error for easy correction
- Simpler frontend code (no debounce timers, loading states)
- Matches original research intent

**Drawbacks:**
- No early feedback during entry
- User discovers problems only after clicking submit
- May require multiple submit attempts to fix all mentions
- Less immediate gratification
- Can feel slower if many mentions are invalid

**Best For:**
- Rate-limited APIs or high server load
- Complex validation requiring multiple checks
- Forms with disambiguation requirements
- Traditional form-based workflows

### Option 3: Hybrid - Debounced Validation with Longer Delay

**How It Works:**
- Same as current implementation but with 2-3 second debounce
- User types mention
- Validation fires after longer pause (e.g., 2000ms)
- Reduces API calls while maintaining real-time feel

**Implementation Pattern:**
```typescript
const newTimer = setTimeout(() => {
  validateMention(id, newMention);
}, 2000); // Increased from 500ms
```

**Benefits:**
- Balances real-time feedback with API efficiency
- Users who pause briefly don't trigger validation
- Reduces API calls by ~75% compared to 500ms
- Still provides preview feedback before submit

**Drawbacks:**
- Slower feedback feels less responsive
- User might finish typing multiple mentions before any validate
- Still makes API calls for previews
- Doesn't solve fundamental duplication issue

**Best For:**
- Gradual improvement without major refactoring
- Teams wanting to reduce load without UX overhaul

### Option 4: Batch Validation on Command

**How It Works:**
- User types all @mentions
- "Validate All" button next to "Add Participant"
- Batch validates all mentions in single API call
- Visual feedback after batch validation

**Implementation Pattern:**
```typescript
const validateAllParticipants = async () => {
  setIsValidating(true);
  try {
    const response = await apiClient.post(
      `/api/v1/guilds/${guildId}/validate-mentions-batch`,
      { mentions: participants.map(p => p.mention) }
    );
    // Update all validation states
    updateParticipantsWithValidation(response.data);
  } finally {
    setIsValidating(false);
  }
};
```

**Benefits:**
- Single API call for all mentions
- User controls when validation happens
- Efficient for multiple participants
- Clear validation state (all or none)

**Drawbacks:**
- Requires new batch endpoint
- Extra user action needed
- Users might forget to validate
- Feels less automated

**Best For:**
- Forms with many participants (5+)
- Power users who understand batch operations
- APIs with strict rate limits

### Option 5: Smart Validation (Skip Known Valid Patterns)

**How It Works:**
- Validate on blur (Option 1)
- Skip validation for exact Discord ID format: `<@123456789>`
- Only validate usernames that need resolution
- Reduces unnecessary API calls

**Implementation Pattern:**
```typescript
const needsValidation = (mention: string): boolean => {
  // Discord ID format <@123456789> is always valid
  return !/^<@\d+>$/.test(mention);
};

const handleBlur = (id: string, mention: string) => {
  if (mention.trim() && needsValidation(mention)) {
    validateMention(id, mention);
  } else if (!needsValidation(mention)) {
    // Mark as valid without API call
    updateParticipantValidation(id, true);
  }
};
```

**Benefits:**
- Combines blur timing with smart skipping
- Reduces API calls for known-valid formats
- Respects users who paste Discord IDs
- Still validates ambiguous usernames

**Drawbacks:**
- More complex logic
- Requires understanding Discord ID format
- Still makes calls for username validation

**Best For:**
- Users who frequently use Discord IDs
- Mixed usage of IDs and usernames

## Recommended Approach

**Option 2: Validation on Form Submit Only**

### Rationale

1. **Aligns with Original Research**: Research notes stated "Validate @mentions on submit, show errors with disambiguation UI"

2. **Eliminates Redundant Validation**: Current approach validates twice:
   - Preview validation during typing
   - Final resolution on submit

3. **Better Disambiguation Support**: Submit-time validation can show all matches with clickable suggestions, which is difficult in real-time UI

4. **Reduces Server Load**: Zero API calls during form entry, all validation happens once

5. **Preserves Form Data**: Error responses preserve all form data for easy correction

6. **Simpler Implementation**: No debounce timers, loading states, or inline validation state management

7. **Single Source of Truth**: Backend handles all validation logic consistently

### Implementation Guidance

**Frontend Changes:**
1. Remove validation endpoint calls from EditableParticipantList
2. Remove validation state (isValid, validationError, loading spinner)
3. Simplify ParticipantInput interface to just id, mention, preFillPosition
4. Display validation errors from API response after submit
5. Add disambiguation UI for multiple matches (clickable suggestions)

**Backend Changes:**
1. Enhance game creation error response with detailed validation errors
2. Return suggestions for ambiguous mentions
3. Include all valid participants and all errors in response
4. Format errors for easy display: `{ input, reason, suggestions[] }`

**User Experience:**
1. User enters all participants without interruption
2. Clicks "Create Game" or "Update Game"
3. If validation fails, form shows errors with suggestions
4. User clicks suggestion chips to replace invalid mentions
5. Form preserves all other data, user clicks submit again
6. Success on second attempt

### Migration Path

**Phase 1 - Quick Win (Option 3):**
- Increase debounce from 500ms to 2000ms
- Reduces API calls by ~75% with minimal code change
- Buys time for larger refactor

**Phase 2 - Full Implementation (Option 2):**
- Remove real-time validation from EditableParticipantList
- Enhance backend validation response format
- Build disambiguation UI component
- Update form error handling

## Implementation Details

### Current Code to Remove

```typescript
// Remove from EditableParticipantList.tsx
const [validationTimers, setValidationTimers] = useState<Map<string, ReturnType<typeof setTimeout>>>(new Map());
const validateMention = useCallback(/* ... */);
const handleMentionChange = (id: string, newMention: string) => {
  // Remove debounce timer logic
  // Remove validation API call
};
```

### New Submit-Time Validation

```typescript
// In CreateGame.tsx / EditGame.tsx
const handleSubmit = async (formData: GameFormData) => {
  try {
    const response = await apiClient.post('/api/v1/games', {
      title: formData.title,
      // ... other fields
      participants: formData.participants.map(p => ({
        mention: p.mention,
        pre_filled_position: p.preFillPosition
      }))
    });
    navigate(`/games/${response.data.game_id}`);
  } catch (error) {
    if (error.response?.status === 422 && error.response.data.invalid_mentions) {
      // Show disambiguation UI
      setValidationErrors(error.response.data.invalid_mentions);
    }
  }
};
```

### Backend Response Format

```python
# Enhanced error response
{
  "error": "invalid_mentions",
  "invalid_mentions": [
    {
      "input": "@john",
      "reason": "Multiple matches found",
      "suggestions": [
        {"discord_id": "123", "username": "john123", "display_name": "John"},
        {"discord_id": "456", "username": "johnny", "display_name": "Johnny"}
      ]
    },
    {
      "input": "@missing",
      "reason": "User not found in guild",
      "suggestions": []
    }
  ],
  "valid_participants": ["@alice", "@bob"]
}
```

## Success Criteria

- Users enter mentions without interruption
- All validation errors shown after submit with clear messages
- Disambiguation UI allows easy selection of correct user
- Form preserves all data on validation error
- Second submit succeeds after corrections
- Zero validation API calls during form entry
- Backend handles all validation consistently
