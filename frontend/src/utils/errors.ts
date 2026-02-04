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

/**
 * Type-safe error handling utilities for API errors.
 */

/**
 * Structure of errors returned from axios/API calls.
 */
export interface ApiError {
  response?: {
    status?: number;
    data?: {
      detail?: string | ApiErrorDetail;
    };
  };
  message?: string;
}

/**
 * Structured API error detail object.
 */
export interface ApiErrorDetail {
  error?: string;
  message?: string;
  [key: string]: unknown;
}

/**
 * Type guard to check if an unknown error is an API error.
 */
export function isApiError(error: unknown): error is ApiError {
  return (
    typeof error === 'object' &&
    error !== null &&
    'response' in error &&
    typeof (error as ApiError).response === 'object'
  );
}

/**
 * Extract a user-friendly error message from an unknown error.
 * Handles both string and object error details from API responses.
 *
 * @param error - The error to extract a message from
 * @param fallback - Default message if no specific message found
 * @returns User-friendly error message
 */
export function getErrorMessage(error: unknown, fallback = 'An error occurred'): string {
  if (isApiError(error)) {
    const detail = error.response?.data?.detail;

    if (typeof detail === 'string') {
      return detail;
    }

    if (typeof detail === 'object' && detail !== null) {
      return detail.message || fallback;
    }
  }

  if (error instanceof Error) {
    return error.message;
  }

  return fallback;
}

/**
 * Check if an API error has a specific status code.
 */
export function hasStatusCode(error: unknown, statusCode: number): boolean {
  return isApiError(error) && error.response?.status === statusCode;
}

/**
 * Extract structured error detail from API error.
 */
export function getErrorDetail(error: unknown): ApiErrorDetail | null {
  if (!isApiError(error)) {
    return null;
  }

  const detail = error.response?.data?.detail;

  if (typeof detail === 'object' && detail !== null) {
    return detail as ApiErrorDetail;
  }

  return null;
}
