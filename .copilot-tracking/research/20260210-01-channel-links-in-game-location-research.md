<!-- markdownlint-disable-file -->

# Task Research Notes: Discord Channel Links in Game Location Field

## Research Executed

### File Analysis

- services/bot/formatters/game_message.py (Lines 1-150)
  - Already supports `channel_id` parameter for voice channel display using `<#channel_id>` format (Line 150)
  - Voice Channel field displayed as: `<#987654321>`
  - Discord automatically renders this as clickable channel link
- frontend/src/components/GameForm.tsx (Lines 600-700)
  - Location field is TextField with multiline, 500 char max
  - Current implementation: Plain text entry, no validation
  - No channel-specific handling
- services/api/services/participant_resolver.py (Lines 1-200)
  - Implements `ParticipantResolver` for validating @mentions
  - Resolves Discord mention formats (`<@discord_id>`) and user-friendly format (`@username`)
  - Provides disambiguation for multiple matches
  - Returns structured validation errors with suggestions
- shared/discord/client.py (Line 392+)
  - `get_guild_channels()` fetches all channels for a guild
  - Returns list with id, name, type, etc.
  - Channel type 0 = text channel
  - Already used for channel sync operations
- services/api/routes/guilds.py (Line 208+)
  - `list_guild_channels()` endpoint returns active channels
  - Fetches channel names dynamically from Discord API
- frontend/src/pages/GuildConfig.tsx (Lines 175-300)
  - Uses Material-UI Autocomplete for role selection
  - Multi-select with chips showing role names
  - Demonstrates pattern for dropdown with API data

### Code Search Results

- Channel mention format in Discord embeds
  - `<#channel_id>` format already implemented (game_message.py Line 150)
  - Used for voice channel field in game announcements
- Autocomplete components in frontend
  - GuildConfig.tsx uses Autocomplete for role multi-select
  - Demonstrates pattern for dropdown with fetched options
- ParticipantResolver patterns
  - Validates mentions via Discord API search
  - Returns structured validation errors for disambiguation
  - Used in game creation for participant validation

### External Research

- #fetch:https://discord.com/developers/docs/reference#message-formatting
  - Discord channel mentions use format: `<#CHANNEL_ID>`
  - Example: `<#103735883630395392>`
  - Discord automatically renders as clickable link to channel
  - Works in message content and embed fields
  - No special permissions needed to create mentions
- #fetch:https://discord.com/developers/docs/resources/channel#get-channel
  - GET `/channels/{channel.id}` endpoint validates channel exists
  - Returns channel object with id, name, type, guild_id
  - Returns 404 if channel not found or bot lacks permissions
  - Channel types: 0=text, 2=voice, 4=category, etc.
  - Bot requires VIEW_CHANNEL permission to access

### Project Conventions

- Standards referenced: Python coding conventions, React/TypeScript patterns
- Instructions followed: Minimal code changes, preserve existing patterns
- Validation pattern: ParticipantResolver provides template for mention validation
- Frontend patterns: Autocomplete with chips for multi-select dropdowns

## Key Discoveries

### Discord Channel Mention Format

**Discord automatically creates clickable channel links** when text contains `<#channel_id>` format:

- Format: `<#1234567890>` where numbers are Discord channel snowflake ID
- Works in: message content, embed descriptions, embed field values
- Behavior: Discord renders as clickable link that navigates to channel
- Permission: Requires no special mention permissions
- Validation: User can only click if they have access to that channel

**Already Implemented in Project**:

- Voice Channel field uses this format (game_message.py Line 150)
- `format_channel_mention()` utility exists (shared/utils/discord.py)
- Pattern proven to work in production

### Current Game Location Implementation

**Backend**:

- `where` field stored as plain text (max 500 chars)
- No validation or special processing
- Passed directly to Discord embed formatter

**Frontend**:

- TextField with multiline entry
- No autocomplete or channel-specific handling
- Character limit validation only

**Discord Display**:

- Where field shows plain text in embed
- No automatic channel link detection
- User must manually type channel name

### Channel Validation Approaches

**Option 1: Validate Channel on Submit (Like Username Validation)**

_Pattern from ParticipantResolver_:

- Parse location text for patterns starting with '#'
- Extract channel name/ID after '#'
- Search guild channels via Discord API
- Return validation errors with disambiguation if needed
- Only validate when submitting game creation

_Implementation_:

1. Backend: Create `ChannelResolver` similar to `ParticipantResolver`
2. Parse `where` field for `#channel-name` patterns
3. Search Discord guild channels by name
4. If single match: Store as `#channel-name` (preserve user format)
5. If multiple matches: Return error with channel list for disambiguation
6. If no match: Return validation error
7. Format display: Backend converts to `<#channel_id>` for Discord embed

