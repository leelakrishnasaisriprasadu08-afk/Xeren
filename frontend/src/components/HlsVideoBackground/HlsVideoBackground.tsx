import React, { useEffect, useRef, useState, useCallback } from 'react'
import Hls from 'hls.js'
import './HlsVideoBackground.css'

export interface HlsVideoBackgroundProps {
  /** HLS stream URL (.m3u8) */
  src?: string
  /** Fallback MP4 video URL if HLS is unsupported or fails */
  fallbackSrc?: string
  /** Poster image before video starts */
  poster?: string
  /** Initial muted state (default true for autoplay compatibility) */
  isMuted?: boolean
  /** Controlled play/pause state */
  isPlaying?: boolean
  /** Callback when audio state changes */
  onToggleMute?: (muted: boolean) => void
  /** Callback when playback state changes */
  onTogglePlay?: (playing: boolean) => void
  /** Callback when video loading state updates */
  onReady?: () => void
  /** Show on-screen quick playback pill */
  showPlaybackBadge?: boolean
  /** Dark overlay gradient density */
  overlayIntensity?: 'subtle' | 'balanced' | 'deep'
}

const safePlay = (el: HTMLVideoElement | null) => {
  if (!el) return
  try {
    const res = el.play()
    if (res && typeof res.catch === 'function') {
      res.catch(() => {})
    }
  } catch {
    // Autoplay or media playback blocked
  }
}

const safePause = (el: HTMLVideoElement | null) => {
  if (!el) return
  try {
    el.pause()
  } catch {
    // Pause error ignored
  }
}

