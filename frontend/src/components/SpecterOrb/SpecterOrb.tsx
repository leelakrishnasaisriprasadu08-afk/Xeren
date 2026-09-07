import React, {
  useRef,
  useState,
  useMemo,
  useCallback,
  useEffect,
  useSyncExternalStore,
  type ReactNode,
} from 'react'
import { Canvas, useFrame, useThree } from '@react-three/fiber'
import * as THREE from 'three'
import { cn } from '@/lib/utils'
import './SpecterOrb.css'

const vertexShader = /* glsl */ `
varying vec2 vPlane;

void main() {
  vPlane = uv;
  gl_Position = vec4(position.xy, 0.0, 1.0);
}
`

const fragmentShader = /* glsl */ `
precision highp float;

varying vec2 vPlane;
uniform vec2 uCanvas;
uniform float uClock;
uniform float uCore;
uniform float uSwell;
uniform float uGrain;
uniform float uFlow;
uniform int uBands;
uniform float uDecay;
uniform float uClimb;
uniform float uNorm;
uniform int uSteps;
uniform float uStride;
uniform float uZoom;
uniform float uMaskRadius;
uniform float uMaskFeather;
uniform vec3 uInkA;
uniform vec3 uInkB;
uniform vec3 uInkC;
uniform float uRim;
uniform float uRimShape;
uniform vec3 uSheenA;
uniform vec3 uSheenB;
uniform float uSheen;
uniform float uSheenTight;
uniform float uHaze;
uniform float uHazeTight;
uniform float uGamma;
uniform float uGain;
uniform float uOpacity;
uniform vec3 uBackdrop;
uniform float uBackdropAlpha;
uniform vec2 uSwing;

const float SKIN = 0.002;

float spark(vec3 cell) {
  cell = fract(cell * 0.3183099 + vec3(0.71, 0.113, 0.419));
  cell *= 17.0;
  return fract(cell.x * cell.y * cell.z * (cell.x + cell.y + cell.z));
}

float wisp(vec3 spot) {
  vec3 anchor = floor(spot);
  vec3 lean = fract(spot);
  lean = lean * lean * (3.0 - 2.0 * lean);
  float n000 = spark(anchor + vec3(0.0, 0.0, 0.0));
  float n100 = spark(anchor + vec3(1.0, 0.0, 0.0));
  float n010 = spark(anchor + vec3(0.0, 1.0, 0.0));
  float n110 = spark(anchor + vec3(1.0, 1.0, 0.0));
  float n001 = spark(anchor + vec3(0.0, 0.0, 1.0));
  float n101 = spark(anchor + vec3(1.0, 0.0, 1.0));
  float n011 = spark(anchor + vec3(0.0, 1.0, 1.0));
  float n111 = spark(anchor + vec3(1.0, 1.0, 1.0));
  return mix(
    mix(mix(n000, n100, lean.x), mix(n010, n110, lean.x), lean.y),
    mix(mix(n001, n101, lean.x), mix(n011, n111, lean.x), lean.y),
    lean.z
  );
}

float shell(vec3 spot) {
  vec3 probe = spot * uGrain + vec3(0.0, 0.0, uClock * uFlow);
  float sum = 0.0;
  float amp = 1.0;
  for (int i = 0; i < 5; i++) {
    if (i >= uBands) break;
    sum += wisp(probe) * amp;
    probe *= uClimb;
    amp *= uDecay;
  }
  return sum * uNorm;
}

float field(vec3 spot) {
  return length(spot) - uCore - shell(spot) * uSwell;
}

vec3 slope(vec3 spot) {
  vec2 nudge = vec2(0.0025, 0.0);
  float here = field(spot);
  return normalize(
    here - vec3(
      field(spot - nudge.xyy),
      field(spot - nudge.yxy),
      field(spot - nudge.yyx)
    )
  );
}

float rimTerm(vec3 normal, vec3 ray, vec3 axis) {
  float lean = sqrt(max(dot(normal, axis), 0.0)) * 1.5 - dot(normal, -ray);
  return pow(max(lean, 0.0), uRimShape);
}

float gloss(vec3 toLight, vec3 toEye, vec3 normal, float tight) {
  vec3 between = normalize(toLight + toEye);
  return pow(max(dot(normal, between), 0.0), tight);
}

void main() {
  vec2 plane = vPlane * 2.0 - 1.0;
  float aspect = uCanvas.x / max(uCanvas.y, 1.0);
  if (aspect >= 1.0) {
    plane.x *= aspect;
  } else {
    plane.y /= aspect;
  }
  plane /= max(uZoom, 0.05);

  float span = length(plane);
  // Fully open orb: no artificial circular disc cutout clamping the smoke or edges
  float disc = (uMaskRadius <= 0.0 || uMaskRadius >= 5.0)
    ? 1.0
    : (1.0 - smoothstep(uMaskRadius - uMaskFeather, uMaskRadius, span));

  vec3 lit = vec3(0.0);

  if (disc > 0.0) {
    vec3 eye = vec3(0.0, 0.0, -1.0);
    vec3 ray = normalize(vec3(plane, 1.0));

    float hull = uCore + uSwell;
    float toward = dot(eye, ray);
    float gap = dot(eye, eye) - hull * hull;
    float root = toward * toward - gap;

    if (root < 0.0) {
      vec3 grazed = eye + ray * max(-toward, 0.0);
      float nearest = max(field(grazed), 0.0);
      vec3 wash = max(dot(plane, vec2(0.707)), 0.0) * uInkA
        + max(dot(plane, vec2(-0.707)), 0.0) * uInkB
        + uInkC;
      lit = pow(max(1.0 - nearest, 0.0), uHazeTight) * wash * uHaze;
    } else {
      float reach = sqrt(root);
      float travel = max(-toward - reach, 0.0);
      float limit = -toward + reach;
      float nearest = 1.0e9;
      bool struck = false;
      vec3 landed = eye + ray * travel;

      for (int i = 0; i < 96; i++) {
        if (i >= uSteps) break;
        vec3 at = eye + ray * travel;
        float march = field(at);
        nearest = min(nearest, march);
        if (march < SKIN) {
          struck = true;
          landed = at;
          break;
        }
        travel += max(march * uStride, SKIN);
        if (travel > limit) break;
      }

      if (!struck) {
        vec3 wash = max(dot(plane, vec2(0.707)), 0.0) * uInkA
          + max(dot(plane, vec2(-0.707)), 0.0) * uInkB
          + uInkC;
        lit = pow(max(1.0 - max(nearest, 0.0), 0.0), uHazeTight) * wash * uHaze;
      } else {
        vec3 normal = slope(landed);
        vec3 toEye = normalize(eye - landed);

        vec3 axis = normalize(vec3(0.707 + uSwing.x, 0.707 + uSwing.y, 0.0));
        lit += uInkA * rimTerm(normal, ray, axis) * uRim;
        lit += uInkB * rimTerm(normal, ray, -axis) * uRim;
        lit += uInkC * rimTerm(normal, ray, vec3(0.0, 0.0, -1.0)) * uRim * 0.667;

        vec3 keyDir = normalize(vec3(0.6 + uSwing.x, 0.8 + uSwing.y, -0.5));
        vec3 fillDir = normalize(vec3(-0.6 + uSwing.x, -0.8 + uSwing.y, 0.0));
        lit += uSheenA * gloss(keyDir, toEye, normal, uSheenTight) * uSheen;
        lit += uSheenB * gloss(fillDir, toEye, normal, uSheenTight * 1.33) * uSheen * 0.75;
      }
    }

    lit = pow(max(lit, 0.0), vec3(uGamma));
  }

  lit *= uGain * disc;

  float cover = clamp(max(lit.r, max(lit.g, lit.b)), 0.0, 1.0);
  float rest = uBackdropAlpha * (1.0 - cover);
  gl_FragColor = vec4(lit + uBackdrop * rest, cover + rest) * uOpacity;
}
`

