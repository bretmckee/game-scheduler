import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { MentionChip } from '../MentionChip';

describe('MentionChip', () => {
  it('renders username and display name correctly', () => {
    const onClick = vi.fn();
    render(
      <MentionChip 
        username="johndoe" 
        displayName="John Doe" 
        onClick={onClick} 
      />
    );

    expect(screen.getByText(/@johndoe \(John Doe\)/)).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const onClick = vi.fn();
    const user = userEvent.setup();
    
    render(
      <MentionChip 
        username="johndoe" 
        displayName="John Doe" 
        onClick={onClick} 
      />
    );

    const chip = screen.getByText(/@johndoe \(John Doe\)/);
    await user.click(chip);

    expect(onClick).toHaveBeenCalledTimes(1);
  });

  it('renders as a clickable chip', () => {
    const onClick = vi.fn();
    render(
      <MentionChip 
        username="johndoe" 
        displayName="John Doe" 
        onClick={onClick} 
      />
    );

    const chip = screen.getByText(/@johndoe \(John Doe\)/);
    expect(chip).toBeVisible();
  });
});
