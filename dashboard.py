import os
import math
from datetime import datetime, timezone

import streamlit as st
import requests


# ============================================================
#  CONFIG
# ============================================================

COINGECKO_BASE = "https://api.coingecko.com/api/v3"
FEAR_GREED_API = "https://api.alternative.me/fng/"
# Optional: if you want real news from newsapi.org – set this in Streamlit secrets or env
NEWSAPI_KEY = os.environ.get("NEWSAPI_KEY", None)  # optional
COINGLASS_API_KEY = os.environ.get("COINGLASS_API_KEY", None)  # optional for OI/Funding/Liquidations

# Last Bitcoin halving date (block-based approximation)
LAST_HALVING_DATE = datetime(2024, 4, 20, tzinfo=timezone.utc)


# ============================================================
#  HELPERS – FETCH DATA
# ============================================================

def fetch_json(url, params=None, headers=None, timeout=10):
    try:
        r = requests.get(url, params=params, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.warning(f"Data fetch error from {url}: {e}")
        return None


# ---------- NEWS (Macro + Crypto) ----------

def get_news_basic():
    """
    Returns a list of news items:
    [
      {
        "title": str,
        "summary": str,
        "why": str,
        "source": str,
        "url": str,
        "category": str,  # "Macro" / "Crypto" / "Flows / ETFs" / "Regulation"
        "published_at": datetime
      }, ...
    ]

    If NEWSAPI_KEY is not provided, returns static demo news.
    """
    if not NEWSAPI_KEY:
        # Static demo data – structure only.
        now = datetime.utcnow()
        return [
            {
                "title": "Fed signals potential rate cuts as inflation cools",
                "summary": "The US Federal Reserve hints that if inflation keeps trending lower, rate cuts may be considered in the coming year.",
                "why": "Lower rates usually support risk assets (stocks & crypto) as cash and bonds become less attractive.",
                "source": "Demo / Example",
                "url": "https://www.federalreserve.gov",
                "category": "Macro",
                "published_at": now,
            },
            {
                "title": "Bitcoin ETFs record strong weekly inflows",
                "summary": "Spot Bitcoin ETFs saw significant net inflows this week, indicating continued institutional demand.",
                "why": "Consistent ETF inflows suggest that larger, long-term players are accumulating BTC.",
                "source": "Demo / Example",
                "url": "https://www.coindesk.com",
                "category": "Flows / ETFs",
                "published_at": now,
            },
            {
                "title": "EU moves forward with MiCA crypto regulation framework",
                "summary": "The European Union advances its MiCA regulatory framework aimed at exchanges and stablecoin issuers.",
                "why": "Clear regulation can be long-term bullish for crypto adoption, but may pressure specific tokens in the short term.",
                "source": "Demo / Example",
                "url": "https://www.reuters.com",
                "category": "Regulation",
                "published_at": now,
            },
        ]

    # Example using NewsAPI.org (requires free API key)
    # You can customize the query/filters to better match macro + crypto.
    url = "https://newsapi.org/v2/everything"
    params = {
        "q": "crypto OR bitcoin OR ethereum OR blockchain OR 'digital assets'",
        "language": "en",
        "sortBy": "publishedAt",
        "pageSize": 10,
        "apiKey": NEWSAPI_KEY,
    }
    data = fetch_json(url, params=params)
    if not data or "articles" not in data:
        return []

    items = []
    for art in data["articles"]:
        title = art.get("title") or "No title"
        desc = art.get("description") or ""
        url = art.get("url") or ""
        source = (art.get("source") or {}).get("name", "Unknown")
        published_at = art.get("publishedAt") or ""
        try:
            dt = datetime.fromisoformat(published_at.replace("Z", "+00:00"))
        except Exception:
            dt = datetime.utcnow()

        # Very rough categorization by keywords
        title_lower = title.lower()
        if any(k in title_lower for k in ["fed", "inflation", "rates", "bond", "economy", "macro"]):
            category = "Macro"
        elif any(k in title_lower for k in ["etf", "flows", "inflows", "outflows"]):
            category = "Flows / ETFs"
        elif any(k in title_lower for k in ["regulation", "sec", "mica", "law", "legal"]):
            category = "Regulation"
        else:
            category = "Crypto"

        items.append(
            {
                "title": title,
                "summary": desc,
                "why": "Potential impact on risk appetite and capital flows into crypto.",
                "source": source,
                "url": url,
                "category": category,
                "published_at": dt,
            }
        )

    return items


# ---------- CORE MARKET DATA (CoinGecko + Fear & Greed) ----------

def get_coingecko_bitcoin():
    url = f"{COINGECKO_BASE}/coins/bitcoin"
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false",
    }
    return fetch_json(url, params=params)


