/**
 * Chat Panel Component for Story 4.1: Chat Interface
 *
 * Features:
 * - Scrollable message history with user/bot styling
 * - Text input for submitting messages
 * - Enter key to submit, Shift+Enter for newline
 * - Auto-scroll to bottom on new messages
 * - Session-based message persistence
 */

"use client";

import React, { useEffect, useRef, useState, useContext } from "react";
import { ChatPanelProps, ChatMessage } from "@/types/chat";
import { useChatHistory } from "@/hooks/useChatHistory";
import { SessionContext } from "@/lib/SessionContext";

export const ChatPanel: React.FC<ChatPanelProps> = ({ sessionId }) => {
  const { chatHistory, isLoading, error, sendMessage } =
    useChatHistory(sessionId);
  const [currentMessage, setCurrentMessage] = useState("");
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  // Auto-scroll to bottom when new messages arrive
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [chatHistory]);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!currentMessage.trim()) {
      setLocalError("Message cannot be empty");
      return;
    }

    setLocalError(null);

    // Clear input optimistically
    const messageToSend = currentMessage;
    setCurrentMessage("");

    // Send message
    await sendMessage(messageToSend);
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLTextAreaElement>) => {
    // Enter key submits, Shift+Enter adds newline
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSubmit(e as unknown as React.FormEvent);
    }
  };

  const renderMessage = (message: ChatMessage) => {
    const isUser = message.role === "user";

    return (
      <div
        key={message.id}
        className={`flex ${isUser ? "justify-end" : "justify-start"} mb-4`}
      >
        <div
          className={`max-w-xs px-4 py-2 rounded-lg ${
            isUser
              ? "bg-blue-100 dark:bg-blue-900 text-gray-900 dark:text-gray-100 rounded-br-none"
              : "bg-gray-100 dark:bg-gray-700 text-gray-900 dark:text-gray-100 rounded-bl-none"
          }`}
        >
          <p className="text-sm whitespace-pre-wrap">{message.content}</p>
          <span className="text-xs text-gray-500 dark:text-gray-400 mt-1 block">
            {new Date(message.timestamp).toLocaleTimeString([], {
              hour: "2-digit",
              minute: "2-digit",
            })}
          </span>
        </div>
      </div>
    );
  };

  return (
    <div className="flex flex-col h-full bg-white dark:bg-gray-900 border border-gray-300 dark:border-gray-700 rounded-lg shadow-sm">
      {/* Message History */}
      <div className="flex-1 overflow-y-auto p-4 bg-gray-50 dark:bg-gray-800">
        {chatHistory.length === 0 && !error ? (
          <div className="flex items-center justify-center h-full text-gray-400 dark:text-gray-500">
            <p className="text-center">
              No messages yet. Start typing to begin analysis!
            </p>
          </div>
        ) : (
          <div>
            {chatHistory.map((message) => renderMessage(message))}
            {isLoading && (
              <div className="flex justify-start mb-4">
                <div className="bg-gray-100 dark:bg-gray-700 px-4 py-2 rounded-lg">
                  <div className="flex space-x-2">
                    <div className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"></div>
                    <div
                      className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                      style={{ animationDelay: "0.2s" }}
                    ></div>
                    <div
                      className="w-2 h-2 bg-gray-500 rounded-full animate-bounce"
                      style={{ animationDelay: "0.4s" }}
                    ></div>
                  </div>
                </div>
              </div>
            )}
            <div ref={messagesEndRef} />
          </div>
        )}
      </div>

      {/* Error Display */}
      {(error || localError) && (
        <div className="px-4 py-2 bg-red-50 border-t border-red-200">
          <p className="text-sm text-red-700">{error || localError}</p>
        </div>
      )}

      {/* Input Area */}
      <form onSubmit={handleSubmit} className="border-t border-gray-300 dark:border-gray-700 p-4">
        <div className="flex gap-2">
          <textarea
            value={currentMessage}
            onChange={(e) => setCurrentMessage(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Type your analysis request and press Enter..."
            disabled={isLoading}
            rows={2}
            className="flex-1 p-2 border border-gray-300 dark:border-gray-600 dark:bg-gray-800 dark:text-gray-100 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-blue-500 disabled:bg-gray-100 dark:disabled:bg-gray-700 disabled:cursor-not-allowed"
          />
          <button
            type="submit"
            disabled={isLoading || !currentMessage.trim()}
            className="px-4 py-2 bg-blue-500 text-white rounded-lg hover:bg-blue-600 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
          >
            Send
          </button>
        </div>
        <p className="text-xs text-gray-500 dark:text-gray-400 mt-2">
          Shift+Enter for newline, Enter to send
        </p>
      </form>
    </div>
  );
};

// Wrapper component that provides sessionId from SessionContext
const ChatPanelWithSession: React.FC = () => {
  const session = useContext(SessionContext);

  if (!session) {
    return <div className="p-4 text-red-600">Session not initialized</div>;
  }

  return <ChatPanel sessionId={session.sessionId} />;
};

export default ChatPanelWithSession;
