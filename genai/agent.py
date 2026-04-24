"""
Smart-Boutique/genai/agent.py
-------------------------------
LangChain Chains + Agent — from your notes Sections 2-3
Covers: ChatPromptTemplate, RetrievalQA, Tool-Calling Agent, LangSmith.
Every import uses try/except for version compatibility.
"""

import os
import sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

# ── LangSmith (Section 1.3) — set BEFORE importing langchain ─────────────────
os.environ["LANGCHAIN_TRACING_V2"] = os.getenv("LANGCHAIN_TRACING_V2", "false")
os.environ["LANGCHAIN_API_KEY"]    = os.getenv("LANGCHAIN_API_KEY", "")
os.environ["LANGCHAIN_PROJECT"]    = os.getenv("LANGCHAIN_PROJECT", "smart-boutique")

from langchain_anthropic import ChatAnthropic

# ── PROMPTS (Section 2.2) ─────────────────────────────────────────────────────
try:
    from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
except ImportError:
    from langchain.prompts import ChatPromptTemplate, MessagesPlaceholder

# ── CHAINS (Section 2.3) ──────────────────────────────────────────────────────
try:
    from langchain.chains import ConversationalRetrievalChain
except ImportError:
    ConversationalRetrievalChain = None

# ── AGENTS (Section 2.6) ──────────────────────────────────────────────────────
try:
    from langchain.agents import AgentExecutor, create_tool_calling_agent
except ImportError:
    try:
        from langchain_community.agents import AgentExecutor, create_tool_calling_agent
    except ImportError:
        AgentExecutor            = None
        create_tool_calling_agent = None

from genai.rag_pipeline import get_retriever
from genai.memory import get_production_memory, get_memory_by_name
from genai.tools import ALL_TOOLS

# ── Claude LLM ────────────────────────────────────────────────────────────────
def get_claude_llm(model: str = "claude-haiku-4-5-20251001", temperature: float = 0.3):
    """
    Section 2.1 — Models:
    LangChain wraps all providers with one unified interface.
    Changing model = change one line. Everything else stays the same.
    """
    return ChatAnthropic(
        model=model,
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
        max_tokens=1024,
        temperature=temperature
    )


BOUTIQUE_SYSTEM_PROMPT = """You are the AI Fashion Assistant for Anjali Ladies Boutique,
located in Muggam, Kerala, India. The boutique specialises in embroidery,
customization, kurtas, sarees, sets, and ethnic wear.

Guidelines:
- Answer using the provided context and tools
- Always recommend specific products with prices and sizes
- Use Rs for prices. Be warm and knowledgeable about Indian fashion
- For size questions, give measurements in inches
- For occasion questions, suggest specific categories and colors"""


def build_rag_chain(retriever_type: str = "hybrid",
                    memory_type: str = "Summary Buffer Memory ⭐"):
    """
    Section 2.3 — RetrievalQA Chain:
    Retriever → Prompt → LLM — the core RAG chain.
    Includes ConversationSummaryBufferMemory for chat history.
    """
    if ConversationalRetrievalChain is None:
        raise ImportError("ConversationalRetrievalChain not available. "
                         "Run: pip install langchain --upgrade")

    llm       = get_claude_llm()
    retriever = get_retriever(search_type=retriever_type, k=4)
    memory    = get_memory_by_name(memory_type)

    # Section 2.2 — ChatPromptTemplate
    # System + History (MessagesPlaceholder) + Context + Question
    prompt = ChatPromptTemplate.from_messages([
        ("system", BOUTIQUE_SYSTEM_PROMPT + """

Use the following retrieved context to answer.
If context doesn't have the answer, use general Indian fashion knowledge.

Context:
{context}"""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{question}"),
    ])

    chain = ConversationalRetrievalChain.from_llm(
        llm=llm,
        retriever=retriever,
        memory=memory,
        combine_docs_chain_kwargs={"prompt": prompt},
        return_source_documents=True,
        verbose=False
    )
    return chain


def build_tool_agent():
    """
    Section 2.6 — Tool-Calling Agent:
    Agent decides which tools to call. Uses ReAct loop:
    Think → Act (call tool) → Observe result → Think → Answer
    """
    if create_tool_calling_agent is None or AgentExecutor is None:
        raise ImportError("Agent components not available. "
                         "Run: pip install langchain --upgrade")

    llm = get_claude_llm(temperature=0)

    agent_prompt = ChatPromptTemplate.from_messages([
        ("system", BOUTIQUE_SYSTEM_PROMPT + """

You have boutique database tools. Use them when the user asks about
sales data, customers, suppliers, or seasonal demand."""),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_tool_calling_agent(
        llm=llm,
        tools=ALL_TOOLS,
        prompt=agent_prompt
    )

    return AgentExecutor(
        agent=agent,
        tools=ALL_TOOLS,
        verbose=True,
        max_iterations=5,
        handle_parsing_errors=True,
        return_intermediate_steps=True
    )


def get_answer(question: str, chain=None, agent=None,
               chat_history: list = None, mode: str = "rag") -> dict:
    """Routes question to RAG chain or Tool agent."""
    if chat_history is None:
        chat_history = []

    result = {"answer": "", "sources": [], "tools_used": [], "mode_used": mode}

    try:
        if mode in ("rag", "hybrid") and chain:
            response        = chain({"question": question})
            result["answer"] = response.get("answer", "")
            source_docs     = response.get("source_documents", [])
            result["sources"] = list(set([
                doc.metadata.get("source_file", "knowledge base")
                for doc in source_docs
            ]))

        elif mode == "agent" and agent:
            response        = agent.invoke({
                "input": question,
                "chat_history": chat_history
            })
            result["answer"] = response.get("output", "")
            steps = response.get("intermediate_steps", [])
            result["tools_used"] = [
                step[0].tool for step in steps if hasattr(step[0], "tool")
            ]

    except Exception as e:
        result["answer"] = f"I encountered an error: {str(e)}. Please try again."

    return result


def detect_question_type(question: str) -> str:
    """
    Simple RouterChain pattern — routes to RAG or Agent.
    Data questions → Agent | Knowledge questions → RAG
    """
    q = question.lower()
    data_kw = ["how many","total","revenue","sales","orders","customer",
               "supplier","return rate","best selling","top","performance",
               "statistics","number","database"]
    know_kw = ["wear","recommend","fabric","size","festival","occasion",
               "color","style","how to","what is","explain","guide",
               "tips","care","wash","tailor","design"]

    if sum(1 for kw in data_kw if kw in q) > sum(1 for kw in know_kw if kw in q):
        return "agent"
    return "rag"