def get_coingecko_global():
    url = f"{COINGECKO_BASE}/global"
    return fetch_json(url)


def get_fear_and_greed():
    params = {"limit": 1, "format": "json"}
    data = fetch_json(FEAR_GREED_API, params=params)
    if data and "data" in data and data["data"]:
        return data["data"][0]
    return None


# ---------- DERIVATIVES DATA (OI, Funding, Liquidations – CoinGlass) ----------

def get_coinglass_headers():
    if not COINGLASS_API_KEY:
        return None
    return {"coinglassSecret": COINGLASS_API_KEY}


def get_oi_data():
    """
    Fetch total open interest in USD from CoinGlass.
    If no API key is provided, returns a demo value with a flag.
    """
    if not COINGLASS_API_KEY:
        return {"value": 28_000_000_000, "demo": True}

    url = "https://open-api.coinglass.com/public/v2/futures/openInterest"
    params = {"symbol": "BTC", "currency": "USD"}
    data = fetch_json(url, params=params, headers=get_coinglass_headers())
    # You will need to adapt parsing depending on CoinGlass response structure
    if not data:
        return None
    # Placeholder: adapt to real response
    return {"value": 28_000_000_000, "demo": False}


def get_funding_data():
    """
    Fetch average funding rate for BTC (and possibly majors).
    If no API key – returns demo.
    """
    if not COINGLASS_API_KEY:
        return {
            "btc": 0.012 / 100,  # 0.012% -> 0.00012
            "majors_avg": 0.020 / 100,
            "demo": True,
        }

    url = "https://open-api.coinglass.com/public/v2/funding"
    params = {"symbol": "BTC"}
    data = fetch_json(url, params=params, headers=get_coinglass_headers())
    if not data:
        return None
    # Placeholder parsing; adjust according to real API response.
    return {
        "btc": 0.012 / 100,
        "majors_avg": 0.020 / 100,
        "demo": False,
    }


def get_liquidations_data():
    """
    Fetch 24h liquidations (long vs short).
    If no API key – returns demo.
    """
    if not COINGLASS_API_KEY:
        return {
            "total": 180_000_000,
            "longs": 140_000_000,
            "shorts": 40_000_000,
            "demo": True,
        }

    url = "https://open-api.coinglass.com/public/v2/liquidation"
    params = {"currency": "USD"}
    data = fetch_json(url, params=params, headers=get_coinglass_headers())
    if not data:
        return None
    # Placeholder; adjust parsing to real CoinGlass response.
    return {
        "total": 180_000_000,
            "longs": 140_000_000,
            "shorts": 40_000_000,
            "demo": False,
    }


# ============================================================
#  SCORING LOGIC
# ============================================================

def score_cycle(btc_price, btc_ath):
    """Score cycle mainly from distance to ATH and halving timing."""
    if not btc_price or not btc_ath:
        return 0, "Unknown"

    pct_from_ath = (btc_price / btc_ath) - 1  # -0.4 means 40% below ATH
    days_since_halving = (datetime.now(timezone.utc) - LAST_HALVING_DATE).days

    # Base score from distance to ATH
    if pct_from_ath <= -0.5:
        base = 3  # Deep value / early cycle
        label = "Deep Value / Early Cycle"
    elif -0.5 < pct_from_ath <= -0.2:
        base = 2  # Early/Mid bull
        label = "Early / Mid Bull"
    elif -0.2 < pct_from_ath <= 0.1:
        base = 0  # Mid/Late bull
        label = "Mid / Late Bull"
    else:
        base = -2  # Euphoria / late cycle
        label = "Euphoria / Late Cycle"

    # Halving adjustment
    if days_since_halving < 0:
        # Pre-halving – often accumulation
        base += 0.5
    elif 0 <= days_since_halving <= 270:
        base += 0.5  # Historically strong bull region
    # else: no adjustment

    return base, label


