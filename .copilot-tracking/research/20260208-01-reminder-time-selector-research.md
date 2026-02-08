<!-- markdownlint-disable-file -->

# Task Research Notes: Reminder Time Selector Component

## Research Executed

### File Analysis

- `frontend/src/components/DurationSelector.tsx`
  - Clean preset + custom pattern with Select dropdown and TextField inputs
  - Manages single value (number | null) with hours/minutes breakdown
  - Preset options: 2 hours (120), 4 hours (240), Custom
  - Custom mode shows separate hours/minutes numeric inputs
- `frontend/src/components/GameForm.tsx` (lines 615-640)
  - Current reminder UI: Plain TextField accepting comma-separated integers
  - Label: "Reminder Times (minutes)"
  - Helper text: "Comma-separated (e.g., 60, 15). Leave empty for default"
  - Validation on blur using `validateReminderMinutes`
- `frontend/src/utils/fieldValidation.ts` (lines 50-80)
  - Validates comma-separated string input
  - Returns `ValidationResult` with `value: number[]` (array of parsed integers)
  - Range validation: 1 to 10080 minutes (1 week max)
  - Enforces integer values only

### Code Search Results

- Reminder data structure confirmed across codebase:
  - Schema: `reminder_minutes: list[int] | None` (shared/schemas/game.py, template.py)
  - Model: `reminder_minutes: Mapped[list[int] | None] = mapped_column(JSON, nullable=True)`
  - Frontend state: `reminderMinutes: string` (comma-separated) converted to array before submission
- DurationSelector usage pattern:
  - Imported and used in GameForm for `expectedDurationMinutes` field
  - Replaced previous text-based duration parsing
  - Successfully handles null, preset, and custom values

### External Research

- #fetch:https://mui.com/material-ui/react-chip/
  - Chip component perfect for displaying multiple selected reminder times
  - Supports `onDelete` callback for removing individual items
  - Can be used in combination with Select or Autocomplete
- #fetch:https://mui.com/material-ui/react-autocomplete/
  - Autocomplete with `multiple` prop allows selecting multiple preset options
  - Supports `freeSolo` for custom input alongside presets
  - Built-in chip display for selected values
  - `getOptionLabel`, `renderTags`, `renderInput` for customization

### Project Conventions

- Standards referenced: `.github/instructions/reactjs.instructions.md`, `.github/instructions/typescript-5-es2022.instructions.md`, `.github/instructions/test-driven-development.instructions.md`
- Instructions followed: Component reusability, self-documenting code, TDD methodology

## Key Discoveries

### Critical Difference: Single vs Multiple Values

**DurationSelector Architecture:**

```typescript
export interface DurationSelectorProps {
  value: number | null; // Single value
  onChange: (minutes: number | null) => void;
  error?: boolean;
  helperText?: string;
}
```

**Reminder Requirements:**

```typescript
// Required interface for reminder times
export interface ReminderSelectorProps {
  value: number[]; // Multiple values (array)
  onChange: (minutes: number[]) => void;
  error?: boolean;
  helperText?: string;
}
```

### Current Reminder Time Workflow

1. **User Input**: Types comma-separated integers in TextField (`"60, 15, 1440"`)
2. **Validation**: `validateReminderMinutes()` parses and validates each value
3. **Storage**: Frontend stores as string, converts to `number[]` before submission
4. **Backend**: Receives and stores as `list[int]` in JSON column

**User Pain Points:**

- Manual typing of numbers is error-prone
- No visual feedback for common presets
- Unclear what common reminder intervals are
- Comma-separated format not intuitive

### Proposed Preset Values

Based on user suggestion and common use cases:

```typescript
const REMINDER_PRESETS = [
  { label: '5 minutes', value: 5 },
  { label: '30 minutes', value: 30 },
  { label: '1 hour', value: 60 },
  { label: '2 hours', value: 120 },
  { label: '1 day', value: 1440 },
  { label: 'Custom...', value: 'custom' },
];
```

### Complete Examples

#### Approach A: MUI Autocomplete with Multiple Selection

