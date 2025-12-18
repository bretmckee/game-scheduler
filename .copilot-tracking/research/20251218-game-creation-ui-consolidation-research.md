<!-- markdownlint-disable-file -->
# Task Research Notes: Game Creation UI Consolidation

## Research Executed

### File Analysis
- frontend/src/pages/CreateGame.tsx
  - Current implementation uses URL param `guildId` to determine server context
  - Template dropdown rendered outside GameForm component (lines 177-195)
  - Template selection triggers auto-population of form with template defaults
  - Uses `getTemplates(guildId)` API call to fetch templates per server
  - Auto-selects default template or first template on load
  - Navigation entry point: `/guilds/:guildId/games/new`

- frontend/src/components/GameForm.tsx
  - Pure form component with no server/template selection logic
  - Accepts `guildId`, `channels`, and `initialData` as props
  - Channel dropdown is required (lines 409-421)
  - Currently displays single channel from selected template
  - Form includes all game fields: title, description, location, date/time, duration, reminders, max players, participants
  - Supports validation error display and correction suggestions

- frontend/src/pages/MyGames.tsx
  - Entry point for game creation flow
  - Implements smart navigation logic (lines 125-132):
    - Single server → navigate directly to `/guilds/{guildId}/games/new`
    - Multiple servers → open `ServerSelectionDialog`
  - Fetches guilds on mount and filters by template access
  - Uses `canUserCreateGames` utility to check permissions

- frontend/src/components/ServerSelectionDialog.tsx
  - Reusable dialog for server selection
  - Accepts: `open`, `onClose`, `guilds`, `onSelect` props
  - Simple list-based interface
  - Currently used for multi-server game creation flow

### Code Search Results
- Server selection pattern
  - MyGames component already implements conditional server selection
  - ServerSelectionDialog is standalone, reusable component
  - Pattern: check guild count → auto-select or prompt user

- Template loading pattern
  - Templates loaded per-guild via `getTemplates(guildId)` API
  - API endpoint: `/api/v1/guilds/{guildId}/templates`
  - Response includes full template data with channel info

### External Research
- #file:.github/instructions/reactjs.instructions.md
  - Use functional components with hooks
  - Implement component composition over inheritance
  - Keep components small and focused on single concern
  - Use TypeScript interfaces for props
  - Proper state management with useState for local state

### Project Conventions
- Standards referenced: ReactJS instructions, TypeScript 5/ES2022 guidelines
- Instructions followed: Component composition, hooks patterns, MUI design system
- Existing patterns: Dropdown selects with FormControl/InputLabel/Select from MUI
- Navigation: React Router v6 with useNavigate hook

## Key Discoveries

### Project Structure
The game creation flow is split across three layers:
1. **Entry point** (MyGames.tsx) - Handles server count logic and initial navigation
2. **Template selection** (CreateGame.tsx) - Loads templates and manages template state
3. **Form rendering** (GameForm.tsx) - Pure form component with field inputs

Current routing uses guild-specific URLs: `/guilds/:guildId/games/new`

### Implementation Patterns

**Server Selection Logic** (MyGames.tsx lines 125-132):
```typescript
const handleCreateGame = () => {
  const availableGuilds = guilds.filter((guild) => guildsWithTemplates.has(guild.id));

  if (availableGuilds.length === 1 && availableGuilds[0]) {
    navigate(`/guilds/${availableGuilds[0].id}/games/new`);
  } else {
    setServerDialogOpen(true);
  }
};
```

**Template Loading** (CreateGame.tsx lines 62-82):
```typescript
useEffect(() => {
  const fetchData = async () => {
    if (!guildId) return;

    try {
      setLoading(true);
      const templatesResponse = await getTemplates(guildId);
      setTemplates(templatesResponse);

      // Auto-select default template
      const defaultTemplate = templatesResponse.find((t) => t.is_default);
      if (defaultTemplate) {
        setSelectedTemplate(defaultTemplate);
      } else if (templatesResponse.length > 0) {
        setSelectedTemplate(templatesResponse[0]!);
      }
    } catch (err: unknown) {
      console.error('Failed to fetch data:', err);
      setError(
        (err as any).response?.data?.detail || 'Failed to load server data. Please try again.'
      );
    } finally {
      setLoading(false);
    }
  };

  fetchData();
}, [guildId]);
```