def score_sentiment(fng_value):
    """Contrarian sentiment scoring from Fear & Greed (0–100)."""
    if fng_value is None:
        return 0, "Unknown"

    v = int(fng_value)
    if v <= 25:
        return 2, "Extreme Fear (Contrarian Bullish)"
    elif 25 < v <= 50:
        return 1, "Fear / Neutral"
    elif 50 < v <= 75:
        return -1, "Greed"
    else:
        return -2, "Extreme Greed (Risky)"


def score_rotation(btc_dominance, eth_btc_ratio_change_30d=None):
    """
    Rotation = BTC season vs Altseason.
    Uses BTC dominance and optionally ETH/BTC 30D performance.
    """
    if btc_dominance is None:
        return 0, "Unknown"

    dom = btc_dominance
    score = 0
    label = "Balanced"

    if dom >= 55:
        score -= 1
        label = "BTC Dominant – Altcoins face headwind"
    elif 45 <= dom < 55:
        score += 0
        label = "No clear Altseason – mixed rotation"
    else:  # dom < 45
        score += 1
        label = "Altseason Zone – higher altcoin beta"

    if eth_btc_ratio_change_30d is not None:
        # If ETH strongly outperforms BTC over 30 days, increase altseason signal.
        if eth_btc_ratio_change_30d > 0.1:  # >10% outperformance
            score += 0.5
        elif eth_btc_ratio_change_30d < -0.1:
            score -= 0.5

    return score, label


def score_leverage(oi_usd, total_mkt_cap, funding_btc, funding_majors, liq_data):
    """
    Combine OI, funding and liquidations into a leverage risk score.
    More negative = more dangerous (over-leveraged), positive = cleaner.
    """
    if not oi_usd or not total_mkt_cap:
        return 0, "Unknown leverage conditions"

    oi_ratio = oi_usd / total_mkt_cap  # e.g. 0.06 = 6%

    score = 0.0
    notes = []

    # OI ratio scoring
    if oi_ratio < 0.03:
        score += 1
        notes.append("Low OI relative to market cap – less crowded leverage.")
    elif 0.03 <= oi_ratio <= 0.07:
        score += 0
        notes.append("Moderate OI – normal leverage environment.")
    else:
        score -= 1
        notes.append("High OI – crowded positions, higher liquidation risk.")

    # Funding scoring
    if funding_btc is not None and funding_majors is not None:
        avg_funding = (funding_btc + funding_majors) / 2
        # rough thresholds (per 8h)
        if avg_funding > 0.00025:  # >0.025% / 8h
            score -= 1
            notes.append("High positive funding – many leveraged longs.")
        elif 0 < avg_funding <= 0.00025:
            notes.append("Mild positive funding – bullish positioning but not extreme.")
        elif avg_funding < 0:
            score += 1
            notes.append("Negative funding – market leaning short, contrarian bullish.")

    # Liquidations scoring
    if liq_data:
        longs = liq_data.get("longs", 0)
        shorts = liq_data.get("shorts", 0)
        total = liq_data.get("total", 0)
        if total > 0 and longs > shorts * 2:
            score += 0.5
            notes.append("Recent long liquidations – some excess leveraged longs flushed.")
        elif total > 0 and shorts > longs * 2:
            score -= 0.5
            notes.append("Recent short liquidations – shorts squeezed, risk of pullback.")

    # Clamping score to a reasonable range
    score = max(-3, min(3, score))

    if score >= 1.5:
        label = "Clean / low leverage – safer environment."
    elif 0.5 <= score < 1.5:
        label = "Slightly favorable leverage conditions."
    elif -0.5 < score < 0.5:
        label = "Neutral – normal leverage conditions."
    elif -1.5 <= score <= -0.5:
        label = "Elevated leverage – be cautious with alts."
    else:
        label = "High leverage risk – avoid aggressive alt exposure."

    return score, label + " " + " ".join(notes)


