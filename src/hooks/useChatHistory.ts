/**
 * Custom hook for managing chat history and API communication
 * Story 4.1: Chat Interface Component
 */

import { useState, useCallback } from "react";
import { ChatMessage, ChatResponse } from "@/types/chat";

interface UseChatHistoryReturn {
  chatHistory: ChatMessage[];
  isLoading: boolean;
  error: string | null;
  sendMessage: (message: string) => Promise<void>;
  clearHistory: () => void;
}

export const useChatHistory = (sessionId: string): UseChatHistoryReturn => {
  const [chatHistory, setChatHistory] = useState<ChatMessage[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const sendMessage = useCallback(
    async (message: string) => {
      // Validate message
      if (!message.trim()) {
        setError("Message cannot be empty");
        return;
      }

      setIsLoading(true);
      setError(null);

      try {
        const response = await fetch("/api/chat", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            session_id: sessionId,
            message: message.trim(),
          }),
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data: ChatResponse = await response.json();

        if (data.status === "error") {
          setError(data.error?.message || "Failed to send message");
          return;
        }

        if (data.data) {
          // Add message to history
          setChatHistory((prev) => [...prev, data.data!]);
        }
      } catch (err) {
        const errorMessage =
          err instanceof Error ? err.message : "Unknown error occurred";
        setError(errorMessage);
        console.error("Error sending message:", err);
      } finally {
        setIsLoading(false);
      }
    },
    [sessionId]
  );

  const clearHistory = useCallback(() => {
    setChatHistory([]);
    setError(null);
  }, []);

  return {
    chatHistory,
    isLoading,
    error,
    sendMessage,
    clearHistory,
  };
};
