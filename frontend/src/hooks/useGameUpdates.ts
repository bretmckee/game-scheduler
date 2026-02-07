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

import { useEffect, useRef, useState } from 'react';

interface GameUpdateEvent {
  type: string;
  game_id: string;
  guild_id: string;
}

export function useGameUpdates(
  guildId: string | undefined,
  onUpdate: (gameId: string) => void
): void {
  const onUpdateRef = useRef(onUpdate);
  const [reconnectTrigger, setReconnectTrigger] = useState(0);

  useEffect(() => {
    onUpdateRef.current = onUpdate;
  }, [onUpdate]);

  useEffect(() => {
    const eventSource = new EventSource('/api/v1/sse/game-updates', {
      withCredentials: true,
    });

    let lastMessageTime = Date.now();
    const TIMEOUT_MS = 45000;
    const TIMEOUT_CHECK_INTERVAL_MS = 10000;

    eventSource.onopen = () => {
      lastMessageTime = Date.now();
    };

    eventSource.onmessage = (event) => {
      lastMessageTime = Date.now();

      try {
        const data: GameUpdateEvent = JSON.parse(event.data);

        if (data.type === 'keepalive') {
          return;
        }

        if (data.type === 'game_updated') {
          if (!guildId || data.guild_id === guildId) {
            onUpdateRef.current(data.game_id);
          }
        }
      } catch (error) {
        console.error('[SSE] Failed to parse event:', error);
      }
    };

    eventSource.onerror = () => {
      // EventSource will automatically attempt to reconnect
    };

    const timeoutCheckInterval = setInterval(() => {
      const timeSinceLastMessage = Date.now() - lastMessageTime;
      if (timeSinceLastMessage > TIMEOUT_MS && eventSource.readyState === 1) {
        setReconnectTrigger((prev) => prev + 1);
      }
    }, TIMEOUT_CHECK_INTERVAL_MS);

    return () => {
      clearInterval(timeoutCheckInterval);
      eventSource.close();
    };
  }, [guildId, reconnectTrigger]);
}