def score_flows(stable_dom, btc_netflow=None, eth_netflow=None):
    """
    Score from stablecoin dominance and net exchange flows.
    Higher score = more supportive flows environment.
    """
    score = 0.0
    notes = []

    if stable_dom is not None:
        # Roughly: stablecoin dominance between 10-18% is healthy "dry powder"
        if 10 <= stable_dom <= 18:
            score += 1
            notes.append("Meaningful stablecoin 'dry powder' available.")
        elif stable_dom < 8:
            score -= 0.5
            notes.append("Lower stablecoin share – less sidelined capital.")
        else:
            notes.append("Stablecoin share neutral.")

    # Netflows (negative = outflows from exchanges = bullish)
    if btc_netflow is not None:
        if btc_netflow < 0:
            score += 0.5
            notes.append("BTC net outflows – accumulation signal.")
        elif btc_netflow > 0:
            score -= 0.5
            notes.append("BTC net inflows – potential sell pressure.")

    if eth_netflow is not None:
        if eth_netflow < 0:
            score += 0.25
            notes.append("ETH net outflows – accumulation signal.")
        elif eth_netflow > 0:
            score -= 0.25
            notes.append("ETH net inflows – potential sell pressure.")

    # Clamp
    score = max(-3, min(3, score))

    if score >= 1.5:
        label = "Supportive capital flows – environment favors upside."
    elif 0.5 <= score < 1.5:
        label = "Mildly supportive flows."
    elif -0.5 < score < 0.5:
        label = "Neutral flows."
    elif -1.5 <= score <= -0.5:
        label = "Flows slightly against risk assets."
    else:
        label = "Adverse flows – higher risk of downside."

    return score, label + " " + " ".join(notes)


def combine_scores(cycle_s, rotation_s, lev_s, sent_s, flows_s):
    """
    Combine all partial scores into one total score
    and a textual classification with a legend.
    """
    total = (
        0.35 * cycle_s +
        0.20 * rotation_s +
        0.20 * lev_s +
        0.15 * sent_s +
        0.10 * flows_s
    )

    if total >= 2.0:
        label = "Bullish – accumulate BTC, selective alts."
    elif 1.0 <= total < 2.0:
        label = "Constructive – BTC-led with room for majors."
    elif -0.5 < total < 1.0:
        label = "Mixed – favor BTC, reduce alts."
    elif -1.5 <= total <= -0.5:
        label = "Defensive – reduce alts, increase stables."
    else:
        label = "High risk – avoid alts, keep BTC + stables."

    return total, label


# ============================================================
#  INVESTOR PLAYBOOK – TEXT GENERATION (RULE-BASED)
# ============================================================

def build_investor_playbook(
    cycle_score, cycle_label,
    rotation_score, rotation_label,
    leverage_score, leverage_label,
    sentiment_score, sentiment_label,
    flows_score, flows_label,
    btc_dominance
):
    """
    Returns a dict with high-level allocation and narrative text.
    No AI – pure rule-based logic.
    """
    total_score, total_label = combine_scores(
        cycle_score, rotation_score, leverage_score, sentiment_score, flows_score
    )

    # Default allocation
    alloc = {
        "BTC": 50,
        "ETH / majors": 25,
        "Altcoins": 15,
        "Stablecoins": 10,
    }
    headline = "Neutral environment – balanced allocation."
    details = []

    # Cycle influence
    if cycle_score >= 2:
        details.append("Cycle suggests early/mid-bull positioning – upside still available.")
    elif cycle_score <= -1:
        details.append("Cycle suggests late-stage or euphoric conditions – downside risk increases.")

    # Rotation influence
    if btc_dominance and btc_dominance >= 55:
        details.append("BTC dominance is high and/or rising – market is BTC-led.")
    elif btc_dominance and btc_dominance <= 45:
        details.append("BTC dominance is low – altcoins can move faster but are riskier.")

    # Leverage influence
    details.append(f"Leverage conditions: {leverage_label}")
    details.append(f"Sentiment: {sentiment_label}")
    details.append(f"Flows: {flows_label}")

    # Now define allocation based on total score + dominance
    if total_score >= 2.0:
        alloc = {
            "BTC": 50,
            "ETH / majors": 25,
            "Altcoins": 15,
            "Stablecoins": 10,
        }
        headline = "Bullish setup – focus on BTC, with selective exposure to strong majors and altcoins."
    elif 1.0 <= total_score < 2.0:
        alloc = {
            "BTC": 55,
            "ETH / majors": 25,
            "Altcoins": 10,
            "Stablecoins": 10,
        }
        headline = "Constructive market – prioritize BTC and quality majors, keep altcoins sized modestly."
    elif -0.5 < total_score < 1.0:
        alloc = {
            "BTC": 60,
            "ETH / majors": 20,
            "Altcoins": 5,
            "Stablecoins": 15,
        }
        headline = "Mixed signals – lean into BTC, reduce altcoin exposure, keep some dry powder."
    elif -1.5 <= total_score <= -0.5:
        alloc = {
            "BTC": 50,
            "ETH / majors": 15,
            "Altcoins": 0,
            "Stablecoins": 35,
        }
        headline = "Defensive stance – avoid new altcoin risk, increase stablecoins and keep core BTC."
    else:  # total_score < -1.5
        alloc = {
            "BTC": 40,
            "ETH / majors": 10,
            "Altcoins": 0,
            "Stablecoins": 50,
        }
        headline = "High-risk environment – avoid altcoins, focus on capital preservation."

    return {
        "total_score": total_score,
        "total_label": total_label,
        "allocation": alloc,
        "headline": headline,
        "details": details,
    }


