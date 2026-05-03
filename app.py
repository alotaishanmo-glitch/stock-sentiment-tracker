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
import traceback

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
    #MainMenu, footer, .stDeployButton { visibility: hidden !important; }
    header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; }
    [data-testid="stToolbar"] { display: none !important; }
    .stApp { background: #0A0A0F !important; }
    body { background: #0A0A0F !important; color: #ECEDF2 !important; }
    .block-container { padding: 16px 24px 0 !important; max-width: 100% !important; }

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

    iframe { border: none !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


# ── Logo + tagline (own row, above the search) ─────────────────────────
st.markdown(
    """
    <div style="display:flex;align-items:center;gap:12px;margin-bottom:10px;">
      <div style="font-size:26px;font-weight:700;color:#3B82F6;">⚡ SentimentIQ</div>
      <div style="color:#9A9CA8;font-size:13px;margin-top:6px;">
        Real-time stock sentiment from Reddit, StockTwits & news, scored with FinBERT
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)


# ── Read & validate ticker from URL ────────────────────────────────────
def _safe_ticker(raw: str, default: str = "TSLA") -> str:
    t = (raw or "").strip().upper()
    return t if t.isalpha() and 1 <= len(t) <= 10 else default


current_ticker = _safe_ticker(st.query_params.get("ticker", "TSLA"))


# ── Search bar ─────────────────────────────────────────────────────────
with st.form("ticker_search", clear_on_submit=False):
    c1, c2 = st.columns([8, 2])
    with c1:
        new_ticker = st.text_input(
            "Ticker",
            value=current_ticker,
            label_visibility="collapsed",
            placeholder="Enter ticker (e.g. TSLA, AAPL, NVDA)",
            key="ticker_input",
        )
    with c2:
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


# ── Defaults — used to backfill any missing fields so React never crashes
_FALLBACK_FIELDS = {
    "company": "—",
    "price": 0.0,
    "changePct": 0.0,
    "score": 50.0,
    "confidence": "Low",
    "mentions": 0,
    "bullPct": 50,
    "trendDelta": 0.0,
    "trendDirection": "Stable",
    "trend": [],
    "hotTopics": [],
    "sources": {
        "reddit": {"score": None, "count": 0, "topPost": None, "error": None},
        "stocktwits": {"score": None, "count": 0, "bull": 0, "bear": 0, "error": None},
        "news": {"score": None, "count": 0, "topHeadline": None, "error": None},
    },
    "errors": {},
}


def _normalise(result: dict, ticker: str) -> dict:
    """Ensure result has every field the React app reads, filling gaps with safe defaults."""
    out = {**_FALLBACK_FIELDS, **(result or {})}
    out["ticker"] = result.get("ticker", ticker)
    # Merge nested 'sources' so missing sub-keys don't crash React
    sources = {**_FALLBACK_FIELDS["sources"], **(result.get("sources") or {})}
    for k, v in sources.items():
        sources[k] = {**_FALLBACK_FIELDS["sources"][k], **(v or {})}
    out["sources"] = sources
    return out


# ── Run analysis (cached 5 min per ticker) ─────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def get_analysis(t: str) -> dict:
    from api_server import _run_analysis
    return _run_analysis(t)


error_message = None
trace = None
with st.spinner(
    f"Analysing ${current_ticker} — fetching Reddit, StockTwits & News, then scoring with FinBERT… "
    "(first load can take 1–3 minutes while the model downloads)"
):
    try:
        result = get_analysis(current_ticker)
    except Exception as exc:
        error_message = str(exc)
        trace = traceback.format_exc()
        result = {"ticker": current_ticker, "error": error_message}

# Surface any error prominently so we can see what's failing on Streamlit Cloud
if error_message:
    st.error(f"Analysis crashed: **{error_message}**")
    with st.expander("Show full traceback"):
        st.code(trace, language="text")
elif result.get("error"):
    st.warning(f"Partial result — {result['error']}")

# Show the raw result for debugging (collapsible — won't clutter normal use)
with st.expander("🔧 Debug: raw analysis result"):
    st.json(result)


# ── Inject result into HTML and render ─────────────────────────────────
result_full = _normalise(result, current_ticker)
html_path = pathlib.Path(__file__).parent / "frontend" / "SentimentIQ.html"
html = html_path.read_text(encoding="utf-8")
safe_json = json.dumps(result_full).replace("</", "<\\/")
html = html.replace("__INITIAL_DATA_JSON__", safe_json)

st.components.v1.html(html, height=2900, scrolling=False)
