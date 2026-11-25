export type AccountAuthStatus = 'authenticated' | 'pending' | 'expired' | 'disconnected'

export type AccountPlanTier = 'free' | 'pro' | 'enterprise'

export type AppEventType = 'auth' | 'sync' | 'tool_call' | 'error' | 'token_refresh'

export interface UserConnectedAccount {
  app_id: string
  app_name: string
  icon: string
  user_email?: string | null
  user_name?: string | null
  plan_tier: AccountPlanTier
  auth_status: AccountAuthStatus
  masked_token?: string | null
  connected_at?: string | null
  last_sync?: string | null
  category: string
  description: string
  capabilities: string[]
  requires_api_key?: boolean
  connection_type?: 'cloud_api' | 'local_device' | 'custom_url'
  local_path?: string | null
  endpoint_url?: string | null
  is_custom?: boolean
}

export interface AppActivityLog {
  log_id: string
  timestamp: string
  app_id: string
  app_name: string
  user_email: string
  event_type: AppEventType
  message: string
  details?: Record<string, unknown>
}

export interface AccountLoginPayload {
  app_id: string
  user_email: string
  user_name?: string
  token_or_key?: string
  plan_tier: AccountPlanTier
  local_path?: string
  endpoint_url?: string
  connection_type?: 'cloud_api' | 'local_device' | 'custom_url'
}

export interface AddLocalAppPayload {
  app_name: string
  category: string
  local_path?: string
  description?: string
  capabilities?: string[]
  user_name?: string
}

export interface AddCustomAppPayload {
  app_name: string
  category: string
  connection_type: 'cloud_api' | 'custom_url' | 'local_device'
  endpoint_url?: string
  api_key_or_token?: string
  user_email?: string
  user_name?: string
  plan_tier: AccountPlanTier
  local_path?: string
  description?: string
  capabilities?: string[]
}