# ============================================================
#  STREAMLIT UI
# ============================================================

def render_score_legend():
    with st.expander("Score legend (how to read the total score)"):
        st.markdown(
            """
**Total Score Range (approx. -5 to +5):**

- **≥ 2.0 – Bullish:**  
  Accumulate BTC, allow some exposure to majors and selected altcoins.

- **1.0 – 2.0 – Constructive:**  
  BTC-led environment; prioritize BTC and quality majors, altcoins sized modestly.

- **-0.5 – 1.0 – Mixed / Cautious:**  
  Favor BTC, reduce altcoins, keep meaningful stablecoin buffer.

- **-1.5 – -0.5 – Defensive:**  
  Avoid new altcoin risk, increase stablecoins, keep core BTC.

- **< -1.5 – High Risk:**  
  Avoid altcoins entirely, focus on BTC + stables and capital preservation.
"""
        )


def render_oi_funding_liq_explanations():
    with st.expander("Deep explanation – OI, Funding Rates and Liquidations"):
        st.markdown(
            """
### 1. Open Interest (OI)
**What it is:**  
Total notional size of open futures/perpetual positions.  
It tells you *how much leverage is currently in the system*.

- **High OI** = many leveraged positions are open → the system is “stretched”.  
- **Low OI** = fewer leveraged positions → the market is “cleaner”.

**Why it matters:**  
When OI is high, even a relatively small price move can trigger **liquidation cascades**  
(one liquidation triggers another, etc.), causing sharp moves.

---

### 2. Funding Rates
**What it is:**  
The periodic fee paid between long and short traders on perpetual futures.

- **Positive funding** = longs pay shorts → more traders are long than short.  
- **Negative funding** = shorts pay longs → more traders are short than long.

**Why it matters:**

- **High positive funding** → the market is crowded with leveraged longs.  
  Price becomes fragile – a down move can trigger long liquidations.

- **Negative funding** → the market is crowded with shorts.  
  Often a contrarian bullish signal – a short squeeze can send price higher.

---

### 3. Liquidations
**What it is:**  
Forced closing of leveraged positions when margin is not sufficient.

- **Long liquidations** usually happen on sharp down moves.  
- **Short liquidations** usually happen on sharp up moves.

**Why it matters:**

- A spike in **long liquidations** often marks or approaches **local bottoms** –  
  leveraged longs have already been “washed out”.

- A spike in **short liquidations** often marks or approaches **local tops** –  
  shorts have been squeezed, and follow-through may be limited.

Together, **OI + Funding + Liquidations** describe *how stretched the market is*  
and who is likely to be forced to buy/sell next – a key input for short-term risk.
"""
        )


def render_news_section(news_items):
    st.header("📰 Macro & Crypto News – Smart Money Radar")
    st.caption("Goal: Understand macro forces, regulation and big capital flows that may drive the crypto cycle.")

    if not news_items:
        st.info("No news available at the moment. If you want live news, configure NEWSAPI_KEY.")
        return

    categories = ["All", "Macro", "Crypto", "Flows / ETFs", "Regulation"]
    col1, _ = st.columns([1, 3])
    with col1:
        selected_cat = st.selectbox("Filter by category:", categories)

    for item in news_items:
        if selected_cat != "All" and item["category"] != selected_cat:
            continue

        st.markdown(f"**[{item['category']}] {item['title']}**")
        if item.get("published_at"):
            st.caption(f"{item['source']} – {item['published_at'].strftime('%Y-%m-%d %H:%M UTC')}")
        else:
            st.caption(item["source"])

        if item.get("summary"):
            st.write(item["summary"])
        if item.get("why"):
            st.markdown(f"**Why it matters for markets:** {item['why']}")

        if item.get("url"):
            st.markdown(f"[Read full article ›]({item['url']})")

        st.markdown("---")


