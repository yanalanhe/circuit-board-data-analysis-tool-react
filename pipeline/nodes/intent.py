# pipeline/nodes/intent.py
"""Intent classification node for the new pipeline.

Classifies user queries into report, qa, or chat intents.
Generates direct responses for qa and chat intents.

NOTE: Never import streamlit in this file.
"""
from pipeline.state import PipelineState
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage

_INTENT_SYSTEM_PROMPT = """You are an intent classifier for a data analysis tool.
Classify the user's message into exactly one of these three categories:
- "report": The user wants to create a chart, visualization, analysis report, or any
  computation/aggregation of data (e.g., "create a chart of X vs Y", "analyze column X",
  "calculate correlation", "show trends in")
- "qa": The user wants a direct factual answer about the data without a full report
  (e.g., "what is the max value?", "how many rows?", "what is the average of column B?")
- "chat": General conversation, capability questions, or greetings
  (e.g., "hello", "what can you do?", "thank you")

Respond with ONLY one word: report, qa, or chat. No explanation, no punctuation."""

_QA_RESPONSE_SYSTEM_PROMPT = """You are a data analyst assistant. Answer the user's question about their data concisely and accurately.

Available data context:
{csv_metadata}

Provide a direct, factual answer based on the available data. Keep your response under 200 tokens."""

_CHAT_RESPONSE_SYSTEM_PROMPT = """You are a helpful data analysis assistant. Respond briefly and naturally to the user's message.
Be friendly and conversational. Mention what you can help with if appropriate."""


def _generate_qa_response(state: PipelineState, llm: ChatOpenAI) -> str:
    """Generate a direct answer for Q&A intent queries."""
    try:
        csv_metadata = state.get("csv_metadata", "No data available yet")
        prompt = _QA_RESPONSE_SYSTEM_PROMPT.format(csv_metadata=csv_metadata)

        messages = [
            SystemMessage(content=prompt),
            HumanMessage(content=state["user_query"]),
        ]
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception:
        return "I encountered an error while analyzing the data. Please try again."


def _generate_chat_response(state: PipelineState, llm: ChatOpenAI) -> str:
    """Generate a conversational response for chat intent queries."""
    try:
        messages = [
            SystemMessage(content=_CHAT_RESPONSE_SYSTEM_PROMPT),
            HumanMessage(content=state["user_query"]),
        ]
        response = llm.invoke(messages)
        return response.content.strip()
    except Exception:
        return "I'm here to help! Feel free to ask me anything about your data analysis."


def classify_intent(state: PipelineState) -> dict:
    """Classify user intent as 'report', 'qa', or 'chat'.

    For 'qa' and 'chat' intents, also generates a direct response.
    For 'report' intent, response is left empty (plan generation follows).

    Returns only the changed keys per LangGraph convention.
    Defaults to 'chat' on any LLM error.
    """
    try:
        llm = ChatOpenAI(model="gpt-4o", temperature=0)

        # Classify intent
        messages = [
            SystemMessage(content=_INTENT_SYSTEM_PROMPT),
            HumanMessage(content=state["user_query"]),
        ]
        response = llm.invoke(messages)
        raw = response.content.strip().lower()

        if raw in ("report", "qa", "chat"):
            intent = raw
        elif "report" in raw:
            intent = "report"
        elif "qa" in raw or "q&a" in raw:
            intent = "qa"
        else:
            intent = "chat"

        # Generate response for qa/chat, leave empty for report
        response_text = ""
        if intent == "qa":
            response_text = _generate_qa_response(state, llm)
        elif intent == "chat":
            response_text = _generate_chat_response(state, llm)

        return {
            "intent": intent,
            "response": response_text,
        }
    except Exception as e:
        from utils.error_translation import translate_error
        error_msg = translate_error(e)
        return {
            "intent": "chat",  # safe fallback — pipeline continues
            "response": "I'm having trouble processing your request. Please try again.",
            "error_messages": list(state.get("error_messages", [])) + [error_msg],
        }
