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

- frontend/src/components/GameCard.tsx (Summary Card - UPDATED December 2025)
  - **Layout Structure** (matching recent UI consolidation):
    1. Host with avatar at top (32x32 avatar)
    2. Title with status chip on same line
    3. Description (truncated to 200 chars)
    4. Horizontal flex row with: When, Where (if present), Players (X/N format), Duration (if present)
    5. View Details button
  - **Key Design Elements**:
    - Avatar uses MUI Avatar component with fallback to first letter
    - Host displays as "Host: **display_name**" in subtitle2 variant
    - Info fields in compact horizontal layout with 2-column gap spacing
    - Bold labels followed by values: "When:", "Where:", "Players:", "Duration:"
    - Duration formatted as "Xh Ym" or "Xh" or "Ym"
    - Players count shows "participantCount/maxPlayers" format

- frontend/src/pages/GameDetails.tsx (Details Page - UPDATED December 2025)
  - **Layout Structure** (matching recent UI consolidation):
    1. Title with status chip
    2. Description
    3. "Game Details" section header
    4. Host with avatar (40x40 avatar, larger than summary card)
    5. When with inline calendar download button (for host/participants)
    6. Duration and Reminders on same line with 3-column gap spacing
    7. Where (physical location if provided)
    8. Location (guild_name # channel_name) - NEW: shows Discord server context
    9. Signup Instructions (host-only, boxed with info.light background)
    10. Participants heading with count "(X/N)" format
    11. ParticipantList component
    12. Action buttons
  - **Key Design Elements**:
    - Host avatar 40x40 (vs 32x32 in summary card)
    - Calendar download button as IconButton with DownloadIcon next to When
    - Duration and Reminders use body2 variant in horizontal flex
    - guild_name field now available in GameSession interface
    - Signup instructions only visible to host (conditional rendering)
    - Participants heading includes count in parentheses

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

**Recent UI Consolidation Changes (December 2025)**:
- GameCard (summary) and GameDetails (details page) now follow unified layout pattern
- Host with avatar appears at top of both displays
- Players count uses consistent "X/N" format across all views
- GameDetails added guild_name field to show server context ("Server Name # channel_name")
- Calendar download functionality integrated as inline IconButton next to "When" field
- Duration and Reminders consolidated on same line with horizontal spacing
- Signup instructions moved to boxed section (host-only visibility)
- Avatar sizes: 32x32 in GameCard, 40x40 in GameDetails
- Typography: body1 (fontSize 1.1rem) for main details, body2 for secondary info

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

**GameCard Layout** (Updated December 2025):
```typescript
<Card sx={{ mb: 2 }}>
  <CardContent>
    {/* Host with Avatar - Top of Card */}
    {game.host && game.host.display_name && (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <Avatar
          src={game.host.avatar_url || undefined}
          alt={game.host.display_name}
          sx={{ width: 32, height: 32 }}
        >
          {!game.host.avatar_url && game.host.display_name[0]}
        </Avatar>
        <Typography variant="subtitle2" color="text.secondary">
          Host: <strong>{game.host.display_name}</strong>
        </Typography>
      </Box>
    )}

    {/* Title and Status */}
    <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
      <Typography variant="h6" component="div">
        {game.title}
      </Typography>
      <Chip label={game.status} color={getStatusColor(game.status)} size="small" />
    </Box>

    {/* Description */}
    <Typography variant="body2" color="text.secondary" sx={{ mb: 1 }}>
      {truncateDescription(game.description, 200)}
    </Typography>

    {/* Info Row - Horizontal Flex */}
    <Box sx={{ display: 'flex', gap: 2, flexWrap: 'wrap', mb: 1 }}>
      <Typography variant="body2">
        <strong>When:</strong> {formatDateTime(game.scheduled_at)}
      </Typography>
      {game.where && (
        <Typography variant="body2">
          <strong>Where:</strong> {game.where}
        </Typography>
      )}
      <Typography variant="body2">
        <strong>Players:</strong> {participantCount}/{maxPlayers}
      </Typography>
      {game.expected_duration_minutes && (
        <Typography variant="body2">
          <strong>Duration:</strong> {formatDuration(game.expected_duration_minutes)}
        </Typography>
      )}
    </Box>
  </CardContent>
</Card>
```

**GameDetails Layout** (Updated December 2025):
```typescript
<Paper elevation={3} sx={{ p: 4 }}>
  {/* Title and Status */}
  <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 2 }}>
    <Typography variant="h4" component="h1">
      {game.title}
    </Typography>
    <Chip label={game.status} color={getStatusColor(game.status)} size="medium" />
  </Box>

  {/* Description */}
  <Typography variant="body1" paragraph>
    {game.description}
  </Typography>

  <Divider sx={{ my: 3 }} />

  {/* Game Details Section */}
  <Box sx={{ mb: 3 }}>
    <Typography variant="h6" gutterBottom>
      Game Details
    </Typography>

    {/* Host with Avatar */}
    {game.host && game.host.display_name && (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 2 }}>
        <Avatar
          src={game.host.avatar_url || undefined}
          alt={game.host.display_name}
          sx={{ width: 40, height: 40 }}
        >
          {!game.host.avatar_url && game.host.display_name[0]}
        </Avatar>
        <Typography variant="body1" sx={{ fontSize: '1.1rem' }}>
          <strong>Host:</strong> {game.host.display_name}
        </Typography>
      </Box>
    )}

    {/* When with Calendar Download */}
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 1 }}>
      <Typography variant="body1" sx={{ fontSize: '1.1rem', fontWeight: 'bold' }}>
        <strong>When:</strong> {formatDateTime(game.scheduled_at)}
      </Typography>
      {(isHost || isParticipant) && (
        <IconButton size="small" onClick={handleDownloadCalendar} disabled={calendarLoading}>
          {calendarLoading ? <CircularProgress size={20} /> : <DownloadIcon />}
        </IconButton>
      )}
    </Box>

    {/* Duration and Reminders on Same Line */}
    <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mb: 1 }}>
      {game.expected_duration_minutes && (
        <Typography variant="body2">
          <strong>Duration:</strong> {formatDuration(game.expected_duration_minutes)}
        </Typography>
      )}
      {game.reminder_minutes && game.reminder_minutes.length > 0 && (
        <Typography variant="body2">
          <strong>Reminders:</strong> {game.reminder_minutes.join(', ')} minutes before
        </Typography>
      )}
    </Box>

    {/* Where (Physical Location) */}
    {game.where && (
      <Typography variant="body1" paragraph sx={{ fontSize: '1.1rem' }}>
        <strong>Where:</strong> {game.where}
      </Typography>
    )}

    {/* Location (Discord Context) */}
    <Typography variant="body1" paragraph sx={{ fontSize: '1.1rem' }}>
      <strong>Location:</strong> {game.guild_name || 'Unknown Server'} #{game.channel_name || 'Unknown Channel'}
    </Typography>
  </Box>

  {/* Signup Instructions (Host-Only) */}
  {isHost && game.signup_instructions && (
    <Box sx={{ p: 2, mb: 2, bgcolor: 'info.light', borderRadius: 1, border: '1px solid', borderColor: 'info.main' }}>
      <Typography variant="subtitle2" gutterBottom sx={{ fontWeight: 'bold' }}>
        ℹ️ Signup Instructions
      </Typography>
      <Typography variant="body2">{game.signup_instructions}</Typography>
    </Box>
  )}

  <Divider sx={{ my: 3 }} />

  {/* Participants Section */}
  <Box sx={{ mb: 3 }}>
    <Typography variant="h6" gutterBottom>
      Participants ({game.participant_count || 0}/{game.max_players || 10})
    </Typography>
    <ParticipantList participants={game.participants || []} maxPlayers={game.max_players || 10} />
  </Box>
</Paper>
```

**TypeScript Interfaces** (types/index.ts):
```typescript
export interface Guild {
  id: string;
  guild_name: string;
  created_at: string;
  updated_at: string;
}

export interface GameSession {
  id: string;
  title: string;
  description: string;
  scheduled_at: string;
  where: string | null;
  max_players: number | null;
  guild_id: string;
  guild_name: string | null; // NEW: Added in December 2025 for server context display
  channel_id: string;
  channel_name: string;
  message_id: string | null;
  host: Participant;
  reminder_minutes: number[] | null;
  notify_role_ids: string[] | null;
  expected_duration_minutes: number | null;
  status: string;
  participant_count: number;
  participants: Participant[];
  signup_instructions: string | null;
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

export interface Participant {
  id: string;
  game_session_id: string;
  user_id: string;
  discord_id: string;
  display_name: string;
  avatar_url: string | null; // Used for host avatar display
  joined_at: string;
  pre_filled_position: number | null;
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

### Align Create Game Page Layout with Summary Card and Details Page

Update the game creation page to follow the same visual hierarchy and field layout as the GameCard and GameDetails components, ensuring a consistent user experience across all game-related interfaces.

**Key Visual Alignment Goals**:
- Match information hierarchy from GameCard/GameDetails
- Use consistent typography (body1 at 1.1rem for main fields, body2 for secondary)
- Adopt horizontal flex layouts with 2-3 column gaps for related fields
- Display host information with avatar prominently (if creating on behalf of someone)
- Show server context as "guild_name # channel_name" format
- Use consistent spacing and MUI component patterns

**Layout Target for Create Game Form**:
1. **Server Selection** (if multiple accessible) - FormControl with Select
2. **Template Selection** (after server selected) - FormControl with Select
   - Template description below dropdown (body2, text.secondary)
3. **Game Details Section Header** - Typography variant h6
4. **Title** - TextField (matches GameDetails title display)
5. **Description** - TextField multiline (matches GameDetails description)
6. **Channel** - FormControl Select showing "# channel_name" (read-only from template)
7. **When (Date + Time)** - DateTimePicker or two fields
8. **Duration and Reminders** - Horizontal flex with gap: 3
   - Duration field (optional)
   - Reminders field (optional) showing "X minutes before" format
9. **Where** - TextField (optional physical location)
10. **Location Context Display** - Typography showing "guild_name # channel_name" (read-only)
11. **Max Players** - TextField number input
12. **Signup Instructions** - TextField multiline (optional, shows to host only)
13. **Participants** - Pre-filled participants list (optional)
14. **Action Buttons** - Horizontal flex: Submit, Cancel

**Benefits**:
- Consistent visual language across summary, details, and creation pages
- Users see familiar layout when creating games
- Reduced cognitive load with predictable field ordering
- Better visual hierarchy matches how information is consumed in other views
- Typography consistency improves readability

**Implementation Considerations**:
- Consolidate server + template selection into unified page (route: `/games/new`)
- Apply GameDetails styling patterns (fontSize 1.1rem for primary fields)
- Use horizontal flex for Duration/Reminders like GameDetails does
- Show channel as "# channel_name" to match Discord convention
- Add guild_name display to show server context during creation
- Maintain MUI FormControl patterns for consistency
- Keep existing validation and auto-population logic

## Implementation Guidance

### Objectives
- **Visual Consistency**: Align create game page layout with GameCard and GameDetails patterns
- **Typography Matching**: Use body1 (1.1rem) for primary fields, body2 for secondary info
- **Horizontal Layouts**: Apply flex layouts with gaps for Duration/Reminders like GameDetails
- **Server Context Display**: Show "guild_name # channel_name" format throughout creation flow
- **Simplified Routing**: Consolidate to single `/games/new` route without guild-specific URLs
- **Auto-selection**: Maintain smart defaults for single server/template scenarios
- **Host Avatar Display**: Consider showing current user's avatar as host preview (optional)

### Key Tasks

1. **Update Routing** (App.tsx)
   - Change route from `/guilds/:guildId/games/new` to `/games/new`
   - Remove guildId param dependency

2. **Refactor CreateGame Component** (CreateGame.tsx)
   - Remove URL param extraction for guildId
   - Add state for guilds list and selected guild
   - Load guilds on mount (reuse MyGames pattern)
   - Add server dropdown at top with MUI FormControl
   - Implement guild selection handler that loads templates
   - Hide/disable server dropdown if only 1 accessible guild (auto-select)
   - Apply GameDetails typography patterns to form fields
   - Show guild_name # channel_name context display
   - Use horizontal flex (gap: 3) for Duration/Reminders fields
   - Match heading styles (h6 for "Game Details" section)

3. **Update GameForm Styling** (GameForm.tsx)
   - Apply consistent typography: body1 at fontSize 1.1rem for labels
   - Use body2 for helper text and secondary info
   - Implement horizontal flex layout for Duration/Reminders
   - Show channel as "# channel_name" format
   - Add Location context field showing "guild_name # channel_name" (read-only)
   - Match spacing patterns from GameDetails (mb: 1, gap: 3)
   - Style signup instructions field to match GameDetails boxed format (for preview)

4. **Update MyGames Navigation** (MyGames.tsx)
   - Change "Create Game" button to navigate to `/games/new`
   - Remove server count checking and ServerSelectionDialog usage
   - Simplify to single navigation: `navigate('/games/new')`

5. **Typography and Spacing Consistency**
   - Primary fields: Typography body1 with fontSize '1.1rem'
   - Secondary info: Typography body2 (default size)
   - Section headers: Typography h6 with gutterBottom
   - Field spacing: mb: 1 for tight spacing, mb: 2 for section breaks
   - Horizontal groups: gap: 2 (GameCard) or gap: 3 (GameDetails)

6. **Update Tests**
   - Modify CreateGame tests for new route
   - Update MyGames tests for simplified navigation
   - Add tests for server dropdown auto-selection behavior
   - Test visual consistency with GameCard/GameDetails patterns

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
- **Visual alignment**: Create game form matches GameCard and GameDetails typography
- **Field layout**: Duration/Reminders displayed horizontally with gap: 3 like GameDetails
- **Channel display**: Shows "# channel_name" format matching Discord convention
- **Server context**: Displays "guild_name # channel_name" for location context
- **Typography**: Primary fields use body1 at 1.1rem, secondary use body2
- **Spacing**: Consistent mb: 1, mb: 2, gap: 2/3 patterns match details page
- Form validation and submission work unchanged
- Navigation from "Create Game" button simplified
- No loss of existing functionality
- All tests pass with updated routing and styling
