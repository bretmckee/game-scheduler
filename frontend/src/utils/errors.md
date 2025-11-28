# Error Handling Utilities

## Overview

Type-safe error handling utilities for consistent API error handling across the application.

## Usage

### Basic Error Message Extraction

```typescript
import { getErrorMessage } from '../utils/errors';

try {
  await apiClient.post('/api/v1/games', payload);
} catch (err: unknown) {
  console.error('Failed to create game:', err);
  const errorMessage = getErrorMessage(err, 'Failed to create game. Please try again.');
  setError(errorMessage);
}
```

### Check Status Code

```typescript
import { hasStatusCode, getErrorDetail } from '../utils/errors';

try {
  await apiClient.put(`/api/v1/games/${gameId}`, payload);
} catch (err: unknown) {
  if (hasStatusCode(err, 422)) {
    const detail = getErrorDetail(err);
    if (detail?.error === 'invalid_mentions') {
      // Handle validation errors
      setValidationErrors(detail.invalid_mentions);
    }
  }
}
```

### Type Guard for Custom Logic

```typescript
import { isApiError } from '../utils/errors';

try {
  await apiClient.get('/api/v1/games');
} catch (err: unknown) {
  if (isApiError(err)) {
    // TypeScript knows err.response exists
    const status = err.response?.status;
    const detail = err.response?.data?.detail;
    // Custom handling based on status/detail
  }
}
```

## API

### `getErrorMessage(error: unknown, fallback?: string): string`

Extracts a user-friendly error message from any error type.

- Handles API errors with string or object details
- Falls back to Error.message for standard errors
- Returns custom fallback if no message found

### `isApiError(error: unknown): error is ApiError`

Type guard to safely check if an error is an API error.

### `hasStatusCode(error: unknown, statusCode: number): boolean`

Check if an API error has a specific HTTP status code.

### `getErrorDetail(error: unknown): ApiErrorDetail | null`

Extract structured error detail object from API error.

## Migration from Current Pattern

### Before (with type assertions)

```typescript
} catch (err: unknown) {
  const errorDetail = (err as any).response?.data?.detail;
  const errorMessage = typeof errorDetail === 'string'
    ? errorDetail
    : errorDetail?.message || 'Failed';
  setError(errorMessage);
}
```

### After (type-safe)

```typescript
} catch (err: unknown) {
  const errorMessage = getErrorMessage(err, 'Failed');
  setError(errorMessage);
}
```

## Benefits

- **Type Safety**: No more `as any` type assertions
- **Consistency**: Same error handling pattern everywhere
- **Maintainability**: Change error handling logic in one place
- **Testing**: Easy to mock and test error scenarios
