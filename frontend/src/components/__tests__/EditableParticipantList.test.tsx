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

import { describe, it, expect, vi } from 'vitest';
import { render, fireEvent } from '@testing-library/react';
import { EditableParticipantList } from '../EditableParticipantList';
import type { ParticipantInput } from '../EditableParticipantList';

const makeParticipant = (id: string): ParticipantInput => ({
  id,
  mention: `@user${id}`,
  preFillPosition: 1,
  isExplicitlyPositioned: false,
  validationStatus: 'unknown',
});

const makeOpenSlot = (index: number): ParticipantInput => ({
  id: `open-slot-${index}`,
  mention: '',
  preFillPosition: index + 1,
  isOpenSlot: true,
  isExplicitlyPositioned: false,
  validationStatus: 'valid',
});

describe('EditableParticipantList - open slot placeholders', () => {
  it('should render normally without open slot entries', () => {
    const participants = [makeParticipant('1')];
    const { queryAllByText } = render(
      <EditableParticipantList participants={participants} onChange={vi.fn()} />
    );
    expect(queryAllByText(/open slot/i)).toHaveLength(0);
  });

  it('should render open slot entries when included in participants', () => {
    const participants = [makeParticipant('1'), makeOpenSlot(1), makeOpenSlot(2)];
    const { getAllByText } = render(
      <EditableParticipantList participants={participants} onChange={vi.fn()} />
    );

    const openSlots = getAllByText(/open slot/i);
    expect(openSlots).toHaveLength(2);
  });

  it('should not render open slot rows when none are included', () => {
    const participants = [makeParticipant('1'), makeParticipant('2')];
    const { queryAllByText } = render(
      <EditableParticipantList participants={participants} onChange={vi.fn()} />
    );
    expect(queryAllByText(/open slot/i)).toHaveLength(0);
  });

  it('should render open slot entries with italic styling', () => {
    const participants = [makeOpenSlot(0), makeOpenSlot(1)];
    const { getAllByText } = render(
      <EditableParticipantList participants={participants} onChange={vi.fn()} />
    );

    const openSlots = getAllByText(/open slot/i);
    openSlots.forEach((el) => {
      const style = window.getComputedStyle(el);
      expect(style.fontStyle).toBe('italic');
    });
  });

  it('should handle drag over and drop events on open slot rows', () => {
    const participants = [makeParticipant('1'), makeOpenSlot(1)];
    const onChange = vi.fn();
    const { getByText, getByDisplayValue } = render(
      <EditableParticipantList participants={participants} onChange={onChange} />
    );

    const openSlotText = getByText(/open slot/i);
    // Walk up: Typography -> styled Box -> inner Box -> outer Box (has onDragOver/onDrop)
    const outerBox = openSlotText.parentElement?.parentElement?.parentElement;
    expect(outerBox).not.toBeNull();

    // Initiate drag from the first participant to set draggedIndex state
    const draggable = getByDisplayValue('@user1').closest('[draggable="true"]');
    expect(draggable).not.toBeNull();
    fireEvent.dragStart(draggable!);

    fireEvent.dragOver(outerBox!);
    fireEvent.drop(outerBox!);

    expect(onChange).toHaveBeenCalled();
  });
});

describe('EditableParticipantList - resolvedMention clearing', () => {
  it('clears resolvedMention when the mention text is manually edited', () => {
    const onChange = vi.fn();
    const participant: ParticipantInput = {
      id: 'p1',
      mention: '@user',
      preFillPosition: 1,
      isExplicitlyPositioned: true,
      validationStatus: 'valid',
      resolvedMention: '<@123456>',
    };
    const { getByDisplayValue } = render(
      <EditableParticipantList participants={[participant]} onChange={onChange} />
    );
    fireEvent.change(getByDisplayValue('@user'), { target: { value: '@user edited' } });
    expect(onChange).toHaveBeenCalledWith(
      expect.arrayContaining([
        expect.objectContaining({ id: 'p1', mention: '@user edited', resolvedMention: undefined }),
      ])
    );
  });
});