**Template Dropdown Rendering** (CreateGame.tsx lines 177-195):
```typescript
<Box sx={{ mb: 3 }}>
  <FormControl fullWidth>
    <InputLabel>Game Template</InputLabel>
    <Select
      value={selectedTemplate?.id || ''}
      onChange={(e) => {
        const template = templates.find((t) => t.id === e.target.value);
        setSelectedTemplate(template || null);
      }}
      label="Game Template"
    >
      {templates.map((template) => (
        <MenuItem key={template.id} value={template.id}>
          {template.name}
          {template.is_default && ' (Default)'}
        </MenuItem>
      ))}
    </Select>
  </FormControl>
  {selectedTemplate?.description && (
    <Typography variant="body2" color="text.secondary" sx={{ mt: 1 }}>
      {selectedTemplate.description}
    </Typography>
  )}
</Box>
```

### Complete Examples

**TypeScript Interfaces** (types/index.ts):
```typescript
export interface Guild {
  id: string;
  guild_name: string;
  created_at: string;
  updated_at: string;
}

export interface GameTemplate {
  id: string;
  guild_id: string;
  name: string;
  description: string | null;
  order: number;
  is_default: boolean;
  channel_id: string;
  channel_name: string;
  notify_role_ids: string[] | null;
  allowed_player_role_ids: string[] | null;
  allowed_host_role_ids: string[] | null;
  max_players: number | null;
  expected_duration_minutes: number | null;
  reminder_minutes: number[] | null;
  where: string | null;
  signup_instructions: string | null;
  created_at: string;
  updated_at: string;
}
```

**GameForm Props** (GameForm.tsx lines 87-104):
```typescript
interface GameFormProps {
  mode: 'create' | 'edit';
  initialData?: Partial<GameSession>;
  guildId: string;
  channels: Channel[];
  onSubmit: (formData: GameFormData) => Promise<void>;
  onCancel: () => void;
  validationErrors?: Array<{
    input: string;
    reason: string;
    suggestions: Array<{
      discordId: string;
      username: string;
      displayName: string;
    }>;
  }> | null;
  validParticipants?: string[] | null;
  onValidationErrorClick?: (originalInput: string, newUsername: string) => void;
}
```

### API and Schema Documentation

**Template API** (api/templates.ts):
- `getTemplates(guildId: string): Promise<GameTemplate[]>` - Fetch templates for specific guild
- Endpoint: `GET /api/v1/guilds/{guildId}/templates`
- Returns array of templates sorted by order with default first

**Current Flow APIs**:
1. MyGames fetches: `GET /api/v1/games` and `GET /api/v1/guilds`
2. CreateGame fetches: `GET /api/v1/guilds/{guildId}/templates`
3. Form submits: `POST /api/v1/games` with template_id

### Configuration Examples

**Current Route Configuration** (App.tsx line 55):
```typescript
<Route path="/guilds/:guildId/games/new" element={<CreateGame />} />
```

**MUI FormControl Pattern**:
```typescript
<FormControl fullWidth margin="normal" required>
  <InputLabel>Channel</InputLabel>
  <Select
    value={formData.channelId}
    onChange={handleSelectChange}
    label="Channel"
    disabled={loading}
  >
    {channels.map((channel) => (
      <MenuItem key={channel.id} value={channel.id}>
        {channel.channel_name}
      </MenuItem>
    ))}
  </Select>
</FormControl>
```

### Technical Requirements