const clamp = (val: number, min: number, max: number): number =>
  Math.min(Math.max(val, min), max)

const isTransparent = (val: string): boolean => {
  const s = val.trim().toLowerCase()
  return s === 'transparent' || s === 'none' || s === ''
}

interface SwingState {
  x: number
  y: number
  toX: number
  toY: number
}

export interface SpecterOrbProps {
  width?: string | number
  height?: string | number
  className?: string
  children?: ReactNode
  radius?: number
  turbulence?: number
  noiseScale?: number
  flowSpeed?: number
  octaves?: number
  roughness?: number
  lacunarity?: number
  steps?: number
  stride?: number
  zoom?: number
  maskRadius?: number
  maskFeather?: number
  colorA?: string
  colorB?: string
  colorC?: string
  rimStrength?: number
  rimPower?: number
  specularColorA?: string
  specularColorB?: string
  specularStrength?: number
  specularSharpness?: number
  glowStrength?: number
  glowFalloff?: number
  gamma?: number
  brightness?: number
  opacity?: number
  backgroundColor?: string
  cursorInteraction?: boolean
  cursorLight?: number
  adaptiveQuality?: boolean
  targetFps?: number
  dpr?: number
  paused?: boolean
}

interface InnerMeshProps {
  awake: boolean
  ceiling: number
  readSwing: () => SwingState
  radius: number
  turbulence: number
  noiseScale: number
  flowSpeed: number
  octaves: number
  roughness: number
  lacunarity: number
  steps: number
  stride: number
  zoom: number
  maskRadius: number
  maskFeather: number
  colorA: string
  colorB: string
  colorC: string
  rimStrength: number
  rimPower: number
  specularColorA: string
  specularColorB: string
  specularStrength: number
  specularSharpness: number
  glowStrength: number
  glowFalloff: number
  gamma: number
  brightness: number
  opacity: number
  backgroundColor: string
  cursorInteraction: boolean
  cursorLight: number
  adaptiveQuality: boolean
  targetFps: number
  paused: boolean
}

