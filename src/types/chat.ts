/**
 * Chat interface types for Story 4.1
 * Defines data models for chat messages and component props
 */

export interface ChatMessage {
  id: string;
  role: "user" | "bot";
  content: string;
  timestamp: string;
  status?: "sending" | "sent" | "error";
}

export interface ChatPanelProps {
  sessionId: string;
}

export interface ChatRequest {
  session_id: string;
  message: string;
}

export interface ChatResponse {
  status: "success" | "error";
  data?: ChatMessage;
  error?: {
    message: string;
    code: string;
  };
}
