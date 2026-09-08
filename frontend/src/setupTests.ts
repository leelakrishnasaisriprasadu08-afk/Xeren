import '@testing-library/jest-dom/vitest'

// 1. Mock matchMedia
Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: (query: string) => ({
    matches: false,
    media: query,
    onchange: null,
    addListener: () => {},
    removeListener: () => {},
    addEventListener: () => {},
    removeEventListener: () => {},
    dispatchEvent: () => false,
  }),
})

// Mock IntersectionObserver
if (typeof window.IntersectionObserver === 'undefined') {
  class MockIntersectionObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  Object.defineProperty(window, 'IntersectionObserver', {
    writable: true,
    value: MockIntersectionObserver,
  })
}

// Mock ResizeObserver
if (typeof window.ResizeObserver === 'undefined') {
  class MockResizeObserver {
    observe() {}
    unobserve() {}
    disconnect() {}
  }
  Object.defineProperty(window, 'ResizeObserver', {
    writable: true,
    value: MockResizeObserver,
  })
}

// 2. Mock AudioContext & AudioNodes
class MockAudioNode {
  connect(target: any) {
    return target
  }
  disconnect() {}
}

class MockAudioParam {
  value = 0
  setValueAtTime(_val: number, _time: number) {
    this.value = _val
    return this
  }
  linearRampToValueAtTime(_val: number, _time: number) {
    this.value = _val
    return this
  }
  exponentialRampToValueAtTime(_val: number, _time: number) {
    this.value = _val
    return this
  }
  setTargetAtTime(_val: number, _time: number, _constant: number) {
    this.value = _val
    return this
  }
}

class MockGainNode extends MockAudioNode {
  gain = new MockAudioParam()
}

class MockOscillatorNode extends MockAudioNode {
  frequency = new MockAudioParam()
  type = 'sine'
  onended: (() => void) | null = null
  start(_time?: number) {}
  stop(_time?: number) {}
}

class MockBiquadFilterNode extends MockAudioNode {
  frequency = new MockAudioParam()
  Q = new MockAudioParam()
  type = 'lowpass'
}

class MockAnalyserNode extends MockAudioNode {
  fftSize = 128
  frequencyBinCount = 64
  getByteFrequencyData(array: Uint8Array) {
    array.fill(40)
  }
}

class MockAudioContext {
  state = 'running'
  currentTime = 0
  destination = new MockAudioNode()

  createMediaStreamSource() {
    return new MockAudioNode()
  }
  createAnalyser() {
    return new MockAnalyserNode()
  }
  createGain() {
    return new MockGainNode()
  }
  createOscillator() {
    return new MockOscillatorNode()
  }
  createBiquadFilter() {
    return new MockBiquadFilterNode()
  }
  resume = async () => {}
  close = async () => {}
}

Object.defineProperty(window, 'AudioContext', {
  writable: true,
  value: MockAudioContext,
})

Object.defineProperty(window, 'webkitAudioContext', {
  writable: true,
  value: MockAudioContext,
})

// 3. Mock SpeechSynthesis & Utterance
class MockSpeechSynthesisUtterance {
  text: string
  rate: number = 1
  pitch: number = 1
  voice: any = null
  onstart: (() => void) | null = null
  onend: (() => void) | null = null
  onerror: ((event: any) => void) | null = null

  constructor(text: string) {
    this.text = text
  }
}

const mockSpeechSynthesis = {
  speaking: false,
  pending: false,
  paused: false,
  getVoices: () => [
    { name: 'Natural English (US)', lang: 'en-US' },
  ],
  speak: (utterance: MockSpeechSynthesisUtterance) => {
    mockSpeechSynthesis.speaking = true
    utterance.onstart?.()
    setTimeout(() => {
      mockSpeechSynthesis.speaking = false
      utterance.onend?.()
    }, 50)
  },
  cancel: () => {
    mockSpeechSynthesis.speaking = false
  },
  pause: () => {},
  resume: () => {},
}

Object.defineProperty(window, 'SpeechSynthesisUtterance', {
  writable: true,
  value: MockSpeechSynthesisUtterance,
})

Object.defineProperty(window, 'speechSynthesis', {
  writable: true,
  value: mockSpeechSynthesis,
})

// 4. Mock navigator.mediaDevices
if (!navigator.mediaDevices) {
  Object.defineProperty(navigator, 'mediaDevices', {
    writable: true,
    value: {},
  })
}

Object.defineProperty(navigator.mediaDevices, 'getUserMedia', {
  writable: true,
  value: async () => {
    return {
      getTracks: () => [
        {
          stop: () => {},
          kind: 'audio',
        },
      ],
    }
  },
})

