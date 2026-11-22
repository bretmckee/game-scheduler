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
import { render, screen } from '@testing-library/react';
import { MentionText } from '../MentionText';

const KALLISTI = '255400000000781377';
const LFG = '987600000000000001';

describe('MentionText', () => {
  it('renders token-free text unchanged', () => {
    const { container } = render(<MentionText text="Bring dice @someone in #general" />);

    expect(container.textContent).toBe('Bring dice @someone in #general');
    expect(screen.queryByTestId('member-chip')).not.toBeInTheDocument();
    expect(screen.queryByTestId('channel-chip')).not.toBeInTheDocument();
  });

  it('renders nothing for empty or missing text', () => {
    const { container } = render(
      <>
        <MentionText text="" />
        <MentionText text={null} />
        <MentionText text={undefined} />
      </>
    );

    expect(container).toBeEmptyDOMElement();
  });

  it('renders member and channel tokens as chips without exposing IDs', () => {
    const { container } = render(
      <MentionText text={`Ask <@${KALLISTI}|Kallisti of the Ruby Rose> in <#${LFG}|lfg> first`} />
    );

    expect(screen.getByTestId('member-chip')).toHaveTextContent('@Kallisti of the Ruby Rose');
    expect(screen.getByTestId('channel-chip')).toHaveTextContent('#lfg');
    expect(container.textContent).toBe('Ask @Kallisti of the Ruby Rose in #lfg first');
    expect(container.textContent).not.toContain(KALLISTI);
  });

  it('renders a departed member as the unknown-member chip', () => {
    const { container } = render(<MentionText text={`Ask <@${KALLISTI}|> first`} />);

    expect(screen.getByTestId('unknown-member-chip')).toBeInTheDocument();
    expect(screen.queryByTestId('member-chip')).not.toBeInTheDocument();
    expect(container.textContent).not.toContain(KALLISTI);
  });

  it('renders an unknown channel as the unknown-channel chip', () => {
    const { container } = render(<MentionText text={`Meet in <#${LFG}|>`} />);

    expect(screen.getByTestId('unknown-channel-chip')).toBeInTheDocument();
    expect(screen.queryByTestId('channel-chip')).not.toBeInTheDocument();
    expect(container.textContent).not.toContain(LFG);
  });

  it('truncates token-free text like the previous plain-text truncation', () => {
    const { container } = render(<MentionText text="abcdef ghijkl" maxLength={8} />);

    expect(container.textContent).toBe('abcdef g...');
  });

  it('does not truncate text that fits', () => {
    const { container } = render(
      <MentionText text={`Hi <@${KALLISTI}|Kal>`} maxLength={'Hi @Kal'.length} />
    );

    expect(container.textContent).toBe('Hi @Kal');
    expect(screen.getByTestId('member-chip')).toHaveTextContent('@Kal');
  });

  it('drops a mention that does not fit instead of cutting it in half', () => {
    const { container } = render(
      <MentionText text={`Hi <@${KALLISTI}|Kallisti of the Ruby Rose> later`} maxLength={10} />
    );

    expect(screen.queryByTestId('member-chip')).not.toBeInTheDocument();
    expect(container.textContent).toBe('Hi...');
    expect(container.textContent).not.toContain('<@');
  });

  it('keeps a whole mention and adds an ellipsis when the cut falls right after it', () => {
    const { container } = render(
      <MentionText text={`Hi <@${KALLISTI}|Kal> and more text`} maxLength={'Hi @Kal'.length} />
    );

    expect(screen.getByTestId('member-chip')).toHaveTextContent('@Kal');
    expect(container.textContent).toBe('Hi @Kal...');
  });
});