export const HlsVideoBackground: React.FC<HlsVideoBackgroundProps> = ({
  src = 'https://test-streams.mux.dev/x36xhzz/x36xhzz.m3u8',
  fallbackSrc = 'https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4',
  poster,
  isMuted = true,
  isPlaying = true,
  onToggleMute,
  onTogglePlay,
  onReady,
  showPlaybackBadge = true,
  overlayIntensity = 'balanced',
}) => {
  const videoRef = useRef<HTMLVideoElement | null>(null)
  const hlsRef = useRef<Hls | null>(null)

  const [localMuted, setLocalMuted] = useState<boolean | null>(null)
  const [localPlaying, setLocalPlaying] = useState<boolean | null>(null)
  const muted = localMuted ?? isMuted
  const playing = localPlaying ?? isPlaying

  const [hasLoaded, setHasLoaded] = useState(false)
  const [streamQuality, setStreamQuality] = useState<string>('Auto HD')
  const [streamType, setStreamType] = useState<'hls' | 'native' | 'mp4'>('hls')
  const [playbackError, setPlaybackError] = useState<string | null>(null)

  const onReadyRef = useRef(onReady)
  const playingRef = useRef(playing)

  useEffect(() => {
    onReadyRef.current = onReady
  }, [onReady])

  useEffect(() => {
    playingRef.current = playing
  }, [playing])

  // Sync external muted prop
  useEffect(() => {
    if (videoRef.current) {
      videoRef.current.muted = muted
    }
  }, [muted])

  // Sync external isPlaying prop
  useEffect(() => {
    if (videoRef.current) {
      if (playing) {
        safePlay(videoRef.current)
      } else {
        safePause(videoRef.current)
      }
    }
  }, [playing])

  // Toggle Mute
  const handleToggleMute = useCallback(() => {
    const next = !muted
    setLocalMuted(next)
    if (videoRef.current) {
      videoRef.current.muted = next
    }
    onToggleMute?.(next)
  }, [muted, onToggleMute])

  // Toggle Play/Pause
  const handleTogglePlay = useCallback(() => {
    const next = !playing
    setLocalPlaying(next)
    if (videoRef.current) {
      if (next) {
        safePlay(videoRef.current)
      } else {
        safePause(videoRef.current)
      }
    }
    onTogglePlay?.(next)
  }, [playing, onTogglePlay])

  // Initialize HLS / Video
  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    let hlsInstance: Hls | null = null

    const handleLoadedMetadata = () => {
      setHasLoaded(true)
      onReadyRef.current?.()
    }

    video.addEventListener('loadedmetadata', handleLoadedMetadata)

    // 1. Check if Hls.js is supported
    if (Hls.isSupported()) {
      hlsInstance = new Hls({
        enableWorker: true,
        lowLatencyMode: true,
        backBufferLength: 60,
      })
      hlsRef.current = hlsInstance

      hlsInstance.loadSource(src)
      hlsInstance.attachMedia(video)

      hlsInstance.on(Hls.Events.MANIFEST_PARSED, (_event, data) => {
        setStreamType('hls')
        const highestLevel = data.levels?.[data.firstLevel]
        if (highestLevel?.height) {
          setStreamQuality(`${highestLevel.height}p`)
        } else {
          setStreamQuality('1080p 60fps')
        }

        if (playingRef.current) {
          safePlay(video)
        }
      })

      hlsInstance.on(Hls.Events.ERROR, (_event, data) => {
        if (data.fatal) {
          switch (data.type) {
            case Hls.ErrorTypes.NETWORK_ERROR:
              hlsInstance?.startLoad()
              break
            case Hls.ErrorTypes.MEDIA_ERROR:
              hlsInstance?.recoverMediaError()
              break
            default:
              // Fall back to direct video element
              hlsInstance?.destroy()
              hlsRef.current = null
              setStreamType('mp4')
              video.src = fallbackSrc
              safePlay(video)
              break
          }
        }
      })
    } else if (video.canPlayType('application/vnd.apple.mpegurl')) {
      // 2. Native HLS support (Apple Safari / iOS)
      setStreamType('native')
      setStreamQuality('Apple HLS')
      video.src = src
      safePlay(video)
    } else {
      // 3. Progressive MP4 fallback
      setStreamType('mp4')
      setStreamQuality('Direct MP4')
      video.src = fallbackSrc
      safePlay(video)
    }

    return () => {
      video.removeEventListener('loadedmetadata', handleLoadedMetadata)
      if (hlsInstance) {
        hlsInstance.destroy()
        hlsRef.current = null
      }
    }
  }, [src, fallbackSrc])

  return (
    <div
      className={`hls-video-background-wrapper intensity-${overlayIntensity}`}
      data-testid="hls-video-background"
      aria-hidden="true"
    >
      {/* 1. Full-screen Video Element */}
      <video
        ref={videoRef}
        className={`hls-fullscreen-video ${hasLoaded ? 'loaded' : ''}`}
        playsInline
        autoPlay
        loop
        muted={muted}
        poster={poster}
        onError={() => setPlaybackError('Stream fallback active')}
        data-testid="hls-video-element"
      />

      {/* 2. Film Grain & Holographic Lattice Overlay */}
      <div className="hls-texture-grid" />

      {/* 3. Deep Bottom-Left Radial & Linear Gradient for Hero Readability */}
      <div className="hls-gradient-hero-mask" />

      {/* 4. Top Glass Navigation Shadow Mask */}
      <div className="hls-gradient-header-mask" />

      {/* 5. Cinematic Peripheral Vignette */}
      <div className="hls-vignette" />

      {/* 6. Live HLS Status & Micro Playback Badge */}
      {showPlaybackBadge && (
        <aside
          className="hls-telemetry-badge"
          aria-label="Video stream status and controls"
          title={playbackError || undefined}
          data-testid="hls-stream-badge"
        >
          <div className="telemetry-live-dot" title="Live Video Stream" />
          <span className="telemetry-stream-type">{playbackError ? 'BACKUP' : `${streamType.toUpperCase()} LIVE`}</span>
          <span className="telemetry-separator">/</span>
          <span className="telemetry-quality">{streamQuality}</span>

          <div className="telemetry-controls">
            {/* Audio Toggle */}
            <button
              type="button"
              className={`telemetry-btn ${!muted ? 'active' : ''}`}
              onClick={handleToggleMute}
              title={muted ? 'Unmute video audio' : 'Mute video audio'}
              aria-label={muted ? 'Unmute video audio' : 'Mute video audio'}
              data-testid="hls-mute-toggle"
            >
              {muted ? (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M11 5L6 9H2v6h4l5 4V5z" />
                  <line x1="23" y1="9" x2="17" y2="15" />
                  <line x1="17" y1="9" x2="23" y2="15" />
                </svg>
              ) : (
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M11 5L6 9H2v6h4l5 4V5z" />
                  <path d="M19.07 4.93a10 10 0 0 1 0 14.14M15.54 8.46a5 5 0 0 1 0 7.07" />
                </svg>
              )}
            </button>

            {/* Play/Pause Toggle */}
            <button
              type="button"
              className="telemetry-btn"
              onClick={handleTogglePlay}
              title={playing ? 'Pause video background' : 'Play video background'}
              aria-label={playing ? 'Pause video background' : 'Play video background'}
              data-testid="hls-play-toggle"
            >
              {playing ? (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                  <rect x="6" y="4" width="4" height="16" />
                  <rect x="14" y="4" width="4" height="16" />
                </svg>
              ) : (
                <svg width="13" height="13" viewBox="0 0 24 24" fill="currentColor">
                  <polygon points="5 3 19 12 5 21 5 3" />
                </svg>
              )}
            </button>
          </div>
        </aside>
      )}
    </div>
  )
}
export default HlsVideoBackground
