export interface Source {
  title: string;
  url: string;
  video_id: string;
  start_time: number;
  relevance_score: number;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: Source[];
  isStreaming?: boolean;
}

export interface StatusResponse {
  indexed: boolean;
  chunk_count: number;
  video_count: number;
}