_Pros_:

- Validates actual channel existence in guild
- Provides disambiguation for ambiguous names
- Works with existing validation error patterns
- No frontend changes to form loading
- Backend-driven validation (consistent with existing patterns)

_Cons_:

- User doesn't see validation until form submission
- Manual typing prone to typos
- No guidance on available channels
- More server round-trips for validation

**Option 2: Channel Dropdown with Autocomplete**

_Pattern from GuildConfig Autocomplete_:

- Load guild channels when form opens
- Filter to show only text channels
- Provide Autocomplete with '#' trigger
- Auto-complete channel names as user types
- Immediate validation (only valid selections possible)

_Implementation_:

1. Frontend: Fetch channels on form load (existing endpoint: `/api/v1/guilds/{guild_id}/channels`)
2. Add Autocomplete component triggered by '#' in location field
3. Filter channels by user input after '#'
4. Display channel names with '#' prefix in dropdown
5. On selection: Insert channel name into location text
6. Backend: Parse location for channel mentions, convert to `<#id>` format for Discord

_Pros_:

- Immediate feedback (no validation errors on submit)
- Prevents typos and invalid channels
- User can see available channels
- Better UX (guided selection)
- Can allow mixing text + channel mentions

_Cons_:

- Additional frontend complexity
- Need to detect '#' trigger mid-text
- Must handle partial text + autocomplete
- More initial API calls
- Complex state management for mixed content

### Channel Name vs ID in Storage

**Storage Options**:

1. Store user input as-is (`#general`)
2. Store Discord channel ID (`1234567890`)
3. Store Discord mention format (`<#1234567890>`)

**Recommendation**: Store user input format, convert to mention on display

- Preserves what user typed
- Allows validation to change without data migration
- Backend converts to `<#id>` format when creating Discord embed
- If channel deleted/renamed, text still shows what user intended

### Existing Infrastructure

**Channel Data Already Available**:

- `GET /api/v1/guilds/{guild_id}/channels` endpoint exists
- Returns active channels (is_active=True)
- Fetches channel names dynamically from Discord
- Cached with Redis (performance optimized)

**Discord API Client**:

- `get_guild_channels()` fetches all guild channels
- `fetch_channel()` validates single channel exists
- Already handles permissions and errors
- Returns channel type, name, ID

**Validation Infrastructure**:

- ParticipantResolver pattern established
- Validation error response format defined
- Frontend handles validation errors with suggestions
- Backend returns structured error data

## Alternative Analysis and Evaluation

### Option 1: Backend Validation on Submit

**Description**:
Parse location field for channel references (text starting with '#') during game creation, validate against Discord guild channels, and return structured errors for disambiguation.

**Benefits**:

- Minimal frontend changes (reuses existing validation error display)
- Consistent with username validation pattern
- Backend-driven validation (single source of truth)
- No additional form load complexity

**Trade-offs**:

- User doesn't discover invalid channels until submit
- Multiple round-trips for disambiguation
- Manual typing prone to typos
- No visual guidance on available channels

**Alignment with Existing Patterns**:

- Matches ParticipantResolver validation approach
- Uses existing ValidationError response format
- Leverages existing `get_guild_channels()` method
- Fits transaction management patterns (validation in service layer)

**Implementation Complexity**: **Medium**

- Create ChannelResolver service (~200 lines, similar to ParticipantResolver)
- Add channel parsing logic to GameService.create_game
- Update frontend to display channel validation errors
- Add tests for channel resolution and disambiguation

**Complete Implementation Example**:

```python
# services/api/services/channel_resolver.py (new file)
class ChannelResolver:
    """Resolve channel mentions in location text."""

    def __init__(self, discord_client: DiscordAPIClient):
        self.discord_client = discord_client

    async def resolve_channel_mentions(
        self,
        location_text: str,
        guild_discord_id: str
    ) -> tuple[str, list[dict]]:
        """
        Resolve channel mentions in location text.

        Args:
            location_text: User input location text
            guild_discord_id: Discord guild ID

        Returns:
            Tuple of (resolved_text, validation_errors)
            resolved_text contains <#id> format for valid channels
        """
        # Find all #channel-name patterns
        pattern = r'#([\w-]+)'
        matches = re.finditer(pattern, location_text)

        channels = await self.discord_client.get_guild_channels(guild_discord_id)
        text_channels = {ch['name']: ch['id'] for ch in channels if ch.get('type') == 0}

        resolved = location_text
        errors = []

        for match in matches:
            channel_name = match.group(1)
            matching_ids = [
                ch_id for ch_name, ch_id in text_channels.items()
                if ch_name.lower() == channel_name.lower()
            ]

            if len(matching_ids) == 1:
                # Replace #channel-name with Discord mention format
                resolved = resolved.replace(
                    f'#{channel_name}',
                    f'<#{matching_ids[0]}>',
                    1
                )
            elif len(matching_ids) > 1:
                errors.append({
                    'input': f'#{channel_name}',
                    'reason': 'Multiple channels found',
                    'suggestions': [
                        {'id': ch_id, 'name': ch_name}
                        for ch_name, ch_id in text_channels.items()
                        if ch_name.lower() == channel_name.lower()
                    ]
                })
            else:
                errors.append({
                    'input': f'#{channel_name}',
                    'reason': 'Channel not found',
                    'suggestions': [
                        {'id': ch_id, 'name': ch_name}
                        for ch_name, ch_id in text_channels.items()
                        if channel_name.lower() in ch_name.lower()
                    ][:5]
                })

        return resolved, errors


# services/api/services/games.py (modifications)
async def create_game(
    self,
    game_data: game_schemas.GameCreateRequest,
    current_user: auth_schemas.CurrentUser,
    db: AsyncSession,
) -> game_model.GameSession:
    """Create new game with channel mention validation."""

    # ... existing code ...

    # Resolve channel mentions in location
    if game_data.where:
        channel_resolver = ChannelResolver(self.discord_client)
        resolved_location, channel_errors = await channel_resolver.resolve_channel_mentions(
            game_data.where,
            guild_config.guild_id  # Discord guild ID
        )

        if channel_errors:
            raise ValidationError(
                invalid_mentions=channel_errors,
                valid_participants=[]
            )

        game_data.where = resolved_location

    # ... rest of game creation ...
```

### Option 2: Frontend Autocomplete with '#' Trigger

**Description**:
Load guild channels when form opens, provide Autocomplete component that triggers on '#' character, allow users to select from dropdown or continue typing.

**Benefits**:

- Immediate feedback (no submission errors)
- Prevents invalid channel references
- Visual guidance on available channels
- Better UX (guided selection)
- Can mix plain text with channel mentions

**Trade-offs**:

- Significant frontend complexity
- Need sophisticated text parsing for '#' trigger
- More initial API calls on form load
- Complex state management
- Must handle edge cases (multiple '#', partial matches)

**Alignment with Existing Patterns**:

- Similar to GuildConfig.tsx Autocomplete pattern
- Uses existing `/guilds/{guild_id}/channels` endpoint
- Frontend-driven validation (immediate feedback)
- Matches Material-UI component patterns

**Implementation Complexity**: **High**

- Create ChannelAutocomplete component (~300 lines)
- Implement '#' trigger detection in TextField
- Handle cursor position and text insertion
- Manage channel loading and caching
- Update GameForm to integrate component
- Handle mixed content (text + mentions)
- Add comprehensive tests

**Complete Implementation Example**:

```tsx
// frontend/src/components/ChannelAutocomplete.tsx (new file)
interface ChannelAutocompleteProps {
  value: string;
  onChange: (value: string) => void;
  guildId: string;
  disabled?: boolean;
}

export const ChannelAutocomplete: React.FC<ChannelAutocompleteProps> = ({
  value,
  onChange,
  guildId,
  disabled,
}) => {
  const [channels, setChannels] = useState<Channel[]>([]);
  const [showDropdown, setShowDropdown] = useState(false);
  const [cursorPosition, setCursorPosition] = useState(0);
  const [filterText, setFilterText] = useState('');
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const fetchChannels = async () => {
      const response = await apiClient.get(`/api/v1/guilds/${guildId}/channels`);
      setChannels(response.data);
    };
    fetchChannels();
  }, [guildId]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value;
    const position = e.target.selectionStart || 0;

    onChange(newValue);
    setCursorPosition(position);

    // Detect '#' trigger
    const textBeforeCursor = newValue.substring(0, position);
    const lastHashIndex = textBeforeCursor.lastIndexOf('#');

    if (lastHashIndex !== -1 && lastHashIndex === position - 1) {
      // Just typed '#'
      setShowDropdown(true);
      setFilterText('');
    } else if (lastHashIndex !== -1 && showDropdown) {
      // Continue filtering after '#'
      const filter = textBeforeCursor.substring(lastHashIndex + 1);
      setFilterText(filter);
    } else {
      setShowDropdown(false);
    }
  };

  const handleChannelSelect = (channel: Channel) => {
    const textBeforeCursor = value.substring(0, cursorPosition);
    const textAfterCursor = value.substring(cursorPosition);
    const lastHashIndex = textBeforeCursor.lastIndexOf('#');

    // Replace #filter with #channel-name
    const newValue =
      value.substring(0, lastHashIndex) + `#${channel.channel_name}` + textAfterCursor;

    onChange(newValue);
    setShowDropdown(false);

    // Restore focus
    setTimeout(() => {
      inputRef.current?.focus();
    }, 0);
  };

  const filteredChannels = channels.filter((ch) =>
    ch.channel_name.toLowerCase().includes(filterText.toLowerCase())
  );

  return (
    <Box sx={{ position: 'relative' }}>
      <TextField
        inputRef={inputRef}
        value={value}
        onChange={handleChange}
        fullWidth
        multiline
        rows={2}
        label="Location"
        helperText="Type # to mention a channel"
        disabled={disabled}
      />
      {showDropdown && filteredChannels.length > 0 && (
        <Paper
          sx={{
            position: 'absolute',
            zIndex: 1000,
            width: '100%',
            maxHeight: 200,
            overflow: 'auto',
            mt: 1,
          }}
        >
          <List>
            {filteredChannels.map((channel) => (
              <ListItem key={channel.id} button onClick={() => handleChannelSelect(channel)}>
                <ListItemText primary={`# ${channel.channel_name}`} />
              </ListItem>
            ))}
          </List>
        </Paper>
      )}
    </Box>
  );
};
```

### Comparison Matrix

| Criterion               | Option 1: Backend Validation   | Option 2: Frontend Autocomplete   |
| ----------------------- | ------------------------------ | --------------------------------- |
| **User Experience**     | ⚠️ Errors on submit            | ✅ Immediate feedback             |
| **Development Time**    | ✅ 3-4 hours                   | ⚠️ 8-10 hours                     |
| **Code Complexity**     | ✅ Medium (~300 lines)         | ⚠️ High (~500 lines)              |
| **Pattern Consistency** | ✅ Matches username validation | ⚠️ New pattern                    |
| **Maintenance**         | ✅ Backend-only                | ⚠️ Frontend + Backend             |
| **Testing Effort**      | ✅ Standard service tests      | ⚠️ Complex UI interactions        |
| **Performance**         | ✅ Validation on demand        | ⚠️ Channels load on form open     |
| **Edge Cases**          | ✅ Simple text parsing         | ⚠️ Cursor position, mixed content |
| **Accessibility**       | ✅ Standard form               | ⚠️ Custom dropdown behavior       |

## Recommended Approach

**Selected**: **Option 1 - Backend Validation on Submit**

### Reasoning

1. **Consistency with Existing Patterns**: Matches the established participant validation approach using ParticipantResolver
2. **Lower Implementation Risk**: Backend-only changes with well-understood validation patterns
3. **Faster Delivery**: Can be completed in one development session vs multi-day effort
4. **Maintainability**: Single validation location in backend, no complex frontend state
5. **Progressive Enhancement**: Can add frontend autocomplete later if users request it

### Implementation Steps

**Phase 1: Backend Channel Resolver** (2 hours)

1. Create `ChannelResolver` service modeled after `ParticipantResolver`
2. Implement channel name parsing for `#channel-name` patterns
3. Add Discord API channel search with disambiguation
4. Return structured validation errors matching existing format

**Phase 2: Game Service Integration** (1 hour)

1. Add channel resolution to `GameService.create_game()`
2. Inject ChannelResolver dependency
3. Validate `where` field before game creation
4. Raise ValidationError with channel suggestions

**Phase 3: Frontend Error Display** (30 minutes)

1. Update GameForm to display channel validation errors
2. Reuse existing validation error component
3. Show channel suggestions with format hints

**Phase 4: Testing** (1 hour)

1. Unit tests for ChannelResolver
2. Integration tests for game creation with channel mentions
3. E2E tests verifying Discord embed displays clickable links

**Total Estimated Effort**: 4-5 hours

### Success Criteria

- Users can type `#general` in location field
- Backend validates channel exists in guild
- Returns error if channel not found with similar suggestions
- Returns error if multiple matches with disambiguation list
- Discord embed displays as clickable `<#channel_id>` link
- Existing plain text locations continue to work
- All tests pass

### Future Enhancement Path

If users request better UX, can add Option 2 (autocomplete) as enhancement:

- Foundation already in place (channel resolver backend)
- Frontend adds autocomplete as progressive enhancement
- Backend validation remains as safety net
- Can be scoped as separate feature request
