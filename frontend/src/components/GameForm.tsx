// Copyright 2025-2026 Bret McKee
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

import { FC, useState, useEffect, startTransition } from 'react';
import {
  Typography,
  Box,
  TextField,
  Button,
  FormControl,
  InputLabel,
  Select,
  MenuItem,
  CircularProgress,
  Alert,
  Paper,
  SelectChangeEvent,
  Grid,
  Checkbox,
  FormControlLabel,
} from '@mui/material';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import { AdapterDateFns } from '@mui/x-date-pickers/AdapterDateFns';
import { subMinutes } from 'date-fns';
import { Channel, GameSession, ParticipantType, SignupMethod, SIGNUP_METHOD_INFO } from '../types';
import { ValidationErrors } from './ValidationErrors';
import { ChannelValidationErrors } from './ChannelValidationErrors';
import { formatParticipantDisplay } from '../utils/formatParticipant';
import {
  EditableParticipantList,
  ParticipantInput as EditableParticipantInput,
} from './EditableParticipantList';
import { DurationSelector } from './DurationSelector';
import { ReminderSelector } from './ReminderSelector';
import { RecurrenceSelector } from './RecurrenceSelector';
import { useAuth } from '../hooks/useAuth';
import { Time } from '../constants/time';
import { UI } from '../constants/ui';
import {
  validateDuration,
  validateMaxPlayers,
  validateCharacterLimit,
  validateFutureDate,
  validateReminderMinutes,
} from '../utils/fieldValidation';

/**
 * Round time up to the next half hour (e.g., 5:13 -> 5:30, 5:30 -> 5:30, 5:31 -> 6:00)
 */
function getNextHalfHour(): Date {
  const now = new Date();
  const minutes = now.getMinutes();
  const seconds = now.getSeconds();
  const milliseconds = now.getMilliseconds();

  // If already on the half hour exactly, keep it
  if (minutes === 0 || minutes === Time.MINUTES_PER_HALF_HOUR) {
    if (seconds === 0 && milliseconds === 0) {
      return now;
    }
  }

  // Round up to next half hour
  const nextHalfHour = new Date(now);
  if (minutes < Time.MINUTES_PER_HALF_HOUR) {
    nextHalfHour.setMinutes(Time.MINUTES_PER_HALF_HOUR, 0, 0);
  } else {
    nextHalfHour.setHours(now.getHours() + 1, 0, 0, 0);
  }

  return nextHalfHour;
}

export interface GameFormData {
  title: string;
  host?: string;
  description: string;
  signupInstructions: string;
  scheduledAt: Date | null;
  postAt: Date | null;
  clearPostAt: boolean;
  where: string;
  channelId: string;
  maxPlayers: string;
  reminderMinutes: string;
  reminderMinutesArray: number[];
  expectedDurationMinutes: number | null;
  participants: EditableParticipantInput[];
  signupMethod: string;
  thumbnailFile: File | null;
  imageFile: File | null;
  removeThumbnail: boolean;
  removeImage: boolean;
  rewards: string;
  remindHostRewards: boolean;
  recurRule: string | null;
}

interface GameFormProps {
  mode: 'create' | 'edit';
  initialData?: Partial<GameSession>;
  guildId: string;
  guildName?: string;
  canChangeChannel?: boolean;
  isBotManager?: boolean;
  channels: Channel[];
  allowedSignupMethods?: string[] | null;
  defaultSignupMethod?: string | null;
  onSubmit: (formData: GameFormData) => Promise<void>;
  onSaveAndArchive?: (formData: GameFormData) => Promise<void>;
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
  channelValidationErrors?: Array<{
    type: string;
    input: string;
    reason: string;
    suggestions: Array<{
      id: string;
      name: string;
    }>;
  }> | null;
  onChannelValidationErrorClick?: (originalInput: string, newChannelName: string) => void;
}

/**
 * Replace all exact occurrences of `token` in `text` with `replacement`,
 * but only when the token is not immediately followed by a character that
 * could be part of a longer mention.
 *
 * Discord usernames (and channel names) allow word characters (\w = [a-zA-Z0-9_])
 * as well as periods (`.`), so "@foo" must NOT match inside "@foo.bar".
 * The negative lookahead `(?![\w.])` stops the match when either a word
 * character or a period follows, ensuring only the exact token is replaced.
 */
