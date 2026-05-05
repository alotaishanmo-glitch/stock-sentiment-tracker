"""
How It Works — SentimentIQ methodology page.

Explains every metric on the dashboard so users understand what the numbers mean.
"""

import streamlit as st

st.set_page_config(
    page_title="How It Works — SentimentIQ",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── Dark theme CSS matching the main dashboard ────────────────────────
st.markdown(
    """
    <style>
    #MainMenu, footer, .stDeployButton { visibility: hidden !important; }
    header[data-testid="stHeader"] { background: transparent !important; height: 0 !important; }
    [data-testid="stToolbar"] { display: none !important; }
    .stApp { background: #0A0A0F !important; }
    body { background: #0A0A0F !important; color: #ECEDF2 !important; }
    .block-container { padding: 32px 48px 60px !important; max-width: 860px !important; }

    h1 { color: #ECEDF2 !important; font-size: 32px !important; font-weight: 700 !important;
         letter-spacing: -0.02em !important; }
    h2 { color: #ECEDF2 !important; font-size: 20px !important; font-weight: 600 !important;
         margin-top: 40px !important; margin-bottom: 8px !important; }
    h3 { color: #9A9CA8 !important; font-size: 15px !important; font-weight: 500 !important;
         letter-spacing: 0.04em !important; text-transform: uppercase !important;
         margin-top: 28px !important; margin-bottom: 6px !important; }
    p, li { color: #C0C2CC !important; font-size: 14px !important; line-height: 1.7 !important; }
    a { color: #7AA9F7 !important; }
    code { color: #A5B4FC !important; background: rgba(99,102,241,0.12) !important;
           padding: 2px 6px !important; border-radius: 4px !important;
           font-size: 13px !important; }

    .method-card {
        background: linear-gradient(180deg, rgba(20,20,28,0.7), rgba(17,17,24,0.7));
        border: 1px solid rgba(255,255,255,0.06);
        border-radius: 14px;
        padding: 24px 28px;
        margin: 16px 0;
    }
    .zone-bar {
        display: flex; border-radius: 8px; overflow: hidden;
        height: 36px; margin: 16px 0; font-size: 11px; font-weight: 600;
        letter-spacing: 0.04em;
    }
    .zone-bar > div {
        display: flex; align-items: center; justify-content: center;
        color: rgba(255,255,255,0.9);
    }
    .back-link {
        display: inline-flex; align-items: center; gap: 6px;
        color: #7AA9F7 !important; text-decoration: none !important;
        font-size: 13px; margin-bottom: 24px;
    }
    .back-link:hover { text-decoration: underline !important; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ── Back link ─────────────────────────────────────────────────────────
st.markdown('<a class="back-link" href="/" target="_top">← Back to Dashboard</a>', unsafe_allow_html=True)

# ── Title ─────────────────────────────────────────────────────────────
st.markdown("# 📊 How It Works")
st.markdown(
    "A plain-English breakdown of every metric on the SentimentIQ dashboard — "
    "what we measure, how we measure it, and what to watch out for."
)

# ── 1. Sentiment Score ────────────────────────────────────────────────
st.markdown("## 1. Sentiment Score (0–100)")
st.markdown(
    """
    <div class="method-card">
    Every post and headline is scored by <strong>FinBERT</strong>, a language model
    trained specifically on financial text (earnings calls, analyst notes, SEC filings).

    <h3>How it works</h3>
    <ol>
    <li>FinBERT reads each piece of text and outputs three probabilities:
        <code>positive</code>, <code>negative</code>, and <code>neutral</code>.</li>
    <li>We compute a <strong>compound score</strong> = <code>positive − negative</code>,
        giving a value from −1 (maximally bearish) to +1 (maximally bullish).</li>
    <li>Each score is <strong>weighted by engagement</strong>:
        <ul>
        <li>Reddit: <code>log(upvotes + 1)</code> — viral posts carry more weight</li>
        <li>StockTwits: <code>log(likes + 1)</code></li>
        <li>News: equal weight (no engagement signal available)</li>
        </ul></li>
    <li>The weighted average is scaled from [−1, +1] to <strong>[0, 100]</strong> and displayed on the gauge.</li>
    </ol>
    </div>
    """,
    unsafe_allow_html=True,
)

st.markdown("### Score Zones")
st.markdown(
    """
    <div class="zone-bar">
      <div style="flex:35;background:#EF4444;">0–35 Bearish</div>
      <div style="flex:15;background:#FB923C;">36–50 Slightly Bearish</div>
      <div style="flex:15;background:#FACC15;color:#333;">51–65 Slightly Bullish</div>
      <div style="flex:35;background:#10B981;">66–100 Bullish</div>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 2. Data Sources ──────────────────────────────────────────────────
st.markdown("## 2. Data Sources")
st.markdown(
    """
    <div class="method-card">
    SentimentIQ pulls from <strong>three independent sources</strong>, all fetched
    in parallel with a 45-second timeout each:

    <h3>Reddit</h3>
    <p>Searches <code>r/wallstreetbets</code>, <code>r/stocks</code>,
    <code>r/investing</code>, and <code>r/options</code> via Reddit's public JSON API
    (no API key required). <em>Note:</em> this source may be unavailable on cloud
    deployments due to Reddit rate-limiting server IPs.</p>

    <h3>StockTwits</h3>
    <p>Pulls messages from the public stream API. Each message can carry a
    self-reported <strong>Bull</strong> or <strong>Bear</strong> label, which feeds
    into the bull/bear ratio shown on the StockTwits source card. Also subject to
    rate limits on cloud deployments.</p>

    <h3>News (Yahoo Finance)</h3>
    <p>Fetches headlines via Yahoo Finance RSS using <code>feedparser</code>.
    This is the most reliable source on cloud deployments since RSS feeds are
    rarely rate-limited.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 3. Bull / Bear Ratio ─────────────────────────────────────────────
st.markdown("## 3. Bull / Bear Ratio")
st.markdown(
    """
    <div class="method-card">
    <p>Posts with a <strong>compound score > 0</strong> are classified as
    <span style="color:#34D399;font-weight:600;">Bull</span>, and those with
    <strong>compound < 0</strong> as
    <span style="color:#F87171;font-weight:600;">Bear</span>.</p>

    <p>The percentage shown is:</p>
    <p style="text-align:center;font-size:15px;"><code>bull_count / (bull_count + bear_count) × 100</code></p>

    <p>StockTwits also has <em>self-reported</em> Bull/Bear labels that users tag
    on their own messages — these are shown separately in the StockTwits source card
    and are independent of FinBERT's classification.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 4. Signal Quality ────────────────────────────────────────────────
st.markdown("## 4. Signal Quality")
st.markdown(
    """
    <div class="method-card">
    Three bars that indicate how much you should trust the current score:

    <h3>Volume (0–10)</h3>
    <p>Total post/headline count mapped to a 0–10 scale:
    <code>min(10, round(mentions / 20))</code>. Higher = more data points backing
    the score. A score of 1/10 means roughly 20 posts; 10/10 means 200+.</p>

    <h3>Source Diversity (0–100%)</h3>
    <p>Percentage of the three sources (Reddit, StockTwits, News) that actually
    returned data. <strong>100%</strong> = all three active,
    <strong>33%</strong> = only one source contributed.</p>

    <h3>Model Certainty (0–100)</h3>
    <p>Derived from how much the source scores <em>agree</em> with each other.
    Computed as <code>100 × e<sup>−variance/200</sup></code> with a +5 bonus when
    all three sources are present. Low variance among sources = high certainty.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 5. Confidence Level ──────────────────────────────────────────────
st.markdown("## 5. Confidence Level")
st.markdown(
    """
    <div class="method-card">
    <p>Shown as a badge next to the gauge (<em>High / Medium / Low Confidence</em>).
    This reflects <strong>source agreement</strong>, not prediction accuracy.</p>

    <table style="width:100%;border-collapse:collapse;margin:12px 0;">
    <tr style="border-bottom:1px solid rgba(255,255,255,0.08);">
      <td style="padding:8px 0;color:#34D399;font-weight:600;">High</td>
      <td style="padding:8px 0;color:#C0C2CC;">Variance across source scores &lt; 25 — sources strongly agree</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.08);">
      <td style="padding:8px 0;color:#FACC15;font-weight:600;">Medium</td>
      <td style="padding:8px 0;color:#C0C2CC;">Variance between 25 and 100</td>
    </tr>
    <tr>
      <td style="padding:8px 0;color:#F87171;font-weight:600;">Low</td>
      <td style="padding:8px 0;color:#C0C2CC;">Variance &gt; 100, or only 1 source available</td>
    </tr>
    </table>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 6. Trend Direction ───────────────────────────────────────────────
st.markdown("## 6. Trend Direction")
st.markdown(
    """
    <div class="method-card">
    <p>Compares the average sentiment score of the <strong>first 2 data-bearing
    days</strong> vs. the <strong>last 2</strong> in the 7-day window.</p>

    <table style="width:100%;border-collapse:collapse;margin:12px 0;">
    <tr style="border-bottom:1px solid rgba(255,255,255,0.08);">
      <td style="padding:8px 0;color:#34D399;font-weight:600;">Improving</td>
      <td style="padding:8px 0;color:#C0C2CC;">Delta &gt; +3 points</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.08);">
      <td style="padding:8px 0;color:#F87171;font-weight:600;">Declining</td>
      <td style="padding:8px 0;color:#C0C2CC;">Delta &lt; −3 points</td>
    </tr>
    <tr style="border-bottom:1px solid rgba(255,255,255,0.08);">
      <td style="padding:8px 0;color:#9A9CA8;font-weight:600;">Stable</td>
      <td style="padding:8px 0;color:#C0C2CC;">Delta between −3 and +3 points</td>
    </tr>
    <tr>
      <td style="padding:8px 0;color:#9A9CA8;font-weight:600;">Insufficient Data</td>
      <td style="padding:8px 0;color:#C0C2CC;">Fewer than 2 days have posts — not enough history to compute a trend</td>
    </tr>
    </table>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── 7. Hot Topics ────────────────────────────────────────────────────
st.markdown("## 7. Hot Topics")
st.markdown(
    """
    <div class="method-card">
    <p>The most frequently mentioned words across all scored posts, after
    removing English stopwords and common finance boilerplate
    (<em>stock, buy, sell, hold, price, market, trading</em>, etc.).</p>

    <p>Pill size reflects relative frequency — the largest pill is the most
    mentioned word, and smaller pills trail off proportionally.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# ── Footer ────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(
    """
    <div style="color:#5C5E6B;font-size:12px;text-align:center;padding:16px 0;">
        SentimentIQ · Powered by FinBERT ·
        <a href="/" target="_top" style="color:#7AA9F7;text-decoration:none;">Back to Dashboard</a>
    </div>
    """,
    unsafe_allow_html=True,
)
