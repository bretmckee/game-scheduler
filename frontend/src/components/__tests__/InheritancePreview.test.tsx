import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { InheritancePreview } from '../InheritancePreview';

describe('InheritancePreview', () => {
  it('renders label and value correctly', () => {
    render(
      <InheritancePreview
        label="Max Players"
        value={10}
        inherited={false}
      />
    );

    expect(screen.getByText(/Max Players:/)).toBeInTheDocument();
    expect(screen.getByText('10')).toBeInTheDocument();
  });

  it('displays inherited indicator when inherited is true', () => {
    render(
      <InheritancePreview
        label="Max Players"
        value={10}
        inherited={true}
        inheritedFrom="guild"
      />
    );

    expect(screen.getByText(/Inherited from guild/)).toBeInTheDocument();
  });

  it('does not display inherited indicator when inherited is false', () => {
    render(
      <InheritancePreview
        label="Max Players"
        value={10}
        inherited={false}
      />
    );

    expect(screen.queryByText(/Inherited from/)).not.toBeInTheDocument();
  });

  it('formats array values with commas', () => {
    render(
      <InheritancePreview
        label="Reminder Times"
        value={[60, 15, 5]}
        inherited={false}
      />
    );

    expect(screen.getByText('60, 15, 5')).toBeInTheDocument();
  });

  it('displays "Not set" for null values', () => {
    render(
      <InheritancePreview
        label="Rules"
        value={null}
        inherited={false}
      />
    );

    expect(screen.getByText('Not set')).toBeInTheDocument();
  });
});