function replaceMentionToken(text: string, token: string, replacement: string): string {
  // Escape all regex metacharacters in the token so it is treated as a
  // literal string (e.g. "#general-chat" contains "-" which is safe, but
  // "@foo.bar" contains "." which would otherwise match any character).
  const escaped = token.trim().replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  // (?![\w.]) — negative lookahead: fail if the next char is a word char or
  // a period, both of which are valid continuation characters in a mention.
  return text.replace(new RegExp(escaped + '(?![\\w.])', 'g'), replacement);
}

function buildParticipantList(data: Partial<GameSession>): EditableParticipantInput[] {
  if (data.signup_method === SignupMethod.HOST_SELECTED_WITH_WAITLIST) {
    const confirmed = (data.confirmed_participants ?? []).map((p, index) => ({
      id: p.id,
      mention: formatParticipantDisplay(p.display_name, p.discord_id),
      isValid: true,
      preFillPosition: index + 1,
      isExplicitlyPositioned: true,
      isReadOnly: false,
      validationStatus: 'valid' as const,
    }));
    const maxSlots = data.max_players ?? UI.DEFAULT_MAX_PLAYERS;
    const openSlotCount = Math.max(0, maxSlots - confirmed.length);
    const openSlots = Array.from({ length: openSlotCount }, (_, i) => ({
      id: `open-slot-${i}`,
      mention: '',
      preFillPosition: confirmed.length + i + 1,
      isOpenSlot: true as const,
      isExplicitlyPositioned: false,
      validationStatus: 'valid' as const,
    }));
    const waitlisted = (data.waitlist_participants ?? []).map((p, index) => ({
      id: p.id,
      mention: formatParticipantDisplay(p.display_name, p.discord_id),
      isValid: true,
      preFillPosition: confirmed.length + openSlotCount + index + 1,
      isExplicitlyPositioned: false,
      isReadOnly: true,
      validationStatus: 'valid' as const,
    }));
    return [...confirmed, ...openSlots, ...waitlisted];
  }
  return (data.participants ?? [])
    .sort((a, b) => {
      const aPos =
        a.position_type === ParticipantType.HOST_ADDED ? a.position : Number.MAX_SAFE_INTEGER;
      const bPos =
        b.position_type === ParticipantType.HOST_ADDED ? b.position : Number.MAX_SAFE_INTEGER;
      return aPos - bPos;
    })
    .map((p, index) => ({
      id: p.id,
      mention: formatParticipantDisplay(p.display_name, p.discord_id),
      isValid: true,
      preFillPosition: index + 1,
      isExplicitlyPositioned: p.position_type === ParticipantType.HOST_ADDED,
      isReadOnly: p.position_type !== ParticipantType.HOST_ADDED,
      validationStatus: 'valid' as const,
    }));
}