```typescript
import { Autocomplete, Chip, TextField } from '@mui/material';

const REMINDER_PRESETS = [
  { label: '5 minutes', value: 5 },
  { label: '30 minutes', value: 30 },
  { label: '1 hour', value: 60 },
  { label: '2 hours', value: 120 },
  { label: '1 day', value: 1440 },
];

export function ReminderSelector({ value, onChange, error, helperText }: ReminderSelectorProps) {
  const [customValue, setCustomValue] = useState('');
  const [showCustom, setShowCustom] = useState(false);

  const selectedOptions = value.map(val =>
    REMINDER_PRESETS.find(p => p.value === val) || { label: `${val} min`, value: val }
  );

  const handleChange = (event: any, newValue: typeof REMINDER_PRESETS) => {
    onChange(newValue.map(option => option.value));
  };

  return (
    <Box>
      <Autocomplete
        multiple
        options={REMINDER_PRESETS}
        value={selectedOptions}
        onChange={handleChange}
        getOptionLabel={(option) => option.label}
        isOptionEqualToValue={(option, value) => option.value === value.value}
        renderInput={(params) => (
          <TextField
            {...params}
            label="Reminder Times"
            error={error}
            helperText={helperText || 'Select one or more reminder times'}
          />
        )}
        renderTags={(tagValue, getTagProps) =>
          tagValue.map((option, index) => (
            <Chip
              label={option.label}
              {...getTagProps({ index })}
              key={option.value}
            />
          ))
        }
      />

      {showCustom && (
        <TextField
          label="Custom Minutes"
          type="number"
          value={customValue}
          onChange={(e) => setCustomValue(e.target.value)}
          inputProps={{ min: 1, max: 10080 }}
          sx={{ mt: 2 }}
        />
      )}
    </Box>
  );
}
```

**Benefits:**

- Native multi-select behavior built into MUI
- Chip display shows selected values clearly
- Can add custom values via `freeSolo` prop
- Familiar UX pattern for multi-selection

**Trade-offs:**

- More complex than DurationSelector pattern
- Custom value entry requires additional UI/logic
- May be less intuitive for users expecting simple presets

#### Approach B: Checklist with Custom Option

```typescript
import { FormGroup, FormControlLabel, Checkbox, TextField, Box } from '@mui/material';

const REMINDER_PRESETS = [
  { label: '5 minutes', value: 5 },
  { label: '30 minutes', value: 30 },
  { label: '1 hour', value: 60 },
  { label: '2 hours', value: 120 },
  { label: '1 day', value: 1440 },
];

export function ReminderSelector({ value, onChange, error, helperText }: ReminderSelectorProps) {
  const [customMinutes, setCustomMinutes] = useState('');

  const handlePresetToggle = (presetValue: number) => {
    const isSelected = value.includes(presetValue);
    if (isSelected) {
      onChange(value.filter(v => v !== presetValue));
    } else {
      onChange([...value, presetValue].sort((a, b) => a - b));
    }
  };

  const handleCustomAdd = () => {
    const num = parseInt(customMinutes, 10);
    if (!isNaN(num) && num >= 1 && num <= 10080 && !value.includes(num)) {
      onChange([...value, num].sort((a, b) => a - b));
      setCustomMinutes('');
    }
  };

  return (
    <Box>
      <FormGroup>
        {REMINDER_PRESETS.map(preset => (
          <FormControlLabel
            key={preset.value}
            control={
              <Checkbox
                checked={value.includes(preset.value)}
                onChange={() => handlePresetToggle(preset.value)}
              />
            }
            label={preset.label}
          />
        ))}
      </FormGroup>

      <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
        <TextField
          label="Custom Minutes"
          type="number"
          value={customMinutes}
          onChange={(e) => setCustomMinutes(e.target.value)}
          inputProps={{ min: 1, max: 10080 }}
          size="small"
          sx={{ flex: 1 }}
        />
        <Button onClick={handleCustomAdd} variant="outlined">
          Add
        </Button>
      </Box>

      {value.length > 0 && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 2 }}>
          {value.map(val => {
            const preset = REMINDER_PRESETS.find(p => p.value === val);
            return (
              <Chip
                key={val}
                label={preset ? preset.label : `${val} min`}
                onDelete={() => onChange(value.filter(v => v !== val))}
              />
            );
          })}
        </Box>
      )}

      {helperText && (
        <FormHelperText error={error}>{helperText}</FormHelperText>
      )}
    </Box>
  );
}
```

