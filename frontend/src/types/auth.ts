export type AuthMethod = 'google' | 'github' | 'facebook' | 'passkey' | 'email_otp' | 'phone_otp'

export interface PasskeyCredential {
  credential_id: string
  device_name: string
  public_key: string
  created_at: string
  last_used_at: string
}

export interface UserProfile {
  user_id: string
  handle: string
  display_name: string
  email: string
  phone_number?: string
  avatar_url?: string
  plan_tier: string
  linked_methods: AuthMethod[]
  passkeys: PasskeyCredential[]
  active_project_id?: string
  created_at: string
  last_login_at: string
}

export interface SocialAuthPayload {
  provider: 'google' | 'github' | 'facebook'
  token_or_code?: string
  email?: string
  name?: string
  avatar_url?: string
}

export interface OTPRequestPayload {
  target: string
  method: 'email' | 'phone'
}

export interface OTPVerifyPayload {
  target: string
  code: string
  method: 'email' | 'phone'
}
