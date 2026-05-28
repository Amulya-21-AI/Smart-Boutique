"""
Smart-Boutique/genai/rag_pipeline.py
--------------------------------------
RAG Pipeline — Retrieval Augmented Generation
Covers from your LangChain notes:
  - Document Loading      (Section 4)
  - Chunking              (Section 5)
  - Embeddings            (Section 6)
  - Vector Store ChromaDB (Section 7)
  - Retrievers            (Section 2.4)
  - Advanced RAG          (Section 10)

Every import uses try/except — works on ALL LangChain versions.
"""

import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, ".env"))

# ── TEXT SPLITTER ─────────────────────────────────────────────────────────────
try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain_community.text_splitter import RecursiveCharacterTextSplitter

# ── DOCUMENT LOADERS ──────────────────────────────────────────────────────────
from langchain_community.document_loaders import TextLoader, DirectoryLoader

# ── VECTOR STORE ──────────────────────────────────────────────────────────────
try:
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma

# ── EMBEDDINGS ────────────────────────────────────────────────────────────────
# On Railway/cloud: use fast offline TF-IDF embeddings so the app starts
# instantly (no 400MB model download on startup).
# The AI assistant still works great for boutique Q&A with TF-IDF.

import os as _os
import numpy as _np
from sklearn.feature_extraction.text import TfidfVectorizer as _TFV
from langchain_core.embeddings import Embeddings as _Embeddings

class OfflineEmbeddings(_Embeddings):
    """
    Lightweight TF-IDF embedding — works 100% offline.
    No download needed. Starts instantly on Railway.
    """
    def __init__(self):
        self.vectorizer = _TFV(max_features=512)
        self._fitted    = False

    def _fit_if_needed(self, texts):
        if not self._fitted:
            self.vectorizer.fit(texts)
            self._fitted = True

    def embed_documents(self, texts):
        self._fit_if_needed(texts)
        matrix = self.vectorizer.transform(texts).toarray()
        norms  = _np.linalg.norm(matrix, axis=1, keepdims=True)
        norms[norms == 0] = 1
        return (matrix / norms).tolist()

    def embed_query(self, text):
        if not self._fitted:
            return [0.0] * 512
        vec  = self.vectorizer.transform([text]).toarray()[0]
        norm = _np.linalg.norm(vec)
        if norm == 0:
            return vec.tolist()
        return (vec / norm).tolist()

_embedding_backend  = "offline_tfidf"
_offline_embeddings = OfflineEmbeddings()
HuggingFaceEmbeddings = None
print("✅ Using offline TF-IDF embeddings (fast startup, no download needed)")

# ── BM25 RETRIEVER ────────────────────────────────────────────────────────────
try:
    from langchain_community.retrievers import BM25Retriever
except ImportError:
    from langchain.retrievers import BM25Retriever

# ── ENSEMBLE RETRIEVER ────────────────────────────────────────────────────────
# This moves around the most — try every known location
_ensemble_loaded = False
try:
    from langchain.retrievers import EnsembleRetriever
    _ensemble_loaded = True
except ImportError:
    pass

if not _ensemble_loaded:
    try:
        from langchain_community.retrievers import EnsembleRetriever
        _ensemble_loaded = True
    except ImportError:
        pass

if not _ensemble_loaded:
    try:
        from langchain_core.retrievers import EnsembleRetriever
        _ensemble_loaded = True
    except ImportError:
        pass

if not _ensemble_loaded:
    # Final fallback — disable hybrid, use similarity only
    EnsembleRetriever = None

# ── Paths ─────────────────────────────────────────────────────────────────────
KB_PATH         = os.path.join(ROOT, "genai", "knowledge_base")
CHROMA_PATH     = os.path.join(ROOT, "genai", "chroma_db")
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


def get_embeddings():
    """
    From notes Section 6 — Embeddings:
    Converts text into vectors so semantically similar text
    gets similar coordinates in vector space.

    Backend selection (auto):
      huggingface   → best quality, model downloaded once from internet
      offline_tfidf → works without internet, good for boutique Q&A
    """
    if _embedding_backend in ("huggingface", "huggingface_new"):
        return HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )
    elif _embedding_backend == "offline_tfidf":
        print(f"📊 Using offline TF-IDF embeddings (no internet needed)")
        return _offline_embeddings
    else:
        # Last resort — try again with HuggingFace
        return HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True}
        )


