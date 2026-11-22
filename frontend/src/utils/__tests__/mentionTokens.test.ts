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

import { describe, it, expect } from 'vitest';
import { parseTokens, toEditorText, fromEditorText } from '../mentionTokens';

const KALLISTI = '255400000000781377';
const XANTHIAS = '255400000000999001';
const LFG = '987600000000000001';

describe('parseTokens', () => {
  it('returns token-free text as a single text segment', () => {
    expect(parseTokens('Bring dice')).toEqual([{ kind: 'text', text: 'Bring dice' }]);
  });

  it('returns no segments for empty text', () => {
    expect(parseTokens('')).toEqual([]);
  });

  it('splits text, user and channel tokens into segments', () => {
    expect(
      parseTokens(`Ask <@${KALLISTI}|Kallisti of the Ruby Rose> in <#${LFG}|lfg> first`)
    ).toEqual([
      { kind: 'text', text: 'Ask ' },
      { kind: 'user', id: KALLISTI, label: 'Kallisti of the Ruby Rose' },
      { kind: 'text', text: ' in ' },
      { kind: 'channel', id: LFG, label: 'lfg' },
      { kind: 'text', text: ' first' },
    ]);
  });

  it('maps an empty label to null for departed members and unknown channels', () => {
    expect(parseTokens(`<@${KALLISTI}|><#${LFG}|>`)).toEqual([
      { kind: 'user', id: KALLISTI, label: null },
      { kind: 'channel', id: LFG, label: null },
    ]);
  });

  it.each(['Bob (DM)', '@@@', 'a|b', 'x @y', '  spaced  '])(
    'keeps label %j unmodified',
    (label) => {
      expect(parseTokens(`<@${KALLISTI}|${label}>`)).toEqual([
        { kind: 'user', id: KALLISTI, label },
      ]);
    }
  );

  it.each([`<@${KALLISTI}>`, '<@abc|Bob>', '<#lfg|lfg>', '<@|Bob>'])(
    'leaves %j as plain text',
    (text) => {
      expect(parseTokens(text)).toEqual([{ kind: 'text', text }]);
    }
  );
});

describe('toEditorText', () => {
  it('is the identity for token-free text', () => {
    const text = 'Bring dice @someone and #general';
    expect(toEditorText(text)).toEqual({ raw: text, display: text, map: {}, removedCount: 0 });
  });

  it('shows users as @label and channels as #label and records their IDs', () => {
    const state = toEditorText(`Ask <@${KALLISTI}|Kallisti> in <#${LFG}|lfg>`);

    expect(state.display).toBe('Ask @Kallisti in #lfg');
    expect(state.map).toEqual({ '@Kallisti': `<@${KALLISTI}>`, '#lfg': `<#${LFG}>` });
    expect(state.removedCount).toBe(0);
  });

  it('keeps the collapsed form of the original as raw', () => {
    const state = toEditorText(`Ask <@${KALLISTI}|Kallisti> in <#${LFG}|lfg>`);

    expect(state.raw).toBe(`Ask <@${KALLISTI}> in <#${LFG}>`);
  });

  it('removes departed members and unknown channels and counts them', () => {
    const state = toEditorText(`Ask <@${KALLISTI}|> or <@${XANTHIAS}|Xan> in <#${LFG}|>`);

    expect(state.display).toBe('Ask  or @Xan in ');
    expect(state.removedCount).toBe(2);
    expect(state.map).toEqual({ '@Xan': `<@${XANTHIAS}>` });
  });

  it('marks a label shared by two different IDs as ambiguous', () => {
    const state = toEditorText(`<@${KALLISTI}|Kal> and <@${XANTHIAS}|Kal>`);

    expect(state.display).toBe('@Kal and @Kal');
    expect(state.map).toEqual({ '@Kal': null });
  });

  it('maps a label repeated for the same ID normally', () => {
    const state = toEditorText(`<@${KALLISTI}|Kal> and <@${KALLISTI}|Kal>`);

    expect(state.map).toEqual({ '@Kal': `<@${KALLISTI}>` });
  });
});

describe('fromEditorText', () => {
  it('returns the collapsed raw original byte-identical when unedited', () => {
    const state = toEditorText(`Ask <@${KALLISTI}|Kal> or <@${XANTHIAS}|Kal> in <#${LFG}|lfg>`);

    expect(fromEditorText(state.display, state)).toBe(
      `Ask <@${KALLISTI}> or <@${XANTHIAS}> in <#${LFG}>`
    );
  });

  it('returns token-free text unchanged', () => {
    const text = 'Bring dice @someone';
    expect(fromEditorText(text, toEditorText(text))).toBe(text);
  });

  it('maps labels back to IDs after an edit', () => {
    const state = toEditorText(`Ask <@${KALLISTI}|Kallisti> in <#${LFG}|lfg>`);

    expect(fromEditorText(`${state.display} today`, state)).toBe(
      `Ask <@${KALLISTI}> in <#${LFG}> today`
    );
  });

  it('does not restore removed departed members when the text is unedited', () => {
    const state = toEditorText(`Ask <@${KALLISTI}|> or <@${XANTHIAS}|Xan>`);

    expect(fromEditorText(state.display, state)).toBe(`Ask  or <@${XANTHIAS}>`);
  });

  it('matches the longest label first', () => {
    const state = toEditorText(`<@${KALLISTI}|Al> <@${XANTHIAS}|Al Smith>`);

    expect(fromEditorText(`@Al Smith then @Al.`, state)).toBe(
      `<@${XANTHIAS}> then <@${KALLISTI}>.`
    );
  });

  it('does not map a known label that is only the prefix of a longer typed name', () => {
    const state = toEditorText(`<@${KALLISTI}|Kal>`);

    expect(fromEditorText('@Kallisti and @Kal', state)).toBe(`@Kallisti and <@${KALLISTI}>`);
  });

  it('leaves an ambiguous label as typed so the server asks', () => {
    const state = toEditorText(`<@${KALLISTI}|Kal> and <@${XANTHIAS}|Kal>`);

    expect(fromEditorText('@Kal and @Kal!', state)).toBe('@Kal and @Kal!');
  });

  it('leaves a damaged label and a newly typed name as typed', () => {
    const state = toEditorText(`Ask <@${KALLISTI}|Kallisti>`);

    expect(fromEditorText('Ask @Kallist and @newperson', state)).toBe(
      'Ask @Kallist and @newperson'
    );
  });

  it.each(['Kallisti of the Ruby Rose', 'Bob (DM)', 'x@y', 'a|b', '@@@', 'Kal'])(
    'round-trips member label %j through an unrelated edit',
    (label) => {
      const raw = `Hi <@${KALLISTI}|${label}>, see <@${XANTHIAS}|${label} Two> in <#${LFG}|lfg-chat>`;
      const state = toEditorText(raw);
      const edited = `${state.display} — updated`;

      expect(fromEditorText(edited, state)).toBe(
        `Hi <@${KALLISTI}>, see <@${XANTHIAS}> in <#${LFG}> — updated`
      );
    }
  );
});