def render_metrics_section(
    btc_price, btc_ath, btc_ath_change_pct,
    btc_dominance, total_mkt_cap,
    fng_value, fng_text,
    oi_info, funding_info, liq_info,
    stable_mcap, stable_dom,
    cycle_score, cycle_label,
    rotation_score, rotation_label,
    leverage_score, leverage_label,
    sentiment_score, sentiment_label,
    flows_score, flows_label,
):
    st.header("📊 Market Metrics – Cycle, Rotation, Leverage & Flows")

    # TOP ROW – key metrics
    st.subheader("Top market snapshot")
    c1, c2, c3, c4 = st.columns(4)
    with c1:
        st.metric(
            label="BTC Price (USD)",
            value=f"{btc_price:,.0f}" if btc_price else "N/A",
            delta=f"{btc_ath_change_pct:.1f}% vs ATH" if btc_ath_change_pct is not None else None,
        )
    with c2:
        st.metric(
            label="BTC Dominance (%)",
            value=f"{btc_dominance:.1f}" if btc_dominance is not None else "N/A",
        )
    with c3:
        st.metric(
            label="Fear & Greed Index",
            value=fng_value if fng_value is not None else "N/A",
            delta=fng_text,
        )
    with c4:
        st.metric(
            label="Total Crypto Market Cap (USD)",
            value=f"{total_mkt_cap:,.0f}" if total_mkt_cap else "N/A",
        )

    st.markdown("---")

    # Cycle & valuation
    st.subheader("1) Cycle & Valuation (Bitcoin as the macro anchor)")
    st.markdown(
        """
**BTC Price vs ATH**  
Shows how far the current Bitcoin price is from its all-time high.  
Far below ATH → earlier in the cycle. Near or above ATH → late/euphoric phase.
"""
    )
    st.write(f"- Current BTC price: **{btc_price:,.0f} USD**" if btc_price else "- Current BTC price: N/A")
    if btc_ath and btc_ath_change_pct is not None:
        st.write(f"- Distance from ATH: **{btc_ath_change_pct:.1f}%**")
    st.write(f"- Cycle state (from scoring): **{cycle_label}** (score: {cycle_score:.2f})")
    st.write("Source: CoinGecko – Bitcoin market data")

    st.markdown("---")

    # Rotation
    st.subheader("2) Rotation – BTC vs Altcoins")
    st.markdown(
        """
**BTC Dominance**  
Measures Bitcoin's share of total crypto market cap.  
Rising dominance = capital prefers BTC and moves away from altcoins.  
Falling dominance = market is taking more risk and often altcoins outperform.
"""
    )
    st.write(f"- BTC Dominance: **{btc_dominance:.1f}%**" if btc_dominance is not None else "- BTC Dominance: N/A")
    st.write(f"- Rotation view: **{rotation_label}** (score: {rotation_score:.2f})")
    st.write("Source: CoinGecko Global Market Data")

    st.markdown("---")

    # Leverage & liquidity: OI, Funding, Liquidations
    st.subheader("3) Leverage & Liquidity – OI, Funding, Liquidations")

    render_oi_funding_liq_explanations()

    # OI
    oi_demo = oi_info.get("demo", False) if oi_info else False
    st.markdown("**Open Interest (OI)** – total futures/perpetual positions")
    if oi_info and oi_info.get("value") and total_mkt_cap:
        oi_val = oi_info["value"]
        oi_ratio = oi_val / total_mkt_cap
        st.write(f"- Estimated total OI (USD): **{oi_val:,.0f}**")
        st.write(f"- OI as % of total market cap: **{oi_ratio * 100:.2f}%**")
    else:
        st.write("- OI data unavailable – using neutral assumption in scoring.")
    if oi_demo:
        st.caption("Using demo OI value (configure COINGLASS_API_KEY for live data).")
    st.write("Source: CoinGlass (derivatives data, if API key configured)")

    # Funding
    funding_demo = funding_info.get("demo", False) if funding_info else False
    st.markdown("**Funding Rates** – cost of holding leveraged longs vs shorts")
    if funding_info:
        btc_f = funding_info.get("btc")
        maj_f = funding_info.get("majors_avg")
        if btc_f is not None:
            st.write(f"- BTC funding (per 8h): **{btc_f * 100:.4f}%**")
        if maj_f is not None:
            st.write(f"- Majors avg funding (per 8h): **{maj_f * 100:.4f}%**")
    else:
        st.write("- Funding data unavailable – using neutral assumption in scoring.")
    if funding_demo:
        st.caption("Using demo funding values (configure COINGLASS_API_KEY for live data).")
    st.write("Source: CoinGlass (perpetual futures funding, if API key configured)")

    # Liquidations
    liq_demo = liq_info.get("demo", False) if liq_info else False
    st.markdown("**Liquidations** – forced closing of leveraged positions")
    if liq_info:
        total_liq = liq_info.get("total")
        longs_liq = liq_info.get("longs")
        shorts_liq = liq_info.get("shorts")
        if total_liq is not None:
            st.write(f"- 24h total liquidations: **{total_liq:,.0f} USD**")
        if longs_liq is not None and shorts_liq is not None:
            st.write(f"- Longs: **{longs_liq:,.0f} USD**, Shorts: **{shorts_liq:,.0f} USD**")
    else:
        st.write("- Liquidation data unavailable – using neutral assumption in scoring.")
    if liq_demo:
        st.caption("Using demo liquidation values (configure COINGLASS_API_KEY for live data).")
    st.write("Source: CoinGlass (liquidation statistics, if API key configured)")

    st.write(f"**Leverage score:** {leverage_score:.2f} – {leverage_label}")

    st.markdown("---")

    # Sentiment & flows
    st.subheader("4) Sentiment & Capital Flows")

    st.markdown(
        """
**Fear & Greed Index**  
Composite sentiment from 0 (extreme fear) to 100 (extreme greed).  
Historically, extreme fear = better long-term entries; extreme greed = late-stage risk.
"""
    )
    st.write(f"- Fear & Greed value: **{fng_value}** – {fng_text}" if fng_value is not None else "- Fear & Greed: N/A")
    st.write(f"- Sentiment score: **{sentiment_score:.2f}** – {sentiment_label}")
    st.write("Source: Alternative.me – Crypto Fear & Greed Index")

    st.markdown(
        """
**Stablecoin Market Cap & Dominance**  
Shows how much "dry powder" sits in stablecoins that could potentially flow into risk assets.
"""
    )
    if stable_mcap is not None and stable_dom is not None:
        st.write(f"- Stablecoin market cap: **{stable_mcap:,.0f} USD**")
        st.write(f"- Stablecoin dominance: **{stable_dom:.2f}%**")
    else:
        st.write("- Stablecoin metrics unavailable or incomplete.")
    st.write(f"- Flows score: **{flows_score:.2f}** – {flows_label}")
    st.write("Source: CoinGecko – Stablecoin data")

    st.markdown("---")

    # Show partial scores
    st.subheader("5) Score overview (per pillar)")
    s1, s2, s3, s4, s5 = st.columns(5)
    with s1:
        st.metric("Cycle score", f"{cycle_score:.2f}")
    with s2:
        st.metric("Rotation score", f"{rotation_score:.2f}")
    with s3:
        st.metric("Leverage score", f"{leverage_score:.2f}")
    with s4:
        st.metric("Sentiment score", f"{sentiment_score:.2f}")
    with s5:
        st.metric("Flows score", f"{flows_score:.2f}")

    render_score_legend()


