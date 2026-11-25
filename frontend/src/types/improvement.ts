/**
 * Types for LLM Self-Improvement Engine, Pattern Recognition, and Adaptive Prompt Evolution.
 */

export type ObservationSource = 
  | 'user_query'
  | 'user_task'
  | 'web_search'
  | 'bot_model_output'
  | 'verification_result';

export interface UserQueryPattern {
  pattern_id: string;
  category: 'architecture' | 'coding_style' | 'verification' | 'research' | 'tool_preference' | string;
  intent_cluster: string;
  sample_queries: string[];
  frequency_count: number;
  confidence: number;
  first_observed: string;
  last_observed: string;
  distilled_preference: string;
  recommended_adaptation: string;
  is_active: boolean;
}

export interface SearchModelInsight {
  insight_id: string;
  topic: string;
  consensus_facts: string[];
  recurring_domains: string[];
  failure_traps_identified: string[];
  bot_models_evaluated: string[];
  consensus_agreement_pct: number;
  discovered_at: string;
}

export interface AdaptiveSystemDirective {
  directive_id: string;
  title: string;
  category: 'code_generation' | 'query_routing' | 'search_synthesis' | 'error_mitigation' | string;
  directive_prompt: string;
  source_patterns: string[];
  effectiveness_score: number;
  is_active: boolean;
  evolution_cycle: number;
  created_at: string;
  updated_at: string;
}

export interface SelfImprovementReport {
  adaptive_score: number;
  total_observations_recorded: number;
  patterns_count: number;
  insights_count: number;
  active_directives_count: number;
  evolution_cycles_completed: number;
  recent_improvements: string[];
  timestamp: string;
}

export interface ImprovementHubState {
  report: SelfImprovementReport | null;
  patterns: UserQueryPattern[];
  insights: SearchModelInsight[];
  directives: AdaptiveSystemDirective[];
  isLoading: boolean;
  isAnalyzing: boolean;
  error: string | null;
}
