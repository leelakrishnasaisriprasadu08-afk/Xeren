import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect } from 'vitest';
import Lightfall from '../components/Lightfall/Lightfall';

describe('Lightfall Component Tests', () => {
  it('renders container with data-testid="lightfall-container"', () => {
    render(<Lightfall />);
    const container = screen.getByTestId('lightfall-container');
    expect(container).toBeInTheDocument();
    expect(container).toHaveClass('lightfall-container');
  });

  it('renders with custom className and custom style mixBlendMode', () => {
    render(
      <Lightfall
        className="custom-lightfall-class"
        mixBlendMode="screen"
      />
    );
    const container = screen.getByTestId('lightfall-container');
    expect(container).toHaveClass('custom-lightfall-class');
    expect(container).toHaveStyle({ mixBlendMode: 'screen' });
  });

  it('renders stacked children inside the container', () => {
    render(
      <Lightfall>
        <div data-testid="test-child">Child Content</div>
      </Lightfall>
    );
    expect(screen.getByTestId('test-child')).toBeInTheDocument();
    expect(screen.getByText('Child Content')).toBeInTheDocument();
  });

  it('accepts all custom props without runtime errors', () => {
    const { unmount, rerender } = render(
      <Lightfall
        colors={['#A6C8FF', '#5227FF', '#FF9FFC']}
        backgroundColor="#0A29FF"
        speed={1}
        streakCount={8}
        streakWidth={1}
        streakLength={1}
        glow={1}
        density={1}
        twinkle={1}
        zoom={2}
        backgroundGlow={1}
        opacity={0.9}
        mouseInteraction={true}
        mouseStrength={1}
        mouseRadius={0.6}
        mouseDampening={0.15}
        paused={false}
      />
    );
    expect(screen.getByTestId('lightfall-container')).toBeInTheDocument();

    // Rerender with paused and different colors
    rerender(
      <Lightfall
        colors={['#00f0ff', '#a855f7']}
        backgroundColor="#050510"
        paused={true}
        speed={2}
      />
    );
    expect(screen.getByTestId('lightfall-container')).toBeInTheDocument();

    expect(() => unmount()).not.toThrow();
  });

  it('handles mouse pointer movement when mouseInteraction is true', () => {
    render(<Lightfall mouseInteraction={true} />);
    const container = screen.getByTestId('lightfall-container');
    
    // Simulate pointer move over container
    fireEvent.pointerMove(container, { clientX: 100, clientY: 150 });
    expect(container).toBeInTheDocument();
  });

  it('cleans up resources cleanly on unmount', () => {
    const { unmount } = render(<Lightfall mouseInteraction={false} />);
    expect(() => unmount()).not.toThrow();
  });
});
