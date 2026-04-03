export interface Topic {
  title: string;
  summary: string;
  timestamp?: string | null;
}

export interface Decision {
  decision: string;
  owner: string;
  condition?: string | null;
}

export interface Action {
  task: string;
  owner: string;
  deadline?: string | null;
  priority: 'high' | 'medium' | 'low';
  ambiguous?: boolean;
}

export interface StructuredMOM {
  mom_id: string;
  participants: string[];
  topics: Topic[];
  decisions: Decision[];
  actions: Action[];
  original_language: string;
  file_url?: string | null;
  format_id?: string;
  format_name?: string;
  trace?: Array<{
    agent: string;
    status: string;
    reasoning: string;
    execution_ms: number;
    timestamp: number;
  }>;
  sections?: Record<string, any>;
  template_structure?: {
    sections: Array<{
      id: string;
      label: string;
      fields?: Array<{
        id: string;
        label: string;
        type: string;
      }>;
    }>;
  };
}

export interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  type?: 'text' | 'mom';
  mom?: StructuredMOM;
  file_url?: string;
  timestamp: string;
}

export interface Session {
  session_id: string;
  label: string;
  created_at: string;
}
