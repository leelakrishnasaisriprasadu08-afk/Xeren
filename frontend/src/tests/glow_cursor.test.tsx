import { describe, it, expect } from 'vitest';
import { render, screen, fireEvent } from '@testing-library/react';
import { GlowCursor } from '../components/GlowCursor';

describe('GlowCursor Component Tests', () => {
  it('renders GlowCursor container and canvas', () => {
    render(<GlowCursor />);
    const container = screen.getByTestId('glow-cursor-container');
    const canvas = screen.getByTestId('glow-cursor-canvas');

    expect(container).toBeInTheDocument();
    expect(container).toHaveClass('glow-cursor');
    expect(canvas).toBeInTheDocument();
    expect(canvas).toHaveClass('glow-cursor__canvas');
    expect(canvas).toHaveAttribute('aria-hidden', 'true');
  });

  it('renders children content inside .glow-cursor__content', () => {
    render(
      <GlowCursor>
        <div data-testid="test-child">Interactive Content</div>
      </GlowCursor>
    );

    const child = screen.getByTestId('test-child');
    const contentWrap = screen.getByTestId('glow-cursor-content');

    expect(child).toBeInTheDocument();
    expect(child).toHaveTextContent('Interactive Content');
    expect(contentWrap).toBeInTheDocument();
    expect(contentWrap).toHaveClass('glow-cursor__content');
  });

  it('accepts custom styling, className, and data attributes', () => {
    render(
      <GlowCursor
        className="custom-glow-cursor"
        style={{ width: '400px', height: '300px' }}
        data-custom="glow-test"
      >
        <span>Content</span>
      </GlowCursor>
    );

    const container = screen.getByTestId('glow-cursor-container');
    expect(container).toHaveClass('glow-cursor');
    expect(container).toHaveClass('custom-glow-cursor');
    expect(container).toHaveStyle({ width: '400px', height: '300px' });
    expect(container).toHaveAttribute('data-custom', 'glow-test');
  });

  it('accepts all custom props without crashing', () => {
    const { unmount } = render(
      <GlowCursor
        color="#10b981"
        secondaryColor="#047857"
        trailLength={28}
        trailWidth={6}
        trailTaper={0.75}
        followSpeed={0.25}
        glowIntensity={2.2}
        glowSpread={1.4}
        hotspot={0.7}
        brightness={1.3}
        opacity={0.9}
        pulseSpeed={1.8}
        noiseStrength={0.05}
        idleFade={true}
        idleTimeout={600}
        fadeDuration={800}
        blendMode="screen"
        maxDevicePixelRatio={1.5}
        enabled={true}
      >
        <div>Custom Props Inner</div>
      </GlowCursor>
    );

    expect(screen.getByText('Custom Props Inner')).toBeInTheDocument();
    unmount();
  });

  it('handles pointer move, enter, and leave events gracefully', () => {
    render(
      <GlowCursor>
        <button type="button">Test Target</button>
      </GlowCursor>
    );

    const container = screen.getByTestId('glow-cursor-container');

    // Simulate pointer interactions
    fireEvent.pointerEnter(container, { clientX: 100, clientY: 100 });
    fireEvent.pointerMove(container, { clientX: 150, clientY: 120 });
    fireEvent.pointerMove(container, { clientX: 200, clientY: 150 });
    fireEvent.pointerLeave(container);

    expect(container).toBeInTheDocument();
  });

  it('cleans up event listeners and resources on unmount', () => {
    const { unmount } = render(<GlowCursor />);
    expect(screen.getByTestId('glow-cursor-container')).toBeInTheDocument();
    expect(() => unmount()).not.toThrow();
  });
});