def load_documents():
    """
    From notes Section 4 — Document Loaders:
    Loads all .txt files from knowledge_base/ folder.
    """
    print("📂 Loading knowledge base documents...")
    loader = DirectoryLoader(
        KB_PATH,
        glob="**/*.txt",
        loader_cls=TextLoader,
        loader_kwargs={"encoding": "utf-8"}
    )
    docs = loader.load()
    print(f"   Loaded {len(docs)} documents")

    # Add metadata for Advanced RAG filtering (Section 10.1)
    for doc in docs:
        filename = os.path.basename(doc.metadata.get("source", ""))
        if "product"    in filename: doc.metadata["category"] = "products"
        elif "size"     in filename: doc.metadata["category"] = "sizing"
        elif "fabric"   in filename: doc.metadata["category"] = "fabric"
        elif "festival" in filename: doc.metadata["category"] = "occasions"
        doc.metadata["source_file"] = filename

    return docs


def split_documents(docs):
    """
    From notes Section 5 — Chunking:
    chunk_size=500, chunk_overlap=100 (20% overlap).
    """
    print("✂️  Splitting into chunks...")
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=500,
        chunk_overlap=100,
        separators=["\n\n", "\n", "━━━", "---", " ", ""],
        length_function=len
    )
    chunks = splitter.split_documents(docs)
    print(f"   Created {len(chunks)} chunks")
    return chunks


def build_vector_store(chunks=None):
    """
    From notes Section 7 — Vector Stores:
    ChromaDB stores all knowledge as searchable vectors.
    """
    embeddings = get_embeddings()

    if os.path.exists(CHROMA_PATH) and os.listdir(CHROMA_PATH):
        print("📚 Loading existing ChromaDB...")
        vs = Chroma(
            persist_directory=CHROMA_PATH,
            embedding_function=embeddings,
            collection_name="boutique_knowledge"
        )
        try:
            count = vs._collection.count()
            print(f"   {count} chunks loaded")
        except Exception:
            pass
        return vs

    print("🔨 Building ChromaDB from scratch...")
    if chunks is None:
        docs   = load_documents()
        chunks = split_documents(docs)

    vs = Chroma.from_documents(
        documents=chunks,
        embedding=embeddings,
        persist_directory=CHROMA_PATH,
        collection_name="boutique_knowledge"
    )
    print(f"   ✅ {len(chunks)} chunks saved to ChromaDB")
    return vs


def get_retriever(search_type="hybrid", k=4):
    """
    From notes Section 2.4 + 10.1:

    similarity → Naive RAG
    mmr        → Advanced RAG (diverse results)
    hybrid     → Advanced RAG (Vector + BM25)

    Falls back to similarity if EnsembleRetriever not available.
    """
    vs = build_vector_store()

    if search_type == "similarity":
        print(f"🔍 Similarity Retriever (k={k})")
        return vs.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )

    elif search_type == "mmr":
        print(f"🔍 MMR Retriever (k={k})")
        return vs.as_retriever(
            search_type="mmr",
            search_kwargs={"k": k, "fetch_k": k * 3, "lambda_mult": 0.7}
        )

    elif search_type == "hybrid":
        if EnsembleRetriever is None:
            print("⚠️  EnsembleRetriever not available — using similarity")
            return vs.as_retriever(
                search_type="similarity",
                search_kwargs={"k": k}
            )

        print(f"🔍 Hybrid Retriever (vector + BM25, k={k})")
        dense  = vs.as_retriever(
            search_type="similarity",
            search_kwargs={"k": k}
        )
        docs    = load_documents()
        chunks  = split_documents(docs)
        sparse  = BM25Retriever.from_documents(chunks)
        sparse.k = k

        return EnsembleRetriever(
            retrievers=[dense, sparse],
            weights=[0.6, 0.4]
        )

    return vs.as_retriever(search_kwargs={"k": k})


def get_filtered_retriever(category: str, k: int = 4):
    """Metadata filtered retriever — from notes Section 10.1."""
    vs = build_vector_store()
    return vs.as_retriever(
        search_type="similarity",
        search_kwargs={"k": k, "filter": {"category": category}}
    )


def rebuild_vector_store():
    """Force rebuild — call after updating knowledge base files."""
    import shutil
    if os.path.exists(CHROMA_PATH):
        shutil.rmtree(CHROMA_PATH)
        print("🗑️  Cleared ChromaDB")
    docs   = load_documents()
    chunks = split_documents(docs)
    build_vector_store(chunks)
    print("✅ Vector store rebuilt")


def search_knowledge_base(query: str, k: int = 4) -> list:
    """Direct search for testing what RAG retrieves."""
    vs      = build_vector_store()
    results = vs.similarity_search_with_score(query, k=k)
    return [
        {
            "content":  doc.page_content,
            "source":   doc.metadata.get("source_file", "unknown"),
            "category": doc.metadata.get("category", "unknown"),
            "score":    round(float(score), 4)
        }
        for doc, score in results
    ]


if __name__ == "__main__":
    rebuild_vector_store()
    for q in ["Kurta for wedding?", "Size XL in inches?", "Kerala summer fabric?"]:
        print(f"\nQuery: {q}")
        for r in search_knowledge_base(q, k=2):
            print(f"  [{r['source']}] {r['content'][:80]}...")
