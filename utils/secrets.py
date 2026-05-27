"""utils/secrets.py — load API keys from .env locally or Streamlit secrets in cloud."""
import os
from dotenv import load_dotenv

def load_api_keys():
    """
    Load environment variables.
    Locally: reads .env file.
    In cloud (Streamlit Community Cloud / Railway): reads from os.environ
    which is populated from the platform's secrets/env-vars UI.
    """
    # Try .env first (local dev)
    env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
    load_dotenv(env_path)

    # If running on Streamlit Cloud, secrets are injected as env vars automatically.
    # Streamlit also exposes them via st.secrets — copy to os.environ so
    # non-Streamlit code (LangChain agents) can use os.getenv().
    try:
        import streamlit as st
        for k, v in st.secrets.items():
            if isinstance(v, str):
                os.environ.setdefault(k, v)
    except Exception:
        pass