const SpecterOrbMesh: React.FC<InnerMeshProps> = ({
  awake,
  ceiling,
  readSwing,
  radius,
  turbulence,
  noiseScale,
  flowSpeed,
  octaves,
  roughness,
  lacunarity,
  steps,
  stride,
  zoom,
  maskRadius,
  maskFeather,
  colorA,
  colorB,
  colorC,
  rimStrength,
  rimPower,
  specularColorA,
  specularColorB,
  specularStrength,
  specularSharpness,
  glowStrength,
  glowFalloff,
  gamma,
  brightness,
  opacity,
  backgroundColor,
  cursorInteraction,
  cursorLight,
  adaptiveQuality,
  targetFps,
  paused,
}) => {
  const { gl, invalidate, setDpr } = useThree()
  const materialRef = useRef<THREE.ShaderMaterial | null>(null)
  const clockRef = useRef(0)
  const qualityRef = useRef({
    scale: ceiling,
    frames: 0,
    span: 0,
    wins: 0,
    roof: Infinity,
  })
  const [reducedMotion, setReducedMotion] = useState(false)

  const octaveParams = useMemo(() => {
    const bands = clamp(Math.round(octaves), 1, 5)
    const decay = clamp(roughness, 0.05, 0.95)
    const climb = Math.max(lacunarity, 1.1)
    let amp = 1
    let normSum = 0
    for (let i = 0; i < bands; i++) {
      normSum += amp
      amp *= decay
    }
    return {
      bands,
      decay,
      climb,
      norm: normSum > 0 ? 1 / normSum : 1,
    }
  }, [octaves, roughness, lacunarity])

  useEffect(() => {
    if (typeof window === 'undefined') return
    const media = window.matchMedia('(prefers-reduced-motion: reduce)')
    const handler = () => setReducedMotion(media.matches)
    handler()
    media.addEventListener('change', handler)
    return () => media.removeEventListener('change', handler)
  }, [])

  useEffect(() => {
    const q = qualityRef.current
    q.scale = ceiling
    q.roof = Infinity
    q.wins = 0
    setDpr(ceiling)
  }, [ceiling, setDpr])

  const uniforms = useMemo(
    () => ({
      uBands: { value: 3 },
      uDecay: { value: 0.5 },
      uClimb: { value: 2.0 },
      uNorm: { value: 1.0 },
      uCanvas: { value: new THREE.Vector2(1, 1) },
      uClock: { value: 0 },
      uCore: { value: 0.35 },
      uSwell: { value: 0.3 },
      uGrain: { value: 1.0 },
      uFlow: { value: 0.3 },
      uSteps: { value: 32 },
      uStride: { value: 1.0 },
      uZoom: { value: 1.0 },
      uMaskRadius: { value: 0 },
      uMaskFeather: { value: 0.02 },
      uInkA: { value: new THREE.Color('#4da6ff') },
      uInkB: { value: new THREE.Color('#9959ff') },
      uInkC: { value: new THREE.Color('#6680ff') },
      uRim: { value: 0.75 },
      uRimShape: { value: 3.0 },
      uSheenA: { value: new THREE.Color('#669fff') },
      uSheenB: { value: new THREE.Color('#998fff') },
      uSheen: { value: 1.0 },
      uSheenTight: { value: 12.0 },
      uHaze: { value: 1.0 },
      uHazeTight: { value: 32.0 },
      uGamma: { value: 1.25 },
      uGain: { value: 1.0 },
      uOpacity: { value: 1.0 },
      uBackdrop: { value: new THREE.Color('#0a0a0a') },
      uBackdropAlpha: { value: 1.0 },
      uSwing: { value: new THREE.Vector2(0, 0) },
    }),
    []
  )

  useFrame((_state, delta) => {
    const mat = materialRef.current
    if (!mat || !awake) return

    const dt = Math.min(delta, 0.05)
    if (!paused && !reducedMotion) {
      clockRef.current += dt
    }

    const u = mat.uniforms
    const size = gl.getDrawingBufferSize(new THREE.Vector2())

    u.uBands.value = octaveParams.bands
    u.uDecay.value = octaveParams.decay
    u.uClimb.value = octaveParams.climb
    u.uNorm.value = octaveParams.norm
    u.uCanvas.value.set(Math.max(size.x, 1), Math.max(size.y, 1))
    u.uClock.value = clockRef.current
    u.uCore.value = Math.max(radius, 0.02)
    u.uSwell.value = Math.max(turbulence, 0)
    u.uGrain.value = Math.max(noiseScale, 0.05)
    u.uFlow.value = flowSpeed
    u.uSteps.value = clamp(Math.round(steps), 4, 96)
    u.uStride.value = clamp(stride, 0.25, 1.5)
    u.uZoom.value = Math.max(zoom, 0.1)
    u.uMaskRadius.value = Math.max(maskRadius, 0)
    u.uMaskFeather.value = clamp(maskFeather, 0.001, 1.0)
    u.uInkA.value.set(colorA)
    u.uInkB.value.set(colorB)
    u.uInkC.value.set(colorC)
    u.uRim.value = Math.max(rimStrength, 0)
    u.uRimShape.value = Math.max(rimPower, 0.2)
    u.uSheenA.value.set(specularColorA)
    u.uSheenB.value.set(specularColorB)
    u.uSheen.value = Math.max(specularStrength, 0)
    u.uSheenTight.value = Math.max(specularSharpness, 1)
    u.uHaze.value = Math.max(glowStrength, 0)
    u.uHazeTight.value = Math.max(glowFalloff, 1)
    u.uGamma.value = clamp(gamma, 0.2, 4.0)
    u.uGain.value = Math.max(brightness, 0)
    u.uOpacity.value = clamp(opacity, 0, 1)

    if (isTransparent(backgroundColor)) {
      u.uBackdropAlpha.value = 0
    } else {
      u.uBackdropAlpha.value = 1
      u.uBackdrop.value.set(backgroundColor)
    }

    const swing = readSwing()
    swing.x += (swing.toX - swing.x) * Math.min(4 * dt, 1)
    swing.y += (swing.toY - swing.y) * Math.min(4 * dt, 1)

    if (cursorInteraction) {
      u.uSwing.value.set(swing.x * cursorLight, swing.y * cursorLight)
    } else {
      u.uSwing.value.set(0, 0)
    }

    // Adaptive DPR management
    const q = qualityRef.current
    q.frames += 1
    q.span += delta
    if (q.span >= 0.75) {
      const fps = q.frames / q.span
      q.frames = 0
      q.span = 0
      if (adaptiveQuality && clockRef.current > 0.5) {
        if (fps < 0.85 * targetFps && q.scale > 0.5) {
          q.roof = q.scale
          q.scale = Math.max(0.5, 0.75 * q.scale)
          q.wins = 0
          setDpr(q.scale)
        } else if (fps >= 0.95 * targetFps && q.scale < ceiling) {
          q.wins += 1
          const next = Math.min(ceiling, 1.25 * q.scale)
          if (q.wins >= 3 && next < 0.98 * q.roof) {
            q.scale = next
            q.wins = 0
            setDpr(next)
          }
        } else {
          q.wins = 0
        }
      }
    }

    invalidate()
  })

  return (
    <mesh frustumCulled={false}>
      <planeGeometry args={[2, 2]} />
      <shaderMaterial
        ref={materialRef}
        uniforms={uniforms}
        vertexShader={vertexShader}
        fragmentShader={fragmentShader}
        transparent={true}
        premultipliedAlpha={true}
        depthTest={false}
        depthWrite={false}
      />
    </mesh>
  )
}

