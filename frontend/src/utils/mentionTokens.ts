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

/**
 * Pure helpers for the labeled mention tokens the API returns in game text
 * fields: `<@id|label>` for members and `<#id|label>` for channels. The ID is
 * authoritative; the label is a live, cosmetic display name and is never
 * persisted. An empty label marks a member who left or an unknown channel.
 */

export type MentionSegment =
  | { kind: 'text'; text: string }
  | { kind: 'user'; id: string; label: string | null }
  | { kind: 'channel'; id: string; label: string | null };

/**
 * Per-field editor state produced by `toEditorText`.
 *
 * `map` keys are the editor forms (`@label` / `#label`) and values are the bare
 * tokens they stand for. A `null` value marks a label shared by two different
 * IDs; it is deliberately left unmapped so the server asks which one was meant.
 */
export interface EditorTextState {
  raw: string;
  display: string;
  map: Record<string, string | null>;
  removedCount: number;
}

const TOKEN_PATTERN = /<([@#])(\d+)\|([^>]*)>/g;
const WORD_CHAR = /[\p{L}\p{N}_]/u;

/** Split text into plain-text, member and channel segments. */
export function parseTokens(text: string): MentionSegment[] {
  const segments: MentionSegment[] = [];
  let last = 0;
  for (const match of text.matchAll(TOKEN_PATTERN)) {
    const [whole, sigil, id, label] = match;
    const start = match.index;
    if (start > last) {
      segments.push({ kind: 'text', text: text.slice(last, start) });
    }
    segments.push({
      kind: sigil === '@' ? 'user' : 'channel',
      id: id!,
      label: label === '' ? null : label!,
    });
    last = start + whole.length;
  }
  if (last < text.length) {
    segments.push({ kind: 'text', text: text.slice(last) });
  }
  return segments;
}

/**
 * Convert API text into what the host edits: `@label` / `#label` instead of
 * tokens. Departed members and unknown channels have no name to show, so they
 * are dropped from the editor text and counted in `removedCount`.
 */
export function toEditorText(text: string): EditorTextState {
  const map: Record<string, string | null> = {};
  let raw = '';
  let display = '';
  let removedCount = 0;

  for (const segment of parseTokens(text)) {
    if (segment.kind === 'text') {
      raw += segment.text;
      display += segment.text;
      continue;
    }
    const token = segment.kind === 'user' ? `<@${segment.id}>` : `<#${segment.id}>`;
    raw += token;
    if (segment.label === null) {
      removedCount += 1;
      continue;
    }
    const editorForm = `${segment.kind === 'user' ? '@' : '#'}${segment.label}`;
    display += editorForm;
    const existing = map[editorForm];
    map[editorForm] = existing === undefined || existing === token ? token : null;
  }

  return { raw, display, map, removedCount };
}

/**
 * Convert edited editor text back into submit form.
 *
 * Unedited text with nothing removed returns the original verbatim, so a
 * re-save is byte-identical. Otherwise each known `@label` / `#label` becomes
 * its bare token, longest label first; ambiguous, damaged and new names are
 * left as typed for the server to resolve.
 */
export function fromEditorText(edited: string, state: EditorTextState): string {
  if (state.removedCount === 0 && edited === state.display) {
    return state.raw;
  }

  const labels = Object.keys(state.map).sort((a, b) => b.length - a.length);
  if (labels.length === 0) {
    return edited;
  }

  let result = '';
  let i = 0;
  while (i < edited.length) {
    const label = labels.find((candidate) => matchesAt(edited, i, candidate));
    if (label === undefined) {
      result += edited[i];
      i += 1;
      continue;
    }
    result += state.map[label] ?? label;
    i += label.length;
  }
  return result;
}

/**
 * True when `label` occurs at `index` and is not just the start of a longer
 * name (e.g. `@Kal` inside `@Kallisti`).
 */
function matchesAt(text: string, index: number, label: string): boolean {
  if (!text.startsWith(label, index)) {
    return false;
  }
  const next = text[index + label.length];
  const lastOfLabel = label[label.length - 1]!;
  return next === undefined || !WORD_CHAR.test(lastOfLabel) || !WORD_CHAR.test(next);
}
