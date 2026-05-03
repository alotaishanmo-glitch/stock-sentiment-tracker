"""
SentimentIQ — Streamlit entry point.

Analysis runs server-side in Python; results are injected into the HTML
template as JSON. The search uses Streamlit's native form + URL query params
so it works identically on Streamlit Community Cloud, HF Spaces, and locally
— no browser-to-localhost fetch, no cross-origin issues.

Usage:
    streamlit run app.py
"""

import json
import pathlib

import streamlit as st

st.set_page_config(
    page_title="SentimentIQ",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Style: hide Streamlit chrome, theme the search bar to match dashboard
st.markdown(
    """
    <style>
    /* Hide chrome */
    #MainMenu, footer, .stDeployButton { visibility: hidden !important; }
    header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; }
    [data-testid="stToolbar"] { display: none !important; }

    /* Page background */
    .stApp { background: #0A0A0F !important; }
    body { background: #0A0A0F !important; color: #ECEDF2 !important; }

    /* Tighten container */
    .block-container { padding: 16px 24px 0 !important; max-width: 100% !important; }

    /* Search row styling */
    .stTextInput > div > div > input {
        background: rgba(20,20,28,0.85) !important;
        color: #ECEDF2 !important;
        border: 1px solid rgba(255,255,255,0.10) !important;
        border-radius: 10px !important;
        padding: 10px 14px !important;
        font-family: 'JetBrains Mono', ui-monospace, monospace !important;
        font-size: 14px !important;
    }
    .stTextInput > div > div > input:focus {
        border-color: rgba(59,130,246,0.6) !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.15) !important;
    }
    .stButton > button, .stFormSubmitButton > button {
        background: linear-gradient(180deg, #4f8ef7, #3B82F6) !important;
        color: white !important;
        border: 1px solid rgba(59,130,246,0.6) !important;
        font-weight: 600 !important;
        border-radius: 10px !important;
        height: 42px !important;
        box-shadow: 0 6px 20px rgba(59,130,246,0.4) !important;
        transition: transform 0.15s !important;
    }
    .stButton > button:hover, .stFormSubmitButton > button:hover {
        transform: translateY(-1px);
    }

    /* iframe edges */
    iframe { border: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Read & validate ticker from URL ────────────────────────────────────
def _safe_ticker(raw: str, default: str = "TSLA") -> str:
    t = (raw or "").strip().upper()
    return t if t.isalpha() and 1 <= len(t) <= 10 else default


current_ticker = _safe_ticker(st.query_params.get("ticker", "TSLA"))


# ── Search bar (Streamlit native — works everywhere) ───────────────────
with st.form("ticker_search", clear_on_submit=False):
    c1, c2, c3 = st.columns([1, 6, 2])
    with c1:
        st.markdown(
            "<div style='font-size:22px;font-weight:700;color:#3B82F6;padding-top:6px;'>⚡ SentimentIQ</div>",
            unsafe_allow_html=True,
        )
    with c2:
        new_ticker = st.text_input(
            "Ticker",
            value=current_ticker,
            label_visibility="collapsed",
            placeholder="Enter ticker (e.g. TSLA, AAPL, NVDA)",
            key="ticker_input",
        )
    with c3:
        submitted = st.form_submit_button(
            "🔍 Analyse",
            use_container_width=True,
            type="primary",
        )

if submitted:
    cleaned = _safe_ticker(new_ticker, default=current_ticker)
    if cleaned != current_ticker:
        st.query_params["ticker"] = cleaned
        st.rerun()


# ── Run analysis (cached 5 min per ticker) ─────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_analysis(t: str) -> dict:
    from api_server import _run_analysis
    return _run_analysis(t)


with st.spinner(
    f"Fetching Reddit, StockTwits & News for ${current_ticker}, then scoring with FinBERT…"
):
    try:
        result = get_analysis(current_ticker)
    except Exception as exc:
        result = {
            "ticker": current_ticker,
            "error": str(exc),
            "errors": {"_global": str(exc)},
        }


# ── Inject result into HTML and render ─────────────────────────────────
html_path = pathlib.Path(__file__).parent / "frontend" / "SentimentIQ.html"
html = html_path.read_text(encoding="utf-8")
safe_json = json.dumps(result).replace("</", "<\\/")
html = html.replace("__INITIAL_DATA_JSON__", safe_json)

st.components.v1.html(html, height=2900, scrolling=False)