const emptySubscribe = () => () => {}
const getSystemDpr = () => (typeof window !== 'undefined' ? window.devicePixelRatio || 1 : 1)

export const SpecterOrb: React.FC<SpecterOrbProps> = ({
  width = '100%',
  height = '100%',
  className,
  children,
  radius = 0.35,
  turbulence = 0.22,
  noiseScale = 0.85,
  flowSpeed = 0.1,
  octaves = 3,
  roughness = 0.5,
  lacunarity = 2,
  steps = 32,
  stride = 1,
  zoom = 0.88,
  maskRadius = 0,
  maskFeather = 0.3,
  colorA = '#4da6ff',
  colorB = '#9959ff',
  colorC = '#6680ff',
  rimStrength = 0.75,
  rimPower = 3,
  specularColorA = '#669fff',
  specularColorB = '#998fff',
  specularStrength = 1,
  specularSharpness = 12,
  glowStrength = 1,
  glowFalloff = 28,
  gamma = 1.25,
  brightness = 1,
  opacity = 1,
  backgroundColor = 'transparent',
  cursorInteraction = true,
  cursorLight = 0.2,
  adaptiveQuality = true,
  targetFps = 60,
  dpr = 2,
  paused = false,
}) => {
  const containerRef = useRef<HTMLDivElement | null>(null)
  const swingRef = useRef<SwingState>({ x: 0, y: 0, toX: 0, toY: 0 })
  const [isIntersecting, setIsIntersecting] = useState(false)
  const systemDpr = useSyncExternalStore(emptySubscribe, getSystemDpr, () => 1)

  useEffect(() => {
    const el = containerRef.current
    if (!el || typeof IntersectionObserver === 'undefined') {
      setIsIntersecting(true)
      return
    }
    const obs = new IntersectionObserver(
      ([entry]) => {
        setIsIntersecting(entry.isIntersecting)
      },
      { rootMargin: '120px' }
    )
    obs.observe(el)
    return () => obs.disconnect()
  }, [])

  const readSwing = useCallback(() => swingRef.current, [])

  const handlePointerMove = useCallback((e: React.PointerEvent<HTMLDivElement>) => {
    const el = containerRef.current
    if (!el) return
    const rect = el.getBoundingClientRect()
    if (rect.width && rect.height) {
      swingRef.current.toX = (e.clientX - rect.left) / rect.width - 0.5
      swingRef.current.toY = 0.5 - (e.clientY - rect.top) / rect.height
    }
  }, [])

  const handlePointerLeave = useCallback(() => {
    swingRef.current.toX = 0
    swingRef.current.toY = 0
  }, [])

  const effectiveDpr = useMemo(
    () => clamp(Math.min(systemDpr, dpr), 0.5, 2),
    [systemDpr, dpr]
  )

  const isBgTransparent = isTransparent(backgroundColor)

  return (
    <div
      ref={containerRef}
      className={cn('specter-orb-container relative overflow-visible', className)}
      style={{
        width,
        height,
        backgroundColor: isBgTransparent ? 'transparent' : backgroundColor,
      }}
      onPointerMove={cursorInteraction ? handlePointerMove : undefined}
      onPointerLeave={cursorInteraction ? handlePointerLeave : undefined}
      data-testid="specter-orb"
    >
      <Canvas
        className="absolute inset-0 specter-orb-canvas"
        dpr={effectiveDpr}
        frameloop={isIntersecting && !paused ? 'always' : 'demand'}
        gl={{ antialias: false, alpha: true, powerPreference: 'high-performance' }}
        orthographic={true}
      >
        <SpecterOrbMesh
          awake={isIntersecting}
          ceiling={effectiveDpr}
          readSwing={readSwing}
          radius={radius}
          turbulence={turbulence}
          noiseScale={noiseScale}
          flowSpeed={flowSpeed}
          octaves={octaves}
          roughness={roughness}
          lacunarity={lacunarity}
          steps={steps}
          stride={stride}
          zoom={zoom}
          maskRadius={maskRadius}
          maskFeather={maskFeather}
          colorA={colorA}
          colorB={colorB}
          colorC={colorC}
          rimStrength={rimStrength}
          rimPower={rimPower}
          specularColorA={specularColorA}
          specularColorB={specularColorB}
          specularStrength={specularStrength}
          specularSharpness={specularSharpness}
          glowStrength={glowStrength}
          glowFalloff={glowFalloff}
          gamma={gamma}
          brightness={brightness}
          opacity={opacity}
          backgroundColor={backgroundColor}
          cursorInteraction={cursorInteraction}
          cursorLight={cursorLight}
          adaptiveQuality={adaptiveQuality}
          targetFps={targetFps}
          paused={paused}
        />
      </Canvas>
      {children ? (
        <div className="relative z-10 h-full w-full pointer-events-none specter-orb-content">
          {children}
        </div>
      ) : null}
    </div>
  )
}

export default SpecterOrb
