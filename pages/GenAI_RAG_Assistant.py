"""
Smart-Boutique/pages/GenAI_RAG_Assistant.py
Anjali Ladies Boutique — Unified AI Fashion Assistant
"""

import os
import sys
import shutil

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import streamlit as st
from database.db import init_db

st.set_page_config(
    page_title="Anjali AI · Smart Boutique",
    page_icon="✨",
    layout="wide"
)

from utils.secrets import load_api_keys
load_api_keys()

init_db()
from utils.auth import require_auth
role, cust_id = require_auth()   # both admin and customer

GOLD = "#c9a96e"
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@400;700&family=DM+Sans:wght@300;400;500&display=swap');
html, body, [class*="css"] { font-family: 'DM Sans', sans-serif; }
h1,h2,h3 { font-family: 'Playfair Display', serif !important; }
section[data-testid="stSidebar"] {
    background: linear-gradient(160deg, #1a0a2e 0%, #16213e 60%, #0f3460 100%);
}
section[data-testid="stSidebar"] * { color: #f5e6d3 !important; }
[data-testid="metric-container"] {
    background: linear-gradient(135deg, #1a0a2e22, #0f346022);
    border: 1px solid #c9a96e44; border-radius: 12px; padding: 1rem;
}
.stButton > button {
    background: linear-gradient(135deg, #c9a96e, #e8c99a);
    color: #1a0a2e; font-weight: 600; border: none; border-radius: 8px;
}
.source-badge {
    background: #c9a96e22; border: 1px solid #c9a96e55;
    border-radius: 20px; padding: 2px 10px;
    font-size: 0.8rem; color: #c9a96e;
    display: inline-block; margin: 2px;
}
.tool-badge {
    background: #2ecc7122; border: 1px solid #2ecc7155;
    border-radius: 20px; padding: 2px 10px;
    font-size: 0.8rem; color: #2ecc71;
    display: inline-block; margin: 2px;
}
</style>
""", unsafe_allow_html=True)

init_db()

# ── Header ────────────────────────────────────────────────────────────────────
st.markdown(f"<h1 style='color:{GOLD}'>✨ Anjali AI — Your Boutique Brain</h1>",
            unsafe_allow_html=True)
st.markdown("*From Muggam to your fingertips — fashion wisdom, business insight, "
            "and style expertise. All in one conversation.*")
st.divider()

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown(f"<h3 style='color:{GOLD};'>✨ Anjali AI Settings</h3>",
                unsafe_allow_html=True)

    retriever_type = st.selectbox(
        "🔍 Search Mode",
        ["hybrid", "mmr", "similarity"],
        help="hybrid=BM25+Vector | mmr=Diverse | similarity=Basic"
    )
    retriever_labels = {
        "hybrid":     "Hybrid — Best accuracy",
        "mmr":        "MMR — Diverse results",
        "similarity": "Similarity — Fast search",
    }
    st.caption(retriever_labels[retriever_type])

    memory_type = st.selectbox(
        "🧠 Memory",
        ["Summary Buffer Memory ⭐",
         "Buffer Memory",
         "Window Memory (k=5)",
         "Summary Memory"],
        help="How the assistant remembers your conversation"
    )

    mode = st.selectbox(
        "🤖 Answer Mode",
        ["auto", "rag", "agent"],
        help="auto=smart routing | rag=knowledge base | agent=live data"
    )
    mode_labels = {
        "auto":  "Auto — smart routing",
        "rag":   "Knowledge — boutique style guide",
        "agent": "Live Data — sales & orders",
    }
    st.caption(mode_labels[mode])

    st.divider()
    st.markdown("**Ask Me About:**")
    quick_qs = {
        "👗 Style & Fashion": [
            "What to wear for Onam?",
            "Best fabric for Kerala summer?",
            "Kurta size guide for XL?",
        ],
        "📊 Business Insights": [
            "Which category sells most?",
            "Which supplier performs best?",
            "What is our return rate?",
        ],
        "✂️ Tailor & Design": [
            "Write brief for festive kurta M",
            "Care guide for silk saree",
            "Best Diwali outfit colors?",
        ]
    }
    for group, questions in quick_qs.items():
        st.markdown(f"**{group}**")
        for q in questions:
            if st.button(q, use_container_width=True, key=f"q_{q}"):
                st.session_state["quick_input"] = q

    st.divider()
    col_a, col_b = st.columns(2)
    with col_a:
        if st.button("🔨 Build RAG", use_container_width=True):
            st.session_state["rebuild_rag"] = True
    with col_b:
        if st.button("🗑️ Clear", use_container_width=True):
            st.session_state["messages"]  = []
            st.session_state["rag_chain"] = None
            st.session_state["agent"]     = None
            st.rerun()

    langsmith_on = bool(os.getenv("LANGCHAIN_API_KEY"))
    st.markdown("---")
    st.caption(f"LangSmith: {'✅ ON' if langsmith_on else '⚠️ Off'}")
    st.caption("Vector DB: ChromaDB")

# ── Session State ─────────────────────────────────────────────────────────────
for key in ["messages", "rag_chain", "agent", "rag_built"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key == "messages" else None

# ── Build RAG — with WinError 5 fix ──────────────────────────────────────────
if st.session_state.get("rebuild_rag"):
    st.session_state["rebuild_rag"] = False
    with st.spinner("🔨 Embedding boutique knowledge base..."):
        try:
            # Fix WinError 5: force-delete locked ChromaDB folder first
            chroma_path = os.path.join(ROOT, "genai", "chroma_db")
            if os.path.exists(chroma_path):
                try:
                    shutil.rmtree(chroma_path, ignore_errors=True)
                except Exception:
                    pass

            from genai.rag_pipeline import rebuild_vector_store
            rebuild_vector_store()
            st.session_state["rag_built"]  = True
            st.session_state["rag_chain"]  = None
            st.success("✅ Boutique knowledge loaded successfully!")
        except Exception as e:
            st.error(f"❌ RAG build failed: {e}")
            st.info("💡 Tip: Close any other Streamlit tabs or terminals "
                    "that might be using the ChromaDB folder, then try again.")

# ── Cache chains ──────────────────────────────────────────────────────────────
@st.cache_resource(show_spinner="⚡ Starting Anjali AI...")
def load_chains(ret_type, mem_type):
    try:
        from genai.agent import build_rag_chain, build_tool_agent
        chain = build_rag_chain(retriever_type=ret_type, memory_type=mem_type)
        agent = build_tool_agent()
        return chain, agent
    except Exception:
        return None, None

# ── Main Layout ───────────────────────────────────────────────────────────────
col_chat, col_info = st.columns([3, 1])

with col_chat:

    # ── Welcome Card — pure Streamlit (no raw HTML) ───────────────────────────
    if not st.session_state["messages"]:

        # Top banner
        st.markdown(f"""
<div style='background:linear-gradient(135deg,#1a0a2e,#16213e);
            border:1px solid #c9a96e44; border-radius:16px;
            padding:1.8rem 2rem; margin-bottom:1rem;'>
    <div style='font-size:1.5rem; font-weight:700; color:#c9a96e;
                font-family:serif; margin-bottom:0.3rem;'>
        ✨ &nbsp; Meet Anjali AI
    </div>
    <div style='color:#c9a96e88; font-size:0.88rem; margin-bottom:1rem;'>
        Muggam, Kerala &nbsp;·&nbsp; Embroidery · Customisation · Ethnic Elegance
    </div>
    <div style='color:#d4c5b0; font-size:0.95rem; line-height:1.8;'>
        Born from the heart of <strong style='color:#c9a96e;'>Anjali Ladies Boutique</strong>,
        this assistant carries the same love for hand-stitched embroidery,
        Kerala's festive traditions, and the art of dressing every woman beautifully.
        <br><br>
        Ask about <strong style='color:#e8c99a;'>Onam Kasavu sarees</strong>,
        <strong style='color:#e8c99a;'>the right kurta for monsoon season</strong>,
        <strong style='color:#e8c99a;'>writing a tailor design brief</strong>,
        or <strong style='color:#e8c99a;'>which category drives your boutique's revenue</strong>.
        One assistant. Every answer. No limits.
    </div>
    <div style='margin-top:1.2rem; padding:0.75rem 1rem;
                background:#c9a96e0d; border-radius:8px;
                border-left:3px solid #c9a96e55; color:#c9a96e;
                font-size:0.85rem;'>
        &#128161; <strong>First time?</strong> Click
        <strong>Build RAG</strong> in the sidebar to activate the
        boutique knowledge base &mdash; then ask anything.
    </div>
</div>
""", unsafe_allow_html=True)

        # Capability pills as Streamlit columns
        st.markdown(f"<div style='color:#c9a96e88; font-size:0.78rem; "
                    f"letter-spacing:1px; text-transform:uppercase; "
                    f"margin-bottom:8px;'>What Anjali AI Knows</div>",
                    unsafe_allow_html=True)

        pills = [
            ("🥻", "Sarees & Kasavu"),
            ("👘", "Kurta Styles"),
            ("🧵", "Embroidery"),
            ("📐", "Size & Fit"),
            ("🌿", "Fabric Care"),
            ("🎊", "Festival Dressing"),
            ("✂️", "Tailor Briefs"),
            ("📦", "Order Insights"),
            ("📈", "Sales Trends"),
            ("🛒", "Stock Advice"),
        ]
        cols = st.columns(5)
        for i, (icon, label) in enumerate(pills):
            with cols[i % 5]:
                st.markdown(
                    f"<div style='background:#c9a96e18; border:1px solid #c9a96e33;"
                    f"border-radius:30px; padding:5px 10px; text-align:center;"
                    f"font-size:0.82rem; color:#e8c99a; margin-bottom:6px;'>"
                    f"{icon} {label}</div>",
                    unsafe_allow_html=True
                )
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Chat History ──────────────────────────────────────────────────────────
    for msg in st.session_state["messages"]:
        avatar = "✨" if msg["role"] == "assistant" else "👤"
        with st.chat_message(msg["role"], avatar=avatar):
            st.markdown(msg["content"])

            if msg.get("sources"):
                badges = " ".join([
                    f"<span class='source-badge'>📄 {s}</span>"
                    for s in msg["sources"]
                ])
                st.markdown(f"Sources: {badges}", unsafe_allow_html=True)
            if msg.get("tools_used"):
                badges = " ".join([
                    f"<span class='tool-badge'>🔧 {t}</span>"
                    for t in msg["tools_used"]
                ])
                st.markdown(f"Tools: {badges}", unsafe_allow_html=True)
            if msg.get("mode_used"):
                st.caption(
                    f"Mode: {msg['mode_used']} · "
                    f"Retriever: {msg.get('retriever', retriever_type)} · "
                    f"Memory: {memory_type[:20]}"
                )

    # ── Chat Input ────────────────────────────────────────────────────────────
    default_input = st.session_state.pop("quick_input", "")
    user_input    = st.chat_input(
        "Ask Anjali AI anything about fashion, fabrics, sales, or your boutique..."
    )
    if default_input and not user_input:
        user_input = default_input

    if user_input:
        st.session_state["messages"].append({
            "role": "user", "content": user_input
        })
        with st.chat_message("user", avatar="👤"):
            st.markdown(user_input)

        with st.chat_message("assistant", avatar="✨"):
            with st.spinner("✨ Anjali AI is thinking..."):
                try:
                    from genai.agent import (
                        build_rag_chain, build_tool_agent,
                        get_answer, detect_question_type
                    )

                    chain, agent = load_chains(retriever_type, memory_type)

                    actual_mode = mode
                    if mode == "auto":
                        actual_mode = detect_question_type(user_input)

                    result = get_answer(
                        question=user_input,
                        chain=chain,
                        agent=agent,
                        mode=actual_mode
                    )

                    answer     = result["answer"]
                    sources    = result.get("sources", [])
                    tools_used = result.get("tools_used", [])

                    # fallback when answer is empty
                    if not answer or not answer.strip():
                        try:
                            from genai.rag_pipeline import search_knowledge_base
                            hits = search_knowledge_base(user_input, k=3)
                            if hits:
                                answer = "Here is what our boutique knowledge base says:\n\n"
                                for h in hits:
                                    label = h["source"].replace("_"," ").replace(".txt","").title()
                                    answer += f"**From {label}:**\n"
                                    answer += h["content"].strip() + "\n\n"
                                answer  = answer.strip()
                                sources = list(set(h["source"] for h in hits))
                            else:
                                answer = ("I could not find an answer. "
                                          "Please click **Build RAG** in the sidebar first.")
                        except Exception as fe:
                            answer = f"Could not generate a response. Error: {fe}"

                    st.markdown(answer)

                    if sources:
                        badges = " ".join([
                            f"<span class='source-badge'>📄 {s}</span>"
                            for s in sources
                        ])
                        st.markdown(f"Sources: {badges}",
                                    unsafe_allow_html=True)
                    if tools_used:
                        badges = " ".join([
                            f"<span class='tool-badge'>🔧 {t}</span>"
                            for t in tools_used
                        ])
                        st.markdown(f"Tools: {badges}",
                                    unsafe_allow_html=True)

                    mode_label = (f"{actual_mode} "
                                  f"({'auto-detected' if mode=='auto' else 'manual'})")
                    st.caption(f"Mode: {mode_label} · Retriever: {retriever_type}")

                    st.session_state["messages"].append({
                        "role":       "assistant",
                        "content":    answer,
                        "sources":    sources,
                        "tools_used": tools_used,
                        "mode_used":  actual_mode,
                        "retriever":  retriever_type,
                    })

                except ImportError as e:
                    st.error(f"❌ Missing package: {e}")
                    st.info("Run: pip install langchain langchain-anthropic "
                            "langchain-community chromadb sentence-transformers")
                except Exception as e:
                    st.error(f"❌ Error: {e}")
                    st.exception(e)

# ── Right Panel ───────────────────────────────────────────────────────────────
with col_info:
    st.markdown(f"<h4 style='color:{GOLD};'>✨ Anjali AI</h4>",
                unsafe_allow_html=True)

    chroma_path = os.path.join(ROOT, "genai", "chroma_db")
    rag_ready   = (os.path.exists(chroma_path) and
                   bool(os.listdir(chroma_path)))

    st.markdown("**Knowledge Status:**")
    if rag_ready:
        st.success("✅ Ready")
    else:
        st.warning("⚠️ Build RAG first")

    st.markdown("**Boutique Knowledge:**")
    kb_path = os.path.join(ROOT, "genai", "knowledge_base")
    if os.path.exists(kb_path):
        icons = {
            "product":  "🛍️",
            "size":     "📐",
            "fabric":   "🧵",
            "festival": "🎊",
        }
        for f in sorted(os.listdir(kb_path)):
            if f.endswith(".txt"):
                icon = next((v for k, v in icons.items() if k in f), "📄")
                label = f.replace("_", " ").replace(".txt", "").title()
                st.caption(f"{icon} {label}")

    st.divider()
    st.markdown("**Anjali AI Can:**")
    caps = [
        "👗 Style recommendations",
        "🥻 Kerala festival dressing",
        "📐 Size & fit guidance",
        "🧵 Fabric care advice",
        "✂️ Write tailor briefs",
        "📦 Read live orders",
        "📈 Analyse sales trends",
        "🛒 Stock recommendations",
        "🏆 Supplier comparison",
        "🎊 Occasion styling",
    ]
    for c in caps:
        st.caption(c)

    st.divider()
    st.markdown("**Session:**")
    msgs      = st.session_state.get("messages", [])
    user_msgs = sum(1 for m in msgs if m["role"] == "user")
    st.caption(f"💬 {user_msgs} questions asked")
    st.caption(f"🔍 Mode: {mode}")
    st.caption(f"🔧 Retriever: {retriever_type}")

    if bool(os.getenv("LANGCHAIN_API_KEY")):
        st.divider()
        st.caption("🔍 LangSmith tracing ON")
        st.caption("smith.langchain.com")

st.divider()
st.caption(
    "✨ Anjali AI · Anjali Ladies Boutique · Muggam, Kerala · "
    "Embroidery · Customisation · Ethnic Elegance"
)
