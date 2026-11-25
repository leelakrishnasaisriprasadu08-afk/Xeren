import { render, screen } from '@testing-library/react'
import { describe, it, expect } from 'vitest'
import { XerenMascot } from '../components/XerenMascot/XerenMascot'

describe('3D Animated Black Ball with Eyes (Xeren)', () => {
  it('renders 3D black sphere body with emerald rim light and eye elements', () => {
    const { container } = render(<XerenMascot state="idle" />)

    expect(screen.getByTestId('xeren-mascot')).toBeInTheDocument()

    // 3D Sphere gradients exist
    expect(container.querySelector('#blackSphereGrad')).toBeInTheDocument()
    expect(container.querySelector('#emeraldRimLight')).toBeInTheDocument()

    // Core 3D ball body and 3D eye container
    expect(container.querySelector('.mascot-body-group')).toBeInTheDocument()
    expect(container.querySelector('.mascot-eyes-container')).toBeInTheDocument()
    expect(container.querySelector('.left-eye')).toBeInTheDocument()
    expect(container.querySelector('.right-eye')).toBeInTheDocument()
    expect(container.querySelector('.ball-ground-shadow')).toBeInTheDocument()
  })

  it('comes forward when actively doing work (speaking, thinking, listening)', () => {
    const { container, rerender } = render(<XerenMascot state="speaking" />)

    const ball = screen.getByTestId('xeren-mascot')
    expect(ball).toHaveClass('stage-come-forward')
    expect(container.querySelector('.mascot-talking-mouth')).toBeInTheDocument()

    rerender(<XerenMascot state="thinking" />)
    expect(ball).toHaveClass('stage-come-forward')

    rerender(<XerenMascot state="listening" />)
    expect(ball).toHaveClass('stage-come-forward')
  })

  it('glides back into gentle resting 3D hover after answering (idle or complete)', () => {
    const { rerender } = render(<XerenMascot state="speaking" />)
    const ball = screen.getByTestId('xeren-mascot')
    expect(ball).toHaveClass('stage-come-forward')

    rerender(<XerenMascot state="complete" />)
    expect(ball).toHaveClass('stage-go-back')

    rerender(<XerenMascot state="idle" />)
    expect(ball).toHaveClass('stage-go-back')
  })
})