export const GameForm: FC<GameFormProps> = ({
  mode,
  initialData,
  guildId,
  guildName: _guildName,
  canChangeChannel = true,
  isBotManager = false,
  channels,
  allowedSignupMethods = null,
  defaultSignupMethod = null,
  onSubmit,
  onSaveAndArchive,
  onCancel,
  validationErrors,
  validParticipants,
  onValidationErrorClick,
  channelValidationErrors,
  onChannelValidationErrorClick,
}) => {
  const { user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [hostError, setHostError] = useState<string | null>(null);

  // Validation error states
  const [durationError, setDurationError] = useState<string | null>(null);
  const [reminderError, setReminderError] = useState<string | null>(null);
  const [maxPlayersError, setMaxPlayersError] = useState<string | null>(null);
  const [locationError, setLocationError] = useState<string | null>(null);
  const [descriptionError, setDescriptionError] = useState<string | null>(null);
  const [signupInstructionsError, setSignupInstructionsError] = useState<string | null>(null);
  const [scheduledAtError, setScheduledAtError] = useState<string | null>(null);

  // Calculate available signup methods: if empty/null, all methods are available.
  // HOST_SELECTED_WITH_WAITLIST is a sub-option of HOST_SELECTED and is excluded from the
  // select — it is toggled via the waitlist checkbox instead.
  const availableSignupMethods = (
    !allowedSignupMethods || allowedSignupMethods.length === 0
      ? Object.values(SignupMethod)
      : allowedSignupMethods.filter((method) => method in SignupMethod)
  ).filter((method) => method !== SignupMethod.HOST_SELECTED_WITH_WAITLIST);

  // Determine default signup method
  const resolvedDefaultSignupMethod =
    defaultSignupMethod && availableSignupMethods.includes(defaultSignupMethod)
      ? defaultSignupMethod
      : availableSignupMethods[0] || SignupMethod.SELF_SIGNUP;

  const [formData, setFormData] = useState<GameFormData>({
    title: initialData?.title || '',
    host: '',
    description: initialData?.description || '',
    signupInstructions: initialData?.signup_instructions || '',
    scheduledAt: initialData?.scheduled_at ? new Date(initialData.scheduled_at) : getNextHalfHour(),
    postAt: initialData?.post_at ? new Date(initialData.post_at) : null,
    clearPostAt: false,
    where: initialData?.where_display ?? initialData?.where ?? '',
    channelId: initialData?.channel_id || '',
    maxPlayers: initialData?.max_players?.toString() || '10',
    reminderMinutes: initialData?.reminder_minutes?.join(', ') || '',
    reminderMinutesArray:
      initialData?.reminder_minutes && Array.isArray(initialData.reminder_minutes)
        ? [...initialData.reminder_minutes]
        : [],
    expectedDurationMinutes: initialData?.expected_duration_minutes ?? null,
    participants: initialData ? buildParticipantList(initialData) : [],
    signupMethod: initialData?.signup_method || resolvedDefaultSignupMethod,
    thumbnailFile: null,
    imageFile: null,
    removeThumbnail: false,
    removeImage: false,
    rewards: initialData?.rewards || '',
    remindHostRewards: initialData?.remind_host_rewards ?? false,
    recurRule: initialData?.recur_rule ?? null,
  });

  // Update form when initialData changes (e.g., after async fetch in edit mode)
  useEffect(() => {
    if (initialData) {
      setFormData({
        title: initialData.title || '',
        host: '',
        description: initialData.description || '',
        signupInstructions: initialData.signup_instructions || '',
        scheduledAt: initialData.scheduled_at
          ? new Date(initialData.scheduled_at)
          : getNextHalfHour(),
        postAt: initialData.post_at ? new Date(initialData.post_at) : null,
        clearPostAt: false,
        where: initialData.where_display ?? initialData.where ?? '',
        channelId: initialData.channel_id || '',
        maxPlayers: initialData.max_players?.toString() || '10',
        reminderMinutes: initialData.reminder_minutes?.join(', ') || '',
        reminderMinutesArray:
          initialData.reminder_minutes && Array.isArray(initialData.reminder_minutes)
            ? [...initialData.reminder_minutes]
            : [],
        expectedDurationMinutes: initialData.expected_duration_minutes ?? null,
        participants: buildParticipantList(initialData),
        signupMethod: initialData.signup_method || resolvedDefaultSignupMethod,
        thumbnailFile: null,
        imageFile: null,
        removeThumbnail: false,
        removeImage: false,
        rewards: initialData.rewards || '',
        remindHostRewards: initialData.remind_host_rewards ?? false,
        recurRule: initialData.recur_rule ?? null,
      });
    }
  }, [initialData, resolvedDefaultSignupMethod]);

  // Auto-select channel when only one is available
  useEffect(() => {
    if (channels.length === 1 && !formData.channelId && channels[0]) {
      setFormData((prev) => ({ ...prev, channelId: channels[0]!.id }));
    }
  }, [channels, formData.channelId]);

  // Update participant and host validation status when validationErrors change
  useEffect(() => {
    if (!validationErrors && !validParticipants) return;

    const invalidInputs = new Set(validationErrors?.map((err) => err.input.trim()) || []);
    const validInputs = new Set(validParticipants?.map((input) => input.trim()) || []);

    // Check if host field has a validation error
    const hostInput = formData.host?.trim();
    if (hostInput) {
      const hostValidationError = validationErrors?.find((err) => err.input.trim() === hostInput);
      setHostError(hostValidationError?.reason || null);
    } else {
      setHostError(null);
    }

    setFormData((prev) => ({
      ...prev,
      participants: prev.participants.map((p) => {
        const mention = p.mention.trim();
        if (invalidInputs.has(mention)) {
          return { ...p, validationStatus: 'invalid' as const };
        }
        if (validInputs.has(mention)) {
          return { ...p, validationStatus: 'valid' as const };
        }
        // Don't change status for other participants
        return p;
      }),
    }));
  }, [validationErrors, validParticipants, formData.host]);

  const handleChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({ ...prev, [name]: value }));
  };

  // Validation handler stubs
  const validateDurationField = () => {
    const result = validateDuration(formData.expectedDurationMinutes);
    setDurationError(result.error || null);
  };

  const validateReminderField = () => {
    const result = validateReminderMinutes(formData.reminderMinutesArray, formData.scheduledAt);
    setReminderError(result.error ?? null);
  };

  const validateMaxPlayersField = () => {
    const result = validateMaxPlayers(formData.maxPlayers);
    setMaxPlayersError(result.error || null);
  };

  const validateLocationField = () => {
    const MAX_LOCATION_LENGTH = 500;
    const result = validateCharacterLimit(formData.where, MAX_LOCATION_LENGTH, 'Location');
    setLocationError(result.error || result.warning || null);
  };

  const validateDescriptionField = () => {
    const result = validateCharacterLimit(
      formData.description,
      UI.MAX_DESCRIPTION_LENGTH,
      'Description'
    );
    setDescriptionError(result.error || result.warning || null);
  };

  const validateSignupInstructionsField = () => {
    const MAX_SIGNUP_INSTRUCTIONS_LENGTH = 1000;
    const result = validateCharacterLimit(
      formData.signupInstructions,
      MAX_SIGNUP_INSTRUCTIONS_LENGTH,
      'Signup Instructions'
    );
    setSignupInstructionsError(result.error || result.warning || null);
  };

  // Helper text generators with character counts
  const getLocationHelperText = () => {
    if (locationError) return locationError;
    const MAX_LOCATION_LENGTH = 500;
    const count = formData.where.length;
    if (count === 0) {
      return 'Where players should go for information or mustering (#channel-name, Roll20 link, etc.)';
    }
    return `${count}/${MAX_LOCATION_LENGTH} characters`;
  };

  const getDescriptionHelperText = () => {
    if (descriptionError) return descriptionError;
    const count = formData.description.length;
    if (count === 0) return undefined;
    return `${count}/${UI.MAX_DESCRIPTION_LENGTH} characters`;
  };

  const getSignupInstructionsHelperText = () => {
    if (signupInstructionsError) return signupInstructionsError;
    const MAX_SIGNUP_INSTRUCTIONS_LENGTH = 1000;
    const count = formData.signupInstructions.length;
    if (count === 0) return 'Sent to each player via DM when they join the game';
    return `${count}/${MAX_SIGNUP_INSTRUCTIONS_LENGTH} characters`;
  };

  const handleSelectChange = (event: SelectChangeEvent) => {
    const { name, value } = event.target;
    if (name === 'signupMethod') {
      setFormData((prev) => ({ ...prev, signupMethod: value }));
    } else {
      setFormData((prev) => ({ ...prev, channelId: value }));
    }
  };

  const handleDateChange = (date: Date | null) => {
    setFormData((prev) => ({ ...prev, scheduledAt: date }));
    const result = validateFutureDate(date);
    setScheduledAtError(result.error || null);
  };

  const handlePostAtChange = (date: Date | null) => {
    setFormData((prev) => ({ ...prev, postAt: date, clearPostAt: false }));
  };

  const handleClearPostAtChange = (checked: boolean) => {
    setFormData((prev) => ({
      ...prev,
      clearPostAt: checked,
      postAt: checked ? null : prev.postAt,
    }));
  };

  const handleDurationChange = (minutes: number | null) => {
    setFormData((prev) => ({ ...prev, expectedDurationMinutes: minutes }));
    validateDurationField();
  };

  const handleReminderChange = (minutes: number[]) => {
    setFormData((prev) => ({
      ...prev,
      reminderMinutesArray: minutes,
      reminderMinutes: minutes.join(', '),
    }));
    validateReminderField();
  };

  const handleParticipantsChange = (participants: EditableParticipantInput[]) => {
    setFormData((prev) => ({ ...prev, participants }));
  };

  const handleThumbnailChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;

    if (file) {
      // Validate file size (<5MB)
      if (file.size > UI.MAX_FILE_SIZE_BYTES) {
        alert('Thumbnail must be less than 5MB');
        return;
      }

      // Validate file type
      const validTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        alert('Thumbnail must be PNG, JPEG, GIF, or WebP');
        return;
      }
    }

    setFormData((prev) => ({
      ...prev,
      thumbnailFile: file,
      removeThumbnail: false,
    }));
  };

  const handleImageChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0] || null;

    if (file) {
      // Validate file size (<5MB)
      if (file.size > UI.MAX_FILE_SIZE_BYTES) {
        alert('Banner image must be less than 5MB');
        return;
      }

      // Validate file type
      const validTypes = ['image/png', 'image/jpeg', 'image/gif', 'image/webp'];
      if (!validTypes.includes(file.type)) {
        alert('Banner must be PNG, JPEG, GIF, or WebP');
        return;
      }
    }

    setFormData((prev) => ({
      ...prev,
      imageFile: file,
      removeImage: false,
    }));
  };

  const handleRemoveThumbnail = () => {
    setFormData((prev) => ({
      ...prev,
      thumbnailFile: null,
      removeThumbnail: true,
    }));
  };

  const handleRemoveImage = () => {
    setFormData((prev) => ({
      ...prev,
      imageFile: null,
      removeImage: true,
    }));
  };

  const handleChannelSuggestionClick = (originalInput: string, newChannelName: string) => {
    setFormData((prev) => ({
      ...prev,
      where: prev.where.trim() === originalInput.trim() ? newChannelName : prev.where,
      description: replaceMentionToken(prev.description, originalInput, newChannelName),
      signupInstructions: replaceMentionToken(
        prev.signupInstructions,
        originalInput,
        newChannelName
      ),
    }));
    onChannelValidationErrorClick?.(originalInput, newChannelName);
  };

  const handleSuggestionClick = (originalInput: string, newUsername: string) => {
    const error = validationErrors?.find((e) => e.input === originalInput);
    const suggestion = error?.suggestions.find((s) => `@${s.username}` === newUsername);
    const resolvedMention = suggestion ? `<@${suggestion.discordId}>` : undefined;
    const displayMention = suggestion ? `@${suggestion.displayName}` : newUsername;
    setFormData((prev) => ({
      ...prev,
      participants: prev.participants.map((p) =>
        p.mention.trim() === originalInput.trim()
          ? { ...p, mention: displayMention, resolvedMention, validationStatus: 'unknown' as const }
          : p
      ),
      description: replaceMentionToken(prev.description, originalInput, newUsername),
      signupInstructions: replaceMentionToken(prev.signupInstructions, originalInput, newUsername),
    }));
    onValidationErrorClick?.(originalInput, newUsername);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!guildId || !formData.channelId || !formData.scheduledAt) {
      setError('Please fill in all required fields.');
      return;
    }

    const hasValidationErrors =
      !!durationError ||
      !!reminderError ||
      !!maxPlayersError ||
      !!locationError ||
      !!descriptionError ||
      !!signupInstructionsError ||
      !!scheduledAtError;

    if (hasValidationErrors) {
      setError('Please fix all validation errors before submitting.');
      return;
    }

    try {
      setLoading(true);
      setError(null);
      await onSubmit(formData);
    } catch (err: unknown) {
      console.error('Failed to submit form:', err);
      if (!validationErrors) {
        const errorDetail = (err as any).response?.data?.detail;
        const errorMessage =
          typeof errorDetail === 'string'
            ? errorDetail
            : errorDetail?.message || 'Failed to submit. Please try again.';
        setError(errorMessage);
      }
    } finally {
      startTransition(() => setLoading(false));
    }
  };

  return (
    <LocalizationProvider dateAdapter={AdapterDateFns}>
      <Paper elevation={3} sx={{ p: 4 }}>
        <Typography variant="h4" component="h1" gutterBottom>
          {mode === 'create' ? 'Create New Game' : 'Edit Game'}
        </Typography>

        {error && (
          <Alert severity="error" sx={{ mb: 2 }}>
            {error}
          </Alert>
        )}

        {validationErrors && (
          <ValidationErrors errors={validationErrors} onSuggestionClick={handleSuggestionClick} />
        )}

        {channelValidationErrors && (
          <ChannelValidationErrors
            errors={channelValidationErrors}
            onSuggestionClick={handleChannelSuggestionClick}
          />
        )}

        <Box component="form" onSubmit={handleSubmit} sx={{ mt: 3 }}>
          <TextField
            fullWidth
            required
            label="Game Title"
            name="title"
            value={formData.title}
            onChange={handleChange}
            margin="normal"
            disabled={loading}
            InputLabelProps={{
              sx: { fontSize: '1.1rem' },
            }}
            sx={{ mb: 1 }}
          />

          {isBotManager && (
            <TextField
              fullWidth
              label="Game Host"
              name="host"
              value={formData.host}
              onChange={handleChange}
              margin="normal"
              disabled={loading}
              placeholder={user?.username || 'Your username'}
              helperText={
                hostError ||
                '@mention or enter username if Game Host is someone other than yourself (you are automatically registered as Game Host if left blank)'
              }
              error={!!hostError}
              InputLabelProps={{
                sx: { fontSize: '1.1rem' },
              }}
              sx={{ mb: 1 }}
            />
          )}

          {mode === 'edit' && initialData?.status !== 'SCHEDULED' && (
            <TextField
              fullWidth
              multiline
              rows={3}
              label="Rewards"
              name="rewards"
              value={formData.rewards}
              onChange={handleChange}
              margin="normal"
              disabled={loading}
              helperText="Describe rewards or prizes for participants (displayed as a spoiler)"
              InputLabelProps={{
                sx: { fontSize: '1.1rem' },
              }}
              sx={{ mb: 1 }}
            />
          )}

          <TextField
            fullWidth
            label="Location"
            name="where"
            value={formData.where}
            onChange={handleChange}
            onBlur={validateLocationField}
            margin="normal"
            multiline
            rows={2}
            helperText={getLocationHelperText()}
            error={!!locationError}
            disabled={loading}
            inputProps={{ maxLength: 500 }}
            InputLabelProps={{
              sx: { fontSize: '1.1rem' },
            }}
            sx={{ mb: 1 }}
          />

          <DateTimePicker
            label="Game time (Your Local Time Zone) *"
            value={formData.scheduledAt}
            onChange={handleDateChange}
            disablePast
            disabled={loading}
            slotProps={{
              textField: {
                error: !!scheduledAtError,
                helperText: scheduledAtError,
                InputLabelProps: {
                  sx: { fontSize: '1.1rem' },
                },
              },
            }}
            sx={{ width: '100%', mt: 1, mb: 1 }}
          />

          {mode === 'edit' &&
            initialData?.post_at &&
            !initialData?.message_id &&
            new Date(initialData.post_at) > new Date() && (
              <FormControlLabel
                control={
                  <Checkbox
                    checked={formData.clearPostAt}
                    onChange={(e) => handleClearPostAtChange(e.target.checked)}
                    disabled={loading}
                  />
                }
                label="Post immediately (announce now)"
              />
            )}

          {!formData.clearPostAt &&
            !(
              mode === 'edit' &&
              initialData?.post_at &&
              new Date(initialData.post_at) <= new Date()
            ) && (
              <DateTimePicker
                label="Schedule Posting (optional)"
                value={formData.postAt}
                onChange={handlePostAtChange}
                minDateTime={new Date()}
                maxDateTime={formData.scheduledAt ? subMinutes(formData.scheduledAt, 1) : undefined}
                disabled={loading}
                slotProps={{
                  field: { clearable: true },
                  textField: {
                    helperText: formData.scheduledAt
                      ? `Leave empty to post immediately · must be between now and game start (${formData.scheduledAt.toLocaleString(undefined, { dateStyle: 'medium', timeStyle: 'short' })})`
                      : 'Leave empty to post immediately',
                    InputLabelProps: {
                      sx: { fontSize: '1.1rem' },
                    },
                  },
                }}
                sx={{ width: '100%', mt: 1, mb: 1 }}
              />
            )}

          <Box sx={{ display: 'flex', gap: 3, flexWrap: 'wrap', mb: 1, mt: 1 }}>
            <Box sx={{ flex: '1 1 45%', minWidth: '200px' }}>
              <DurationSelector
                value={formData.expectedDurationMinutes}
                onChange={handleDurationChange}
                error={!!durationError}
                helperText={durationError || undefined}
              />
            </Box>

            <Box sx={{ flex: '1 1 45%', minWidth: '200px' }}>
              <ReminderSelector
                value={formData.reminderMinutesArray}
                onChange={handleReminderChange}
                scheduledAt={formData.scheduledAt}
                error={!!reminderError}
                helperText={reminderError || 'Select one or more reminder times'}
              />
            </Box>
          </Box>

          <Box sx={{ mt: 1, mb: 1 }}>
            <RecurrenceSelector
              scheduledAt={formData.scheduledAt}
              value={formData.recurRule}
              onChange={(rule) => setFormData((prev) => ({ ...prev, recurRule: rule }))}
            />
          </Box>

          {canChangeChannel ? (
            <FormControl fullWidth margin="normal" required sx={{ mb: 1 }}>
              <InputLabel sx={{ fontSize: '1.1rem' }}>Channel</InputLabel>
              <Select
                value={formData.channelId}
                onChange={handleSelectChange}
                label="Channel"
                disabled={loading}
              >
                {channels.map((channel) => (
                  <MenuItem key={channel.id} value={channel.id}>
                    # {channel.channel_name}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          ) : (
            <Box sx={{ mb: 2 }}>
              <Typography variant="body1" sx={{ fontSize: '1.1rem' }}>
                <strong>Channel:</strong> #{' '}
                {channels.find((c) => c.id === formData.channelId)?.channel_name || 'Unknown'}
              </Typography>
            </Box>
          )}

          <FormControl fullWidth margin="normal" sx={{ mb: 1 }}>
            <InputLabel sx={{ fontSize: '1.1rem' }}>Signup Method</InputLabel>
            <Select
              value={
                formData.signupMethod === SignupMethod.HOST_SELECTED_WITH_WAITLIST
                  ? SignupMethod.HOST_SELECTED
                  : formData.signupMethod
              }
              onChange={handleSelectChange}
              name="signupMethod"
              label="Signup Method"
              disabled={loading || availableSignupMethods.length === 1}
              data-testid="signup-method-select"
            >
              {availableSignupMethods.map((method) => (
                <MenuItem key={method} value={method}>
                  {SIGNUP_METHOD_INFO[method as SignupMethod].displayName}
                </MenuItem>
              ))}
            </Select>
            <Typography variant="caption" color="text.secondary" sx={{ mt: 0.5, ml: 1.5 }}>
              {SIGNUP_METHOD_INFO[formData.signupMethod as SignupMethod]?.description ||
                'Select how players can join this game'}
            </Typography>
          </FormControl>

          {(formData.signupMethod === SignupMethod.HOST_SELECTED ||
            formData.signupMethod === SignupMethod.HOST_SELECTED_WITH_WAITLIST) && (
            <FormControlLabel
              label="Players can join waitlist (host selects from queue)"
              sx={{ mb: 1, ml: 0.5 }}
              control={
                <Checkbox
                  checked={formData.signupMethod === SignupMethod.HOST_SELECTED_WITH_WAITLIST}
                  onChange={(e) =>
                    setFormData((prev) => ({
                      ...prev,
                      signupMethod: e.target.checked
                        ? SignupMethod.HOST_SELECTED_WITH_WAITLIST
                        : SignupMethod.HOST_SELECTED,
                    }))
                  }
                  disabled={loading}
                />
              }
            />
          )}

          <EditableParticipantList
            participants={formData.participants}
            onChange={handleParticipantsChange}
          />

          <TextField
            fullWidth
            required
            multiline
            minRows={6}
            label="Description"
            name="description"
            value={formData.description}
            onChange={handleChange}
            onBlur={validateDescriptionField}
            margin="normal"
            disabled={loading}
            helperText={getDescriptionHelperText()}
            error={!!descriptionError}
            InputLabelProps={{
              sx: { fontSize: '1.1rem' },
            }}
            sx={{ mb: 1 }}
          />

          <TextField
            fullWidth
            multiline
            minRows={6}
            label="Signup Instructions"
            name="signupInstructions"
            value={formData.signupInstructions}
            onChange={handleChange}
            onBlur={validateSignupInstructionsField}
            margin="normal"
            helperText={getSignupInstructionsHelperText()}
            error={!!signupInstructionsError}
            disabled={loading}
            sx={{ mb: 1 }}
          />

          <FormControlLabel
            control={
              <Checkbox
                checked={formData.remindHostRewards}
                onChange={(e) =>
                  setFormData((prev) => ({ ...prev, remindHostRewards: e.target.checked }))
                }
                disabled={loading}
              />
            }
            label="Remind me to add rewards when the game completes"
            sx={{ mt: 1, mb: 1 }}
          />

          <Grid container spacing={2} sx={{ mt: 1, mb: 2 }}>
            <Grid size={{ xs: 12, md: 6 }}>
              <TextField
                fullWidth
                label="Max Players"
                name="maxPlayers"
                type="number"
                value={formData.maxPlayers}
                onChange={handleChange}
                onBlur={validateMaxPlayersField}
                helperText={maxPlayersError || undefined}
                error={!!maxPlayersError}
                disabled={loading}
                inputProps={{ min: 1, max: 100 }}
                InputLabelProps={{
                  sx: { fontSize: '1.1rem' },
                }}
              />
            </Grid>
          </Grid>

          <Box sx={{ mt: 3, mb: 2 }}>
            <Typography variant="subtitle1" gutterBottom sx={{ fontWeight: 'bold' }}>
              Images (optional)
            </Typography>
            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Thumbnail Image
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Button variant="outlined" component="label" disabled={loading}>
                  Choose Thumbnail
                  <input
                    type="file"
                    hidden
                    accept="image/png,image/jpeg,image/gif,image/webp"
                    onChange={handleThumbnailChange}
                  />
                </Button>
                {formData.thumbnailFile && (
                  <Typography variant="body2">{formData.thumbnailFile.name}</Typography>
                )}
                {mode === 'edit' &&
                  initialData?.has_thumbnail &&
                  !formData.thumbnailFile &&
                  !formData.removeThumbnail && (
                    <Button
                      size="small"
                      color="error"
                      onClick={handleRemoveThumbnail}
                      disabled={loading}
                    >
                      Remove Thumbnail
                    </Button>
                  )}
              </Box>
            </Box>

            <Box sx={{ mt: 2 }}>
              <Typography variant="subtitle2" gutterBottom>
                Banner Image
              </Typography>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
                <Button variant="outlined" component="label" disabled={loading}>
                  Choose Banner
                  <input
                    type="file"
                    hidden
                    accept="image/png,image/jpeg,image/gif,image/webp"
                    onChange={handleImageChange}
                  />
                </Button>
                {formData.imageFile && (
                  <Typography variant="body2">{formData.imageFile.name}</Typography>
                )}
                {mode === 'edit' &&
                  initialData?.has_image &&
                  !formData.imageFile &&
                  !formData.removeImage && (
                    <Button
                      size="small"
                      color="error"
                      onClick={handleRemoveImage}
                      disabled={loading}
                    >
                      Remove Banner
                    </Button>
                  )}
              </Box>
            </Box>
          </Box>

          <Box sx={{ display: 'flex', gap: 2, mt: 3 }}>
            <Button type="submit" variant="contained" disabled={loading} fullWidth>
              {loading ? (
                <CircularProgress size={24} />
              ) : mode === 'create' ? (
                'Create Game'
              ) : (
                'Save Changes'
              )}
            </Button>
            {onSaveAndArchive &&
              formData.rewards.trim() !== '' &&
              initialData?.archive_channel_id && (
                <Button
                  variant="contained"
                  color="secondary"
                  disabled={loading}
                  fullWidth
                  onClick={async () => {
                    try {
                      setLoading(true);
                      setError(null);
                      await onSaveAndArchive(formData);
                    } catch (err: unknown) {
                      console.error('Failed to save and archive:', err);
                      const errorDetail = (err as any).response?.data?.detail;
                      const errorMessage =
                        typeof errorDetail === 'string'
                          ? errorDetail
                          : errorDetail?.message || 'Failed to save and archive. Please try again.';
                      setError(errorMessage);
                    } finally {
                      setLoading(false);
                    }
                  }}
                >
                  {loading ? <CircularProgress size={24} /> : 'Save and Archive'}
                </Button>
              )}
            <Button variant="outlined" onClick={onCancel} disabled={loading} fullWidth>
              Cancel
            </Button>
          </Box>
        </Box>
      </Paper>
    </LocalizationProvider>
  );
};
