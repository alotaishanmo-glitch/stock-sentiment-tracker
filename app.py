"""
SentimentIQ — Streamlit entry point.

Starts the Flask analysis API in a background daemon thread, then renders
the SentimentIQ dashboard via an iframe pointing at the Flask server.

Usage:
    streamlit run app.py
"""

import socket
import threading

import streamlit as st

st.set_page_config(
    page_title="SentimentIQ",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# Hide Streamlit's own chrome so the dashboard fills the viewport cleanly
st.markdown(
    """
    <style>
    #MainMenu, header, footer, .stDeployButton { visibility: hidden !important; }
    .block-container { padding: 0 !important; max-width: 100% !important; }
    section[data-testid="stAppViewContainer"] > div:first-child { padding: 0 !important; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_resource(show_spinner=False)
def _start_api_server() -> int:
    """Start the Flask API server once and return the port it bound to."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    port = sock.getsockname()[1]
    sock.close()

    from api_server import create_app

    flask_app = create_app(port)
    thread = threading.Thread(
        target=lambda: flask_app.run(
            host="127.0.0.1",
            port=port,
            threaded=True,
            use_reloader=False,
        ),
        daemon=True,
        name="sentiq-api",
    )
    thread.start()
    return port


api_port = _start_api_server()

# Load the dashboard HTML and inject the API port so the JS fetch() knows where to call
import pathlib
html_path = pathlib.Path(__file__).parent / "frontend" / "SentimentIQ.html"
html = html_path.read_text(encoding="utf-8")
html = html.replace("SENTIQ_PORT_VALUE", str(api_port))

st.components.v1.html(html, height=3200, scrolling=False)
