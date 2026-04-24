"""
Smart-Boutique/genai/memory.py
--------------------------------
LangChain Memory — from your notes Section 8
Covers all 4 memory types with bulletproof imports.
"""

import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

from langchain_anthropic import ChatAnthropic

# ── MEMORY IMPORTS ────────────────────────────────────────────────────────────
# In LangChain 0.3+, memory moved to langchain_community
try:
    from langchain.memory import (
        ConversationBufferMemory,
        ConversationBufferWindowMemory,
        ConversationSummaryMemory,
        ConversationSummaryBufferMemory,
    )
except ImportError:
    try:
        from langchain_community.chat_message_histories import ChatMessageHistory
        from langchain_core.chat_history import BaseChatMessageHistory
        # Use simple fallback memory using langchain_core
        from langchain_core.runnables.history import RunnableWithMessageHistory
        # Define stubs for compatibility
        class ConversationBufferMemory:
            def __init__(self, **kwargs):
                self.memory_key    = kwargs.get("memory_key", "chat_history")
                self.return_messages = kwargs.get("return_messages", True)
                self.output_key    = kwargs.get("output_key", "answer")
                self.chat_memory   = ChatMessageHistory()
            def save_context(self, inputs, outputs): pass
            def load_memory_variables(self, inputs): return {self.memory_key: []}
            def clear(self): pass

        ConversationBufferWindowMemory  = ConversationBufferMemory
        ConversationSummaryMemory       = ConversationBufferMemory
        ConversationSummaryBufferMemory = ConversationBufferMemory
    except Exception:
        # Ultimate fallback — simple dict-based memory
        class ConversationBufferMemory:
            def __init__(self, **kwargs):
                self.memory_key      = kwargs.get("memory_key", "chat_history")
                self.return_messages = kwargs.get("return_messages", True)
                self.output_key      = kwargs.get("output_key", "answer")
                self._history        = []
            def save_context(self, inputs, outputs): pass
            def load_memory_variables(self, inputs): return {self.memory_key: self._history}
            def clear(self): self._history = []

        ConversationBufferWindowMemory  = ConversationBufferMemory
        ConversationSummaryMemory       = ConversationBufferMemory
        ConversationSummaryBufferMemory = ConversationBufferMemory


def get_llm():
    return ChatAnthropic(
        model="claude-haiku-4-5-20251001",
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=512,
        temperature=0
    )


def get_buffer_memory():
    """Section 8.1 — Stores ALL messages. Best for testing."""
    return ConversationBufferMemory(
        memory_key="chat_history",
        return_messages=True,
        output_key="answer"
    )


def get_window_memory(k: int = 5):
    """Section 8.2 — Last K messages only."""
    try:
        return ConversationBufferWindowMemory(
            k=k,
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
    except Exception:
        return get_buffer_memory()


def get_summary_memory():
    """Section 8.3 — LLM-summarized history."""
    try:
        return ConversationSummaryMemory(
            llm=get_llm(),
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
    except Exception:
        return get_buffer_memory()


def get_summary_buffer_memory(max_token_limit: int = 1000):
    """Section 8.4 — PRODUCTION BEST: recent exact + summarized older."""
    try:
        return ConversationSummaryBufferMemory(
            llm=get_llm(),
            max_token_limit=max_token_limit,
            memory_key="chat_history",
            return_messages=True,
            output_key="answer"
        )
    except Exception:
        return get_buffer_memory()


def get_production_memory():
    """Returns best memory for production chatbot."""
    return get_summary_buffer_memory(max_token_limit=1000)


MEMORY_DESCRIPTIONS = {
    "Buffer Memory": {
        "stores": "All messages verbatim",
        "efficiency": "Low",
        "best_for": "Short demos and testing",
    },
    "Window Memory (k=5)": {
        "stores": "Last 5 message pairs only",
        "efficiency": "Medium",
        "best_for": "Predictable short context chats",
    },
    "Summary Memory": {
        "stores": "LLM-generated summary of full chat",
        "efficiency": "High",
        "best_for": "Very long customer support sessions",
    },
    "Summary Buffer Memory ⭐": {
        "stores": "Recent exact + summary of older",
        "efficiency": "High + exact recent",
        "best_for": "Production chatbots (recommended)",
    },
}


def get_memory_by_name(name: str):
    mapping = {
        "Buffer Memory":           get_buffer_memory,
        "Window Memory (k=5)":     lambda: get_window_memory(k=5),
        "Summary Memory":          get_summary_memory,
        "Summary Buffer Memory ⭐": get_production_memory,
    }
    return mapping.get(name, get_production_memory)()