// 5. Mock requestAnimationFrame
if (!window.requestAnimationFrame) {
  window.requestAnimationFrame = (cb: FrameRequestCallback) => {
    return setTimeout(() => cb(performance.now()), 16) as unknown as number
  }
  window.cancelAnimationFrame = (id: number) => {
    clearTimeout(id)
  }
}

// 6. Mock HTMLCanvasElement getContext
const mockGradient = {
  addColorStop: () => {},
}

HTMLCanvasElement.prototype.getContext = function (
  this: HTMLCanvasElement,
  contextType: string
) {
  if (contextType === '2d') {
    return {
      fillRect: () => {},
      clearRect: () => {},
      getImageData: () => ({ data: new Array(4) }),
      putImageData: () => {},
      createImageData: () => [],
      setTransform: () => {},
      drawImage: () => {},
      save: () => {},
      fillText: () => {},
      restore: () => {},
      beginPath: () => {},
      moveTo: () => {},
      lineTo: () => {},
      quadraticCurveTo: () => {},
      closePath: () => {},
      stroke: () => {},
      arc: () => {},
      ellipse: () => {},
      fill: () => {},
      measureText: () => ({ width: 0 }),
      transform: () => {},
      translate: () => {},
      rotate: () => {},
      scale: () => {},
      setLineDash: () => {},
      rect: () => {},
      clip: () => {},
      createRadialGradient: () => mockGradient,
      createLinearGradient: () => mockGradient,
    } as unknown as CanvasRenderingContext2D
  }
  if (contextType === 'webgl' || contextType === 'webgl2' || contextType === 'experimental-webgl') {
    return {
      canvas: this,
      drawingBufferWidth: 800,
      drawingBufferHeight: 600,
      getExtension: () => ({
        loseContext: () => {},
      }),
      getParameter: (p: number) => {
        if (p === 0x1f00) return 'WebKit' // VENDOR
        if (p === 0x1f01) return 'WebKit WebGL' // RENDERER
        if (p === 0x1f02) return 'WebGL 1.0' // VERSION
        if (p === 0x8b36) return 'WebGL GLSL ES 1.0' // SHADING_LANGUAGE_VERSION
        if (p === 0x0d33) return 8192 // MAX_TEXTURE_SIZE
        if (p === 0x8872) return 16 // MAX_TEXTURE_IMAGE_UNITS
        if (p === 0x851c) return 8 // MAX_VERTEX_ATTRIBS
        return 0
      },
      enable: () => {},
      disable: () => {},
      depthFunc: () => {},
      blendFunc: () => {},
      blendEquation: () => {},
      blendFuncSeparate: () => {},
      cullFace: () => {},
      frontFace: () => {},
      scissor: () => {},
      viewport: () => {},
      clearColor: () => {},
      clearDepth: () => {},
      clearStencil: () => {},
      clear: () => {},
      colorMask: () => {},
      depthMask: () => {},
      createShader: () => ({}),
      shaderSource: () => {},
      compileShader: () => {},
      getShaderParameter: () => true,
      getShaderInfoLog: () => '',
      createProgram: () => ({}),
      attachShader: () => {},
      linkProgram: () => {},
      getProgramParameter: () => true,
      getProgramInfoLog: () => '',
      useProgram: () => {},
      createBuffer: () => ({}),
      bindBuffer: () => {},
      bufferData: () => {},
      bufferSubData: () => {},
      getUniformLocation: () => ({}),
      getAttribLocation: () => 0,
      enableVertexAttribArray: () => {},
      disableVertexAttribArray: () => {},
      vertexAttribPointer: () => {},
      uniform1f: () => {},
      uniform1i: () => {},
      uniform2f: () => {},
      uniform3f: () => {},
      uniform4f: () => {},
      uniformMatrix4fv: () => {},
      drawArrays: () => {},
      drawElements: () => {},
      createTexture: () => ({}),
      bindTexture: () => {},
      texParameteri: () => {},
      texImage2D: () => {},
      pixelStorei: () => {},
      deleteTexture: () => {},
      deleteProgram: () => {},
      deleteShader: () => {},
      deleteBuffer: () => {},
    } as unknown as WebGLRenderingContext
  }
  return null
} as any

// 7. Mock HTMLMediaElement play/pause
window.HTMLMediaElement.prototype.play = async () => {}
window.HTMLMediaElement.prototype.pause = () => {}
window.HTMLMediaElement.prototype.load = () => {}

