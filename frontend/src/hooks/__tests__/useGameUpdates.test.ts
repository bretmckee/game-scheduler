// Copyright 2026 Bret McKee
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

import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { renderHook } from '@testing-library/react';
import { useGameUpdates } from '../useGameUpdates';

class MockEventSource {
  url: string;
  withCredentials: boolean;
  readyState: number = 1; // OPEN
  onmessage: ((event: any) => void) | null = null;
  onerror: (() => void) | null = null;
  onopen: (() => void) | null = null;
  close = vi.fn();

  constructor(url: string, options?: { withCredentials?: boolean }) {
    this.url = url;
    this.withCredentials = options?.withCredentials || false;
    mockEventSourceInstances.push(this);
  }
}

let mockEventSourceInstances: MockEventSource[] = [];

describe('useGameUpdates', () => {
  const createEventData = (gameId: string, guildId?: string, type = 'game_updated') => ({
    type,
    game_id: gameId,
    ...(guildId ? { guild_id: guildId } : {}),
  });

  const triggerMessage = (data: any, instanceIndex = 0) => {
    mockEventSourceInstances[instanceIndex]!.onmessage!({
      data: JSON.stringify(data),
    });
  };

  const setupConsoleErrorSpy = () => vi.spyOn(console, 'error').mockImplementation(() => {});

  beforeEach(() => {
    mockEventSourceInstances = [];
    globalThis.EventSource = MockEventSource as any;
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it('creates EventSource with correct URL and credentials', () => {
    const onUpdate = vi.fn();

    renderHook(() => useGameUpdates('guild-123', onUpdate));

    expect(mockEventSourceInstances).toHaveLength(1);
    expect(mockEventSourceInstances[0]!.url).toBe('/api/v1/sse/game-updates');
    expect(mockEventSourceInstances[0]!.withCredentials).toBe(true);
  });

  it('calls onUpdate when game_updated event received with matching guild', () => {
    const onUpdate = vi.fn();

    renderHook(() => useGameUpdates('guild-123', onUpdate));

    const eventData = {
      type: 'game_updated',
      game_id: 'game-456',
      guild_id: 'guild-123',
    };

    mockEventSourceInstances[0]!.onmessage!({
      data: JSON.stringify(eventData),
    });

    expect(onUpdate).toHaveBeenCalledWith('game-456');
  });

  it('does not call onUpdate when guild_id does not match', () => {
    const onUpdate = vi.fn();

    renderHook(() => useGameUpdates('guild-123', onUpdate));

    const eventData = createEventData('game-456', 'guild-999');

    triggerMessage(eventData);

    expect(onUpdate).not.toHaveBeenCalled();
  });

  it('calls onUpdate for any guild when guildId is undefined', () => {
    const onUpdate = vi.fn();

    renderHook(() => useGameUpdates(undefined, onUpdate));

    const eventData = createEventData('game-456', 'guild-999');

    triggerMessage(eventData);

    expect(onUpdate).toHaveBeenCalledWith('game-456');
  });

  it('does not call onUpdate for non-game_updated events', () => {
    const onUpdate = vi.fn();

    renderHook(() => useGameUpdates('guild-123', onUpdate));

    const eventData = createEventData('game-456', 'guild-123', 'other_event');

    triggerMessage(eventData);

    expect(onUpdate).not.toHaveBeenCalled();
  });

  it('handles JSON parse errors gracefully', () => {
    const onUpdate = vi.fn();
    const consoleErrorSpy = setupConsoleErrorSpy();

    renderHook(() => useGameUpdates('guild-123', onUpdate));

    mockEventSourceInstances[0]!.onmessage!({
      data: 'invalid json',
    });

    expect(onUpdate).not.toHaveBeenCalled();
    expect(consoleErrorSpy).toHaveBeenCalledWith('[SSE] Failed to parse event:', expect.any(Error));
  });

  it('does not log on EventSource error', () => {
    const onUpdate = vi.fn();
    const consoleErrorSpy = setupConsoleErrorSpy();

    renderHook(() => useGameUpdates('guild-123', onUpdate));

    mockEventSourceInstances[0]!.onerror!();

    // EventSource onerror handler is empty (no logging) as EventSource handles reconnection automatically
    expect(consoleErrorSpy).not.toHaveBeenCalled();
  });

  it('closes EventSource on unmount', () => {
    const onUpdate = vi.fn();

    const { unmount } = renderHook(() => useGameUpdates('guild-123', onUpdate));

    expect(mockEventSourceInstances[0]!.close).not.toHaveBeenCalled();

    unmount();

    expect(mockEventSourceInstances[0]!.close).toHaveBeenCalled();
  });

  it('recreates EventSource when guildId changes', () => {
    const onUpdate = vi.fn();

    const { rerender } = renderHook(({ guildId }) => useGameUpdates(guildId, onUpdate), {
      initialProps: { guildId: 'guild-123' },
    });

    expect(mockEventSourceInstances).toHaveLength(1);
    const firstInstance = mockEventSourceInstances[0]!;

    rerender({ guildId: 'guild-456' });

    expect(firstInstance.close).toHaveBeenCalled();
    expect(mockEventSourceInstances).toHaveLength(2);
  });

  it('handles keepalive messages', () => {
    const onUpdate = vi.fn();

    renderHook(() => useGameUpdates('guild-123', onUpdate));

    const keepaliveData = { type: 'keepalive' };
    triggerMessage(keepaliveData);

    expect(onUpdate).not.toHaveBeenCalled();
  });

  it('triggers reconnection on timeout', () => {
    vi.useFakeTimers();
    const onUpdate = vi.fn();

    const { rerender } = renderHook(() => useGameUpdates('guild-123', onUpdate));

    expect(mockEventSourceInstances).toHaveLength(1);
    const firstInstance = mockEventSourceInstances[0]!;

    // Advance time past the timeout check interval (10s) and timeout threshold (45s)
    vi.advanceTimersByTime(10000); // First timeout check
    vi.advanceTimersByTime(10000); // Second timeout check
    vi.advanceTimersByTime(10000); // Third timeout check
    vi.advanceTimersByTime(10000); // Fourth timeout check
    vi.advanceTimersByTime(10000); // Fifth timeout check - total 50s elapsed

    // Force a re-render to process the reconnectTrigger state change
    rerender();

    // Should have triggered reconnection (new EventSource created)
    expect(mockEventSourceInstances.length).toBeGreaterThan(1);
    expect(firstInstance.close).toHaveBeenCalled();

    vi.useRealTimers();
  });

  it('updates lastMessageTime on onopen', () => {
    const onUpdate = vi.fn();

    renderHook(() => useGameUpdates('guild-123', onUpdate));

    const eventSource = mockEventSourceInstances[0]!;
    expect(eventSource.onopen).toBeDefined();

    // Trigger onopen handler
    eventSource.onopen!();

    // No error should occur (lastMessageTime updated internally)
  });
});
