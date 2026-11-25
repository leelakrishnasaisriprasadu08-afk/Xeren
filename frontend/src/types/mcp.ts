export type MCPTransportType = 'stdio' | 'sse' | 'http'

export interface MCPTool {
  name: string
  description: string
  server_id: string
  parameters?: Record<string, unknown>
  category?: string
}

export interface MCPResource {
  uri: string
  name: string
  mime_type?: string
  description?: string
  server_id: string
}

export interface MCPServer {
  id: string
  name: string
  description: string
  transport: MCPTransportType
  command?: string
  args: string[]
  env?: Record<string, string>
  url?: string
  enabled: boolean
  status: 'connected' | 'connecting' | 'offline' | 'error'
  icon?: string
  category: 'filesystem' | 'developer' | 'database' | 'web' | 'productivity' | 'custom'
  tools: MCPTool[]
  resources?: MCPResource[]
}

export interface MCPPreset extends MCPServer {
  installed?: boolean
}

export interface CrossAppPipelineStep {
  step_id: string
  server_id: string
  tool_name: string
  arguments: Record<string, unknown>
  description: string
  pass_output_to_next?: boolean
}

export interface CrossAppPipeline {
  pipeline_id: string
  name: string
  description: string
  steps: CrossAppPipelineStep[]
}

export interface PipelineExecutionResult {
  pipeline_id: string
  success: boolean
  step_results: Array<{
    step_id: string
    server_id: string
    tool_name: string
    description: string
    success: boolean
    latency_ms: number
    output: unknown
  }>
  final_output?: unknown
  execution_time_ms: number
  error?: string
}