**Benefits:**

- Clear visual indication of all available presets
- Explicit multi-select with checkboxes
- Custom values shown as chips alongside presets
- Simple mental model: check boxes + add custom

**Trade-offs:**

- Takes more vertical space
- More clicks to add custom values
- May feel less compact than dropdown

#### Approach C: Hybrid Select + Chip Display

```typescript
import { FormControl, InputLabel, Select, MenuItem, Chip, Box, TextField, Button } from '@mui/material';

const REMINDER_PRESETS = [
  { label: '5 minutes', value: 5 },
  { label: '30 minutes', value: 30 },
  { label: '1 hour', value: 60 },
  { label: '2 hours', value: 120 },
  { label: '1 day', value: 1440 },
];

export function ReminderSelector({ value, onChange, error, helperText }: ReminderSelectorProps) {
  const [showCustom, setShowCustom] = useState(false);
  const [customMinutes, setCustomMinutes] = useState('');

  const handlePresetAdd = (event: SelectChangeEvent<string>) => {
    const selectedValue = event.target.value;

    if (selectedValue === 'custom') {
      setShowCustom(true);
      return;
    }

    const presetValue = parseInt(selectedValue, 10);
    if (!value.includes(presetValue)) {
      onChange([...value, presetValue].sort((a, b) => a - b));
    }
  };

  const handleCustomAdd = () => {
    const num = parseInt(customMinutes, 10);
    if (!isNaN(num) && num >= 1 && num <= 10080 && !value.includes(num)) {
      onChange([...value, num].sort((a, b) => a - b));
      setCustomMinutes('');
      setShowCustom(false);
    }
  };

  const handleDelete = (minuteValue: number) => {
    onChange(value.filter(v => v !== minuteValue));
  };

  const getPresetLabel = (val: number) => {
    const preset = REMINDER_PRESETS.find(p => p.value === val);
    return preset ? preset.label : `${val} minutes`;
  };

  return (
    <Box>
      <FormControl fullWidth error={error}>
        <InputLabel>Add Reminder Time</InputLabel>
        <Select
          value=""
          onChange={handlePresetAdd}
          label="Add Reminder Time"
          displayEmpty={false}
        >
          {REMINDER_PRESETS.map(preset => (
            <MenuItem
              key={preset.value}
              value={preset.value}
              disabled={value.includes(preset.value)}
            >
              {preset.label}
            </MenuItem>
          ))}
          <MenuItem value="custom">Custom...</MenuItem>
        </Select>
      </FormControl>

      {showCustom && (
        <Box sx={{ display: 'flex', gap: 1, mt: 2 }}>
          <TextField
            label="Custom Minutes"
            type="number"
            value={customMinutes}
            onChange={(e) => setCustomMinutes(e.target.value)}
            inputProps={{ min: 1, max: 10080 }}
            size="small"
            sx={{ flex: 1 }}
            error={error}
          />
          <Button onClick={handleCustomAdd} variant="contained" size="small">
            Add
          </Button>
          <Button onClick={() => setShowCustom(false)} size="small">
            Cancel
          </Button>
        </Box>
      )}

      {value.length > 0 && (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 1, mt: 2 }}>
          {value.map(val => (
            <Chip
              key={val}
              label={getPresetLabel(val)}
              onDelete={() => handleDelete(val)}
              color="primary"
              variant="outlined"
            />
          ))}
        </Box>
      )}

      {helperText && (
        <FormHelperText error={error} sx={{ mt: 1 }}>
          {helperText}
        </FormHelperText>
      )}
    </Box>
  );
}
```

**Benefits:**

