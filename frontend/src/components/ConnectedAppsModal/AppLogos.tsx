import React from 'react'

interface AppLogoProps {
  appId: string
  size?: number
  className?: string
}

export const AppLogo: React.FC<AppLogoProps> = ({ appId, size = 24, className = '' }) => {
  const s = size

  switch (appId.toLowerCase()) {
    // 1. Google Gemini
    case 'gemini':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-gemini ${className}`}
          aria-label="Google Gemini logo"
        >
          <defs>
            <linearGradient id="gemini-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#1ba0e2" />
              <stop offset="50%" stopColor="#7c3aed" />
              <stop offset="100%" stopColor="#ec4899" />
            </linearGradient>
          </defs>
          <path
            d="M12 0C12 6.627 6.627 12 0 12C6.627 12 12 17.373 12 24C12 17.373 17.373 12 24 12C17.373 12 12 6.627 12 0Z"
            fill="url(#gemini-grad)"
          />
        </svg>
      )

    // 2. Canva
    case 'canva':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-canva ${className}`}
          aria-label="Canva logo"
        >
          <defs>
            <linearGradient id="canva-grad" x1="0%" y1="0%" x2="100%" y2="100%">
              <stop offset="0%" stopColor="#00c4cc" />
              <stop offset="50%" stopColor="#3578e5" />
              <stop offset="100%" stopColor="#7d2ae8" />
            </linearGradient>
          </defs>
          <rect width="24" height="24" rx="6" fill="url(#canva-grad)" />
          <path
            d="M17.2 14.8c-.8 2.3-2.7 3.7-5.1 3.7-3.4 0-5.8-2.6-5.8-6.5 0-4.1 2.6-6.6 6.1-6.6 2.2 0 3.9 1.1 4.7 3l-2.4 1.2c-.4-1.1-1.3-1.7-2.3-1.7-1.8 0-3.1 1.4-3.1 4.1 0 2.6 1.2 4 2.9 4 1.3 0 2.2-.8 2.6-1.8l2.4.6z"
            fill="#ffffff"
          />
        </svg>
      )

    // 3. Hugging Face
    case 'huggingface':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-huggingface ${className}`}
          aria-label="Hugging Face logo"
        >
          <circle cx="12" cy="12" r="11" fill="#FFD21E" />
          {/* Eyes */}
          <ellipse cx="8.5" cy="10" rx="1.5" ry="2" fill="#1F2937" />
          <ellipse cx="15.5" cy="10" rx="1.5" ry="2" fill="#1F2937" />
          {/* Smile */}
          <path
            d="M8 14.5C9.2 16.2 10.5 17 12 17C13.5 17 14.8 16.2 16 14.5"
            stroke="#1F2937"
            strokeWidth="1.6"
            strokeLinecap="round"
          />
          {/* Cheeks */}
          <circle cx="6.5" cy="12.5" r="1.5" fill="#FF7878" opacity="0.8" />
          <circle cx="17.5" cy="12.5" r="1.5" fill="#FF7878" opacity="0.8" />
          {/* Hands */}
          <path
            d="M3.5 16C4.5 14 6 15 5 17C4 18 2.5 17.5 3.5 16Z"
            fill="#FFB800"
          />
          <path
            d="M20.5 16C19.5 14 18 15 19 17C20 18 21.5 17.5 20.5 16Z"
            fill="#FFB800"
          />
        </svg>
      )

    // 4. OpenAI / ChatGPT
    case 'openai':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-openai ${className}`}
          aria-label="OpenAI logo"
        >
          <rect width="24" height="24" rx="6" fill="#10a37f" />
          <path
            d="M18.6 10.4a4.3 4.3 0 0 0-.4-3.4 4.4 4.4 0 0 0-3.7-2.1c-.4 0-.8 0-1.2.2a4.4 4.4 0 0 0-3.3-1.6 4.4 4.4 0 0 0-4.2 3.1 4.4 4.4 0 0 0-2.4 2.1 4.4 4.4 0 0 0-.4 3.7c-.4.5-.6 1.1-.6 1.7a4.4 4.4 0 0 0 2.2 3.8 4.4 4.4 0 0 0 3.3 1.6c.4 0 .8 0 1.2-.2a4.4 4.4 0 0 0 3.3 1.6 4.4 4.4 0 0 0 4.2-3.1 4.4 4.4 0 0 0 2.4-2.1c.5-.8.6-1.8.4-2.7.3-.6.5-1.1.5-1.7a4.4 4.4 0 0 0-.5-1zM13 19.8a3 3 0 0 1-1.9-.7l2.2-1.3a1.4 1.4 0 0 0 .7-1.2v-3.1l1.8 1v2.8a3 3 0 0 1-2.8 2.5zm-5.7-2.3a3 3 0 0 1-.9-2l2.2 1.3a1.4 1.4 0 0 0 1.4 0l2.7-1.6v2.1l-2.5 1.4a3 3 0 0 1-2.9-.8zm-1.8-6.1a3 3 0 0 1 1-1.8v2.6a1.4 1.4 0 0 0 .7 1.2l2.7 1.6-1.8 1-2.4-1.4a3 3 0 0 1-1.2-3.2zm9.3.9l-2.7-1.6 1.8-1 2.4 1.4a3 3 0 0 1 1.2 3.2 3 3 0 0 1-1 1.8v-2.6a1.4 1.4 0 0 0-.7-1.2zm2.1-2.4l-2.2-1.3a1.4 1.4 0 0 0-1.4 0l-2.7 1.6V8.1l2.5-1.4a3 3 0 0 1 3.8 2.8v.1zM11 11.2l1.3-.8 1.3.8v1.6l-1.3.8-1.3-.8v-1.6z"
            fill="#ffffff"
          />
        </svg>
      )

    // 5. Anthropic Claude
    case 'claude':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-claude ${className}`}
          aria-label="Anthropic Claude logo"
        >
          <rect width="24" height="24" rx="6" fill="#D97757" />
          <path
            d="M12 4.5l1.6 5 4.9.4-3.8 3.3 1.2 4.8-4-2.8-4 2.8 1.2-4.8-3.8-3.3 4.9-.4L12 4.5z"
            fill="#FAF0EA"
          />
        </svg>
      )

    // 6. Perplexity AI
    case 'perplexity':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-perplexity ${className}`}
          aria-label="Perplexity AI logo"
        >
          <rect width="24" height="24" rx="6" fill="#13343b" />
          <path
            d="M12 3v18M3 12h18M5.6 5.6l12.8 12.8M18.4 5.6L5.6 18.4"
            stroke="#22b8cf"
            strokeWidth="2.2"
            strokeLinecap="round"
          />
          <circle cx="12" cy="12" r="3" fill="#22b8cf" />
        </svg>
      )

    // 7. Midjourney
    case 'midjourney':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-midjourney ${className}`}
          aria-label="Midjourney logo"
        >
          <rect width="24" height="24" rx="6" fill="#0f172a" />
          {/* Sailboat / yacht silhouette */}
          <path
            d="M12 4v10M12 5l5 7h-5M12 6.5l-4 5.5h4M5 16.5c2 1 5 1 7 0s5-1 7 0c-1 2.5-4 4.5-7 4.5s-6-2-7-4.5z"
            stroke="#38bdf8"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )

    // 8. GitHub
    case 'github':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-github ${className}`}
          aria-label="GitHub logo"
        >
          <rect width="24" height="24" rx="6" fill="#181717" />
          <path
            fillRule="evenodd"
            clipRule="evenodd"
            d="M12 4C7.58 4 4 7.67 4 12.2c0 3.62 2.29 6.69 5.47 7.77.4.08.55-.18.55-.39 0-.2-.01-.86-.01-1.56-2.22.5-2.69-.97-2.69-.97-.36-.95-.89-1.2-.89-1.2-.73-.51.05-.5.05-.5.8.06 1.23.85 1.23.85.71 1.25 1.87.89 2.33.68.07-.53.28-.89.5-1.1-1.78-.21-3.64-.91-3.64-4.05 0-.9.31-1.63.82-2.2-.08-.21-.36-1.04.08-2.17 0 0 .67-.22 2.2.84a7.48 7.48 0 0 1 4 0c1.53-1.06 2.2-.84 2.2-.84.44 1.13.16 1.96.08 2.17.51.57.82 1.3.82 2.2 0 3.15-1.87 3.84-3.65 4.04.29.25.54.74.54 1.49 0 1.08-.01 1.95-.01 2.22 0 .22.15.48.55.4 3.18-1.09 5.46-4.15 5.46-7.78C20 7.67 16.42 4 12 4z"
            fill="#ffffff"
          />
        </svg>
      )

    // 9. Supabase
    case 'supabase':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-supabase ${className}`}
          aria-label="Supabase logo"
        >
          <rect width="24" height="24" rx="6" fill="#1c1c1c" />
          <path
            d="M13.4 3.2c.4-.7 1.4-.4 1.4.4v8.1h5.8c.8 0 1.2 1 .7 1.6L10.6 22.8c-.4.7-1.4.4-1.4-.4v-8.1H3.4c-.8 0-1.2-1-.7-1.6L13.4 3.2z"
            fill="url(#supabase-grad)"
          />
          <defs>
            <linearGradient id="supabase-grad" x1="5" y1="3" x2="19" y2="23">
              <stop stopColor="#24b47e" />
              <stop offset="1" stopColor="#3ecf8e" />
            </linearGradient>
          </defs>
        </svg>
      )

    // 10. Notion
    case 'notion':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-notion ${className}`}
          aria-label="Notion logo"
        >
          <rect width="24" height="24" rx="6" fill="#ffffff" />
          <path
            d="M6 5.5l2.2.3c.4 0 .5.2.6.6l.3 7.8 4.7-8.3c.2-.4.4-.5.8-.5l3.4.2c.5 0 .7.3.7.8v11.6c0 .5-.3.8-.8.8l-2.2-.2c-.4 0-.6-.3-.6-.8l-.3-7.8-4.8 8.3c-.2.4-.4.5-.8.5l-3.3-.2c-.5 0-.7-.3-.7-.8V6.3c0-.5.3-.8.8-.8z"
            fill="#000000"
          />
        </svg>
      )

    // 11. Google Drive / Workspace
    case 'gdrive':
    case 'google_drive':
    case 'workspace':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-gdrive ${className}`}
          aria-label="Google Drive logo"
        >
          <rect width="24" height="24" rx="6" fill="#1e293b" />
          <path d="M8.5 4h7l5 9-3.5 6-8.5-15z" fill="#FFC107" />
          <path d="M3.5 19l3.5-6 13.5 0-3.5 6H3.5z" fill="#2196F3" />
          <path d="M3.5 19L8.5 10 12 16 7 19H3.5z" fill="#4CAF50" />
        </svg>
      )

    // 12. Slack
    case 'slack':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-slack ${className}`}
          aria-label="Slack logo"
        >
          <rect width="24" height="24" rx="6" fill="#3F0E40" />
          {/* 4 classic color drops and bars */}
          <path d="M7 11a1.5 1.5 0 0 1-1.5-1.5v-3a1.5 1.5 0 0 1 3 0v3A1.5 1.5 0 0 1 7 11z" fill="#E01E5A" />
          <path d="M5.5 12.5A1.5 1.5 0 0 1 7 11h3a1.5 1.5 0 0 1 0 3H7a1.5 1.5 0 0 1-1.5-1.5z" fill="#36C5F0" />
          <path d="M17 13a1.5 1.5 0 0 1 1.5 1.5v3a1.5 1.5 0 0 1-3 0v-3A1.5 1.5 0 0 1 17 13z" fill="#2EB67D" />
          <path d="M18.5 11.5A1.5 1.5 0 0 1 17 13h-3a1.5 1.5 0 0 1 0-3h3a1.5 1.5 0 0 1 1.5 1.5z" fill="#ECB22E" />
        </svg>
      )

    // 13. Discord
    case 'discord':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-discord ${className}`}
          aria-label="Discord logo"
        >
          <rect width="24" height="24" rx="6" fill="#5865F2" />
          <path
            d="M17.8 7.5c-1-.5-2.1-.8-3.2-1 0 0-.2.4-.3.7 1.2.3 2.3.8 3.3 1.5-1.6-1.1-3.6-1.7-5.6-1.7s-4 .6-5.6 1.7c1-.7 2.1-1.2 3.3-1.5-.1-.3-.3-.7-.3-.7-1.1.2-2.2.5-3.2 1C4.2 11 3.7 14.5 4 17.8c1.3 1 2.6 1.6 3.9 1.9.3-.4.6-.9.9-1.4-.5-.2-.9-.4-1.3-.7.1-.1.2-.2.3-.3 2.8 1.3 5.8 1.3 8.6 0 .1.1.2.2.3.3-.4.3-.8.5-1.3.7.3.5.6 1 .9 1.4 1.3-.3 2.6-.9 3.9-1.9.3-3.8-.6-7.2-2.4-10.3zM9.5 15c-.8 0-1.5-.7-1.5-1.6s.7-1.6 1.5-1.6 1.5.7 1.5 1.6c0 .9-.7 1.6-1.5 1.6zm5 0c-.8 0-1.5-.7-1.5-1.6s.7-1.6 1.5-1.6 1.5.7 1.5 1.6c0 .9-.7 1.6-1.5 1.6z"
            fill="#ffffff"
          />
        </svg>
      )

    // 14. Spotify
    case 'spotify':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-spotify ${className}`}
          aria-label="Spotify logo"
        >
          <circle cx="12" cy="12" r="11" fill="#1ED760" />
          <path
            d="M16.8 15.6c-.2.3-.6.4-.9.2-2.4-1.5-5.5-1.8-9.1-1-.4.1-.7-.1-.8-.5-.1-.4.1-.7.5-.8 4-.9 7.4-.6 10.1 1.1.3.2.4.6.2 1zm1.2-2.7c-.3.4-.8.5-1.2.3-2.8-1.7-7-2.2-10.3-1.2-.5.1-1-.1-1.1-.6-.1-.5.1-1 .6-1.1 3.8-1.1 8.5-.6 11.7 1.4.4.2.5.8.3 1.2zm.1-2.8c-3.3-2-8.8-2.1-12-.1-.5.2-1.1 0-1.3-.5-.2-.5 0-1.1.5-1.3 3.7-2.3 9.7-2.1 13.5.2.5.3.6.9.3 1.4-.2.5-.8.6-1 .3z"
            fill="#121212"
          />
        </svg>
      )

    // 15. Linear
    case 'linear':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-linear ${className}`}
          aria-label="Linear logo"
        >
          <rect width="24" height="24" rx="6" fill="#5E6AD2" />
          <path
            d="M5 12l7-7 7 7-7 7-7-7z"
            stroke="#ffffff"
            strokeWidth="2"
            strokeLinejoin="round"
          />
          <path
            d="M8.5 12l3.5-3.5 3.5 3.5-3.5 3.5-3.5-3.5z"
            fill="#ffffff"
          />
        </svg>
      )

    // 16. Figma
    case 'figma':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-figma ${className}`}
          aria-label="Figma logo"
        >
          <rect width="24" height="24" rx="6" fill="#1e1e1e" />
          <path d="M12 4.5H9a2.5 2.5 0 0 0 0 5h3v-5z" fill="#F24E1E" />
          <path d="M12 4.5h3a2.5 2.5 0 0 1 0 5h-3v-5z" fill="#FF7262" />
          <path d="M12 9.5H9a2.5 2.5 0 0 0 0 5h3v-5z" fill="#A259FF" />
          <circle cx="14.5" cy="12" r="2.5" fill="#1ABCFE" />
          <path d="M9 14.5a2.5 2.5 0 0 0 0 5 2.5 2.5 0 0 0 2.5-2.5v-2.5H9z" fill="#0ACF83" />
        </svg>
      )

    // 17. Blender 3D (Native Local App)
    case 'blender':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-blender ${className}`}
          aria-label="Blender logo"
        >
          <rect width="24" height="24" rx="6" fill="#1C1E24" />
          {/* Blender arms */}
          <path d="M12 4.5l-1.6 3.5h3.2L12 4.5z" fill="#E87D0D" />
          <path d="M4.5 10.5l3.8 1.2-.8-2.6-3 1.4z" fill="#E87D0D" />
          <path d="M19.5 10.5l-3 1.4-.8 2.6 3.8-4z" fill="#E87D0D" />
          {/* Main orange body loop */}
          <circle cx="12" cy="14" r="5.5" fill="#E87D0D" />
          {/* White inner ring */}
          <circle cx="12" cy="14" r="3.6" fill="#FFFFFF" />
          {/* Blue center eye */}
          <circle cx="12" cy="14" r="2.2" fill="#225B99" />
        </svg>
      )

    // 18. Visual Studio Code (Native Local App)
    case 'vscode':
    case 'vs_code':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-vscode ${className}`}
          aria-label="Visual Studio Code logo"
        >
          <rect width="24" height="24" rx="6" fill="#1E1E1E" />
          <path
            d="M17.5 4.2l-9.2 7 9.2 8.6c.5.4 1.5.2 1.5-.7V4.9c0-.9-1-1.1-1.5-.7z"
            fill="#0065A9"
          />
          <path
            d="M17.5 4.2L8.3 11.2l-3.6-2.8c-.4-.3-1-.2-1.2.3l-.7 1.2c-.2.4-.1.9.2 1.1l3.5 2.8-3.5 2.8c-.3.2-.4.7-.2 1.1l.7 1.2c.2.5.8.6 1.2.3l3.6-2.8 9.2 7V4.2z"
            fill="#007ACC"
          />
          <path
            d="M17.5 4.2v15.6l-5.8-4.5 5.8-11.1z"
            fill="#1F8AD2"
            opacity="0.85"
          />
        </svg>
      )

    // 19. OBS Studio (Native Local App)
    case 'obs':
    case 'obs_studio':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-obs ${className}`}
          aria-label="OBS Studio logo"
        >
          <rect width="24" height="24" rx="6" fill="#18181B" />
          <circle cx="12" cy="12" r="8" fill="#27272A" />
          {/* 3-pinwheel arms */}
          <path
            d="M12 7a5 5 0 0 1 4.5 7.2A3.5 3.5 0 0 0 12 10.5V7z"
            fill="#FFFFFF"
          />
          <path
            d="M8.2 14.5A5 5 0 0 1 12 7v3.5a3.5 3.5 0 0 0-3.8 4z"
            fill="#D4D4D8"
          />
          <path
            d="M15.8 14.5a5 5 0 0 1-7.6 0 3.5 3.5 0 0 0 7.6 0z"
            fill="#A1A1AA"
          />
          <circle cx="12" cy="12.5" r="1.8" fill="#18181B" />
        </svg>
      )

    // 20. VLC Media Player (Native Local App)
    case 'vlc':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-vlc ${className}`}
          aria-label="VLC logo"
        >
          <rect width="24" height="24" rx="6" fill="#1C1917" />
          {/* Traffic cone base */}
          <ellipse cx="12" cy="19.5" rx="7" ry="1.5" fill="#C2410C" />
          {/* Traffic cone body with alternating orange & white stripes */}
          <path d="M11 4.5h2l.7 3.5h-3.4L11 4.5z" fill="#F97316" />
          <path d="M10.3 8h3.4l.8 4h-5l.8-4z" fill="#FFFFFF" />
          <path d="M9.5 12h5l.8 4h-6.6l.8-4z" fill="#F97316" />
          <path d="M8.7 16h6.6l.7 3h-8l.7-3z" fill="#FFFFFF" />
        </svg>
      )

    // 21. GIMP Image Editor (Native Local App)
    case 'gimp':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-gimp ${className}`}
          aria-label="GIMP logo"
        >
          <rect width="24" height="24" rx="6" fill="#292524" />
          {/* Wilber head */}
          <path
            d="M6 14.5c0-4 3-7 7-7s6.5 2.5 6.5 6-3 6.5-6.5 6.5c-2.5 0-4.5-1-5.5-2.5-.5.2-1 .5-1.5.5-1 0-1.5-1-1.5-2 0-.5.5-1.5 1.5-1.5z"
            fill="#78716C"
          />
          {/* Wilber eyes */}
          <ellipse cx="11.5" cy="11.5" rx="1.5" ry="1.8" fill="#FFFFFF" />
          <circle cx="12" cy="11.5" r="0.8" fill="#000000" />
          <ellipse cx="15.5" cy="11.5" rx="1.5" ry="1.8" fill="#FFFFFF" />
          <circle cx="15.5" cy="11.5" r="0.8" fill="#000000" />
          {/* Paintbrush */}
          <path d="M5 18l3-3 1.5 1.5-3 3c-.5.5-1.2.2-1.5 0s-.5-1 0-1.5z" fill="#D97706" />
          <path d="M4.5 18.5c-.5.5-.3 1.2 0 1.5s1 .5 1.5 0l-.8-.8-.7-.7z" fill="#F59E0B" />
        </svg>
      )

    // 22. Local Terminal / PowerShell (Native Local App)
    case 'terminal':
    case 'powershell':
    case 'bash':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-terminal ${className}`}
          aria-label="Terminal logo"
        >
          <rect width="24" height="24" rx="6" fill="#0F172A" stroke="#334155" strokeWidth="1" />
          {/* Prompt >_ */}
          <path d="M6 8l4 4-4 4" stroke="#00f0ff" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
          <path d="M12 16h6" stroke="#00f0ff" strokeWidth="2" strokeLinecap="round" />
        </svg>
      )

    // 23. Custom Local Device Application
    case 'device':
    case 'local_device':
    case 'custom':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-device ${className}`}
          aria-label="Local Device App logo"
        >
          <rect width="24" height="24" rx="6" fill="#111827" stroke="rgba(0, 240, 255, 0.4)" strokeWidth="1" />
          {/* Monitor & Stand */}
          <rect x="5" y="6" width="14" height="9" rx="1.5" fill="#1F2937" stroke="#00f0ff" strokeWidth="1" />
          <circle cx="12" cy="10.5" r="2" fill="#00f0ff" opacity="0.8" />
          <path d="M10 17h4M12 15v2" stroke="#9CA3AF" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      )

    // System Security Vault
    case 'system':
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-system ${className}`}
          aria-label="Xeren Vault logo"
        >
          <rect width="24" height="24" rx="6" fill="rgba(0, 240, 255, 0.15)" stroke="#00f0ff" strokeWidth="1.5" />
          <path
            d="M12 4L6 7v5c0 4.4 2.6 8.5 6 9.8 3.4-1.3 6-5.4 6-9.8V7l-6-3z"
            fill="#00f0ff"
            opacity="0.9"
          />
          <path
            d="M10.5 12l1.5 1.5 3-3"
            stroke="#040812"
            strokeWidth="1.6"
            strokeLinecap="round"
            strokeLinejoin="round"
          />
        </svg>
      )

    // Default Fallback Icon
    default:
      return (
        <svg
          width={s}
          height={s}
          viewBox="0 0 24 24"
          fill="none"
          xmlns="http://www.w3.org/2000/svg"
          className={`app-logo-svg logo-default ${className}`}
          aria-label="Application logo"
        >
          <rect width="24" height="24" rx="6" fill="#111827" stroke="rgba(0, 240, 255, 0.3)" strokeWidth="1" />
          <rect x="5" y="6" width="14" height="9" rx="1.5" fill="#1F2937" stroke="#00f0ff" strokeWidth="1" />
          <path d="M8 10h3M8 12h5" stroke="#00f0ff" strokeWidth="1.2" strokeLinecap="round" />
          <path d="M10 17h4M12 15v2" stroke="#9CA3AF" strokeWidth="1.5" strokeLinecap="round" />
        </svg>
      )
  }
}