**Current Requirements**:
- Server selection must happen before template selection (templates are guild-specific)
- Template selection pre-populates form fields with defaults
- Channel is locked to template's channel (no user selection needed)
- Auto-select behavior: single server → auto-select, single template → auto-select default or first
- Form validation must handle participant mentions and field requirements

**State Dependencies**:
- Guild selection → Template loading
- Template selection → Form pre-population
- Templates filtered by user's host role permissions

## Recommended Approach

### Consolidate All Selection Logic into Single Page

Move server selection and template selection into the GameForm component or a new unified CreateGame page that doesn't require pre-selected guildId in URL.

**Benefits**:
- Single page for entire game creation flow
- No intermediate navigation steps
- Better UX with all context visible on one screen
- Simplified routing (no guild-specific URL needed)
- Maintains auto-selection behavior for single server/template cases

**Implementation Strategy**:

1. **Modify Route**: Change from `/guilds/:guildId/games/new` to `/games/new`
2. **Enhance GameForm**: Add optional server and template dropdowns at top
3. **State Management**:
   - Load all user's guilds with template access
   - Load templates when guild selected
   - Pre-populate form when template selected
4. **Auto-selection Logic**:
   - If 1 accessible guild → auto-select and hide dropdown
   - If 1 template in selected guild → auto-select default/first
   - Show dropdowns only when multiple options exist
5. **Navigation Update**: MyGames "Create Game" button navigates to `/games/new`

**Component Hierarchy**:
```
CreateGame (Page)
├── Server Dropdown (conditional: show only if multiple servers)
├── Template Dropdown (conditional: show after server selected)
│   └── Template Description (show when template selected)
└── GameForm (show when template selected)
    ├── All existing fields
    └── Submit handlers unchanged
```

## Implementation Guidance

### Objectives
- Consolidate game creation into single unified page without guild-based routing
- Move template selection into form component for better cohesion
- Add server selection dropdown with auto-population for single-server users
- Maintain all existing validation, pre-population, and submission logic
- Preserve auto-selection behavior for improved UX

### Key Tasks

1. **Update Routing** (App.tsx)
   - Change route from `/guilds/:guildId/games/new` to `/games/new`
   - Remove guildId param dependency

2. **Refactor CreateGame Component** (CreateGame.tsx)
   - Remove URL param extraction for guildId
   - Add state for guilds list and selected guild
   - Load guilds on mount (reuse MyGames pattern)
   - Add server dropdown above template dropdown
   - Implement guild selection handler that loads templates
   - Hide server dropdown if only 1 accessible guild (auto-select)
   - Keep template dropdown logic (already implemented)
   - Pass selectedGuild.id to GameForm as guildId

3. **Update MyGames Navigation** (MyGames.tsx)
   - Change "Create Game" button to navigate to `/games/new`
   - Remove server count checking and ServerSelectionDialog
   - Simplify to single navigation: `navigate('/games/new')`

4. **Alternative: Move Selection into GameForm** (GameForm.tsx)
   - Add optional `guilds` prop for server selection
   - Add optional `onGuildChange` callback
   - Add optional `templates` prop or load internally
   - Render server dropdown at top if guilds provided
   - Render template dropdown after server selection
   - Keep all existing form fields below

5. **Update Tests**
   - Modify CreateGame tests for new route
   - Update MyGames tests for simplified navigation
   - Add tests for server dropdown behavior
   - Test auto-selection scenarios

### Dependencies
- No new dependencies required
- Uses existing API endpoints
- Reuses existing components and patterns
- Leverages MUI FormControl/Select pattern

### Success Criteria
- User can access game creation from `/games/new` route
- Server dropdown appears with user's accessible guilds
- Single server users see pre-selected server (dropdown hidden or disabled)
- Template dropdown loads after server selection
- Single template auto-selects (default first)
- All form fields pre-populate from selected template
- Form validation and submission work unchanged
- Navigation from "Create Game" button simplified
- No loss of existing functionality