- Dropdown pattern similar to DurationSelector (familiar to users)
- Chip display clearly shows all selected values
- Can't accidentally select same value twice (disabled in dropdown)
- Custom option appears inline, similar to DurationSelector custom mode
- Compact when no reminders selected

**Trade-offs:**

- Two-step process (select then chips appear)
- Less immediately obvious it's multi-select
- Custom workflow slightly different from DurationSelector

## Recommended Approach

**Approach C: Hybrid Select + Chip Display** is the optimal solution because:

1. **Consistency with DurationSelector**: Uses same Select dropdown pattern users just learned
2. **Clear Multi-Value Display**: Chips make it obvious multiple values are selected
3. **Intuitive Interaction**: "Add reminder" select dropdown → chips appear below
4. **Space Efficient**: Compact when empty, expands to show selections
5. **Prevents Duplicates**: Disables already-selected presets in dropdown
6. **Familiar Custom Pattern**: Custom mode appears inline like DurationSelector
7. **Component Similarity**: Can reuse testing patterns from DurationSelector

### Key Implementation Details

**Component Structure:**

```typescript
export interface ReminderSelectorProps {
  value: number[]; // Array of selected reminder minutes
  onChange: (minutes: number[]) => void;
  error?: boolean;
  helperText?: string;
}
```

**State Management:**

- `value` prop contains array of selected reminder times
- Select dropdown stays empty (value="") after each selection
- Chips display all selected values with delete buttons
- Custom mode toggle separate from main select

**Preset Values:**

```typescript
const REMINDER_PRESETS = [
  { label: '5 minutes', value: 5 },
  { label: '30 minutes', value: 30 },
  { label: '1 hour', value: 60 },
  { label: '2 hours', value: 120 },
  { label: '1 day', value: 1440 },
];
```

**Custom Input Validation:**

- Range: 1-10080 minutes (matches existing validation)
- Integer only (no decimals)
- Duplicate detection (don't add if already selected)
- Auto-sort values ascending for consistent display

**Integration with GameForm:**

```typescript
// Replace current TextField
<TextField
  label="Reminder Times (minutes)"
  // ... existing props
/>

// With new ReminderSelector
<ReminderSelector
  value={formData.reminderMinutesArray}  // New state: number[]
  onChange={(minutes) => {
    setFormData(prev => ({
      ...prev,
      reminderMinutesArray: minutes,
      reminderMinutes: minutes.join(', ')  // Keep string for backward compat
    }));
  }}
  error={!!reminderError}
  helperText={reminderError || 'Select one or more reminder times'}
/>
```

## Implementation Guidance

- **Objectives**:
  1. Create ReminderSelector component with Select + Chip pattern
  2. Support preset values (5min, 30min, 1hr, 2hr, 1day) + custom input
  3. Display selected values as deletable chips
  4. Match DurationSelector's interaction pattern for consistency
  5. Maintain existing validation rules (1-10080 minute range)

- **Key Tasks**:
  1. Create ReminderSelector component stub following TDD methodology
  2. Write comprehensive tests for multi-value selection, chip display, custom input
  3. Implement preset selection with duplicate prevention
  4. Add chip display with delete functionality
  5. Implement custom minute input with validation
  6. Integrate into GameForm replacing current TextField
  7. Update TemplateForm for consistency
  8. Remove comma-separated parsing from validation (still parse for old data compatibility)

- **Dependencies**:
  - MUI components: Select, MenuItem, Chip, TextField, Button, FormControl, FormHelperText
  - Existing validation constants from fieldValidation.ts
  - vitest and @testing-library/react for testing

- **Success Criteria**:
  1. Users can select multiple preset reminder times
  2. Selected times display as chips with delete buttons
  3. Custom minute input works with validation
  4. Cannot add duplicate values
  5. Values automatically sorted ascending
  6. Interaction pattern feels similar to DurationSelector
  7. All validation rules enforced (1-10080 range, integers only)
  8. 100% test coverage matching DurationSelector test quality
  9. Existing games with comma-separated reminder data load correctly