def render_investor_playbook(playbook, btc_dominance):
    st.header("🎯 Today's Investor Playbook")

    total_score = playbook["total_score"]
    total_label = playbook["total_label"]
    alloc = playbook["allocation"]
    headline = playbook["headline"]
    details = playbook["details"]

    st.subheader("High-level view")
    st.write(f"**Total market score:** {total_score:.2f} – {total_label}")
    st.write(f"**Headline:** {headline}")
    if btc_dominance is not None:
        st.caption(f"Current BTC dominance: {btc_dominance:.1f}%")

    st.markdown("---")

    st.subheader("Suggested high-level allocation (not financial advice)")
    cols = st.columns(len(alloc))
    for (name, pct), c in zip(alloc.items(), cols):
        c.metric(label=name, value=f"{pct}%")

    st.markdown("---")

    st.subheader("Why this stance (in simple terms)")
    for d in details:
        st.write(f"- {d}")

    st.markdown(
        """
> This playbook is purely rule-based and derived from live metrics  
> (cycle, rotation, leverage, sentiment and flows).  
> It is not financial advice, but a structured way to interpret the data each day.
"""
    )


def main():
    st.set_page_config(
        page_title="100M$ LIFE – Daily Market Dashboard",
        page_icon="📊",
        layout="wide",
    )

    st.title("100M$ LIFE – Daily Market Dashboard")
    st.caption(
        f"Macro, liquidity and crypto cycle – updated at "
        f"{datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}"
    )

    # ======================
    # Fetch data
    # ======================
    with st.spinner("Fetching live data..."):
        news_items = get_news_basic()
        btc_data = get_coingecko_bitcoin()
        global_data = get_coingecko_global()
        fng_data = get_fear_and_greed()
        oi_info = get_oi_data()
        funding_info = get_funding_data()
        liq_info = get_liquidations_data()

    # Parse BTC data
    mkt = btc_data.get("market_data", {}) if btc_data else {}
    btc_price = mkt.get("current_price", {}).get("usd")
    btc_ath = mkt.get("ath", {}).get("usd")
    btc_ath_change_pct = mkt.get("ath_change_percentage", {}).get("usd")

    # Parse global data
    global_mkt = global_data.get("data", {}) if global_data else {}
    btc_dom = global_mkt.get("market_cap_percentage", {}).get("btc")
    total_mkt_cap = global_mkt.get("total_market_cap", {}).get("usd")

    # Stablecoins (rough approximation: sum of known stable mcap vs total)
    # For V1, we approximate by taking USDT + USDC + DAI if available in global API,
    # or you can later fetch individual stablecoins from CoinGecko.
    stable_mcap = None
    stable_dom = None
    if global_mkt and "total_market_cap" in global_mkt and "market_cap_percentage" in global_mkt:
        # Very rough hack: if CoinGecko exposes stablecoins in market_cap_percentage, use it.
        # If not, you can later implement a dedicated stablecoin fetch.
        perc = global_mkt.get("market_cap_percentage", {})
        # These keys might not exist; we handle gracefully.
        stables_pct = 0
        for k in ["usdt", "usdc", "dai", "busd", "tusd"]:
            v = perc.get(k)
            if v:
                stables_pct += v
        if stables_pct and total_mkt_cap:
            stable_dom = stables_pct
            stable_mcap = total_mkt_cap * (stables_pct / 100.0)

    # Fear & Greed
    fng_value = None
    fng_text = "Unknown"
    if fng_data:
        fng_value = fng_data.get("value")
        fng_text = fng_data.get("value_classification")

    # For now we don't compute real ETH/BTC change or netflows –
    # these can be added later when you have APIs.
    eth_btc_change_30d = None
    btc_netflow = None
    eth_netflow = None

    # ======================
    # Scoring
    # ======================
    cycle_score, cycle_label = score_cycle(btc_price, btc_ath)
    sentiment_score, sentiment_label = score_sentiment(fng_value)
    rotation_score, rotation_label = score_rotation(btc_dom, eth_btc_change_30d)

    oi_val = oi_info.get("value") if oi_info else None
    funding_btc = funding_info.get("btc") if funding_info else None
    funding_majors = funding_info.get("majors_avg") if funding_info else None

    leverage_score, leverage_label = score_leverage(
        oi_usd=oi_val,
        total_mkt_cap=total_mkt_cap,
        funding_btc=funding_btc,
        funding_majors=funding_majors,
        liq_data=liq_info,
    )

    flows_score, flows_label = score_flows(
        stable_dom=stable_dom,
        btc_netflow=btc_netflow,
        eth_netflow=eth_netflow,
    )

    playbook = build_investor_playbook(
        cycle_score, cycle_label,
        rotation_score, rotation_label,
        leverage_score, leverage_label,
        sentiment_score, sentiment_label,
        flows_score, flows_label,
        btc_dominance=btc_dom,
    )

    # ======================
    # RENDER SECTIONS
    # ======================

    # Part 1 – News
    render_news_section(news_items)

    st.markdown("---")

    # Part 2 – Metrics
    render_metrics_section(
        btc_price, btc_ath, btc_ath_change_pct,
        btc_dom, total_mkt_cap,
        fng_value, fng_text,
        oi_info, funding_info, liq_info,
        stable_mcap, stable_dom,
        cycle_score, cycle_label,
        rotation_score, rotation_label,
        leverage_score, leverage_label,
        sentiment_score, sentiment_label,
        flows_score, flows_label,
    )

    st.markdown("---")

    # Part 3 – Investor Playbook
    render_investor_playbook(playbook, btc_dom)


if __name__ == "__main__":
    main()
