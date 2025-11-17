import streamlit as st
import requests
from datetime import datetime

# -----------------------
#  Helpers: API calls
# -----------------------

def get_coingecko_bitcoin():
    url = "https://api.coingecko.com/api/v3/coins/bitcoin"
    params = {
        "localization": "false",
        "tickers": "false",
        "market_data": "true",
        "community_data": "false",
        "developer_data": "false",
        "sparkline": "false",
    }
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    return r.json()

def get_coingecko_global():
    url = "https://api.coingecko.com/api/v3/global"
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    return r.json()

def get_fear_and_greed():
    # Alternative.me Fear & Greed Index
    url = "https://api.alternative.me/fng/"
    params = {"limit": 1, "format": "json"}
    r = requests.get(url, params=params, timeout=10)
    r.raise_for_status()
    data = r.json()
    if "data" in data and data["data"]:
        return data["data"][0]
    return None


# -----------------------
#  Scoring logic (V1)
# -----------------------

def score_cycle(btc_price, btc_ath):
    """
    ניקוד מצב מחזור על בסיס מרחק מה-ATH
    """
    if not btc_price or not btc_ath:
        return 0, "לא ידוע"

    pct_from_ath = (btc_price / btc_ath) - 1  # למשל -0.4 אומר 40% מתחת ל-ATH

    if pct_from_ath <= -0.5:
        return 3, "Deep Value / Early Cycle"
    elif -0.5 < pct_from_ath <= -0.2:
        return 2, "Early / Mid Bull"
    elif -0.2 < pct_from_ath <= 0.1:
        return 0, "Mid / Late Bull"
    else:  # מעל 10% מעל ATH
        return -2, "Euphoria / Late Cycle"


def score_sentiment(fng_value):
    """
    ניקוד סנטימנט על בסיס Fear & Greed (0-100)
    Contrarian: פחד קיצוני = הזדמנות, תאוות בצע קיצונית = אזהרה
    """
    if fng_value is None:
        return 0, "לא ידוע"

    value = int(fng_value)

    if value <= 25:
        return 2, "Extreme Fear (Contrarian Bullish)"
    elif 25 < value <= 50:
        return 1, "Fear / Neutral"
    elif 50 < value <= 75:
        return -1, "Greed"
    else:  # > 75
        return -2, "Extreme Greed (Risky)"


def score_rotation(btc_dominance):
    """
    ניקוד רוטציה BTC מול אלטים על בסיס דומיננטיות בלבד (V1, בלי שיפוע היסטורי)
    """
    if btc_dominance is None:
        return 0, "לא ידוע"

    dom = btc_dominance

    if dom >= 55:
        return -1, "BTC Dominant – Altcoins Risky"
    elif 45 <= dom < 55:
        return 0, "Balanced – no clear Altseason"
    else:  # dom < 45
        return 1, "Altseason Zone – Higher Risk/Reward"


def decide_allocation(cycle_score, sentiment_score, rotation_score):
    """
    החלטת הקצאה גסה BTC / ETH / אלטים / סטייבלים
    על בסיס 3 ציונים בלבד (V1)
    """
    total = 0.5 * cycle_score + 0.3 * sentiment_score + 0.2 * rotation_score

    # ברירת מחדל
    allocation = {
        "BTC": 50,
        "ETH / Majors": 25,
        "Altcoins": 15,
        "Stablecoins": 10,
    }
    text = "שוק במצב ניטרלי יחסית. הקצאה מאוזנת."

    if total >= 2:
        # שוק במצב חיובי מוקדם/אמצעי, מותר קצת יותר אלטים
        allocation = {
            "BTC": 45,
            "ETH / Majors": 25,
            "Altcoins": 20,
            "Stablecoins": 10,
        }
        text = "Early/Mid Bull – אפשר להגדיל מעט חשיפה לאלטים, לשמור ליבה ב-BTC/ETH."

    elif 0.5 <= total < 2:
        allocation = {
            "BTC": 55,
            "ETH / Majors": 25,
            "Altcoins": 10,
            "Stablecoins": 10,
        }
        text = "שוק במצב חיובי אבל לא בטירוף – עדיפות ל-BTC/ETH, אלטים במינון נמוך."

    elif -1.5 <= total < 0.5:
        allocation = {
            "BTC": 60,
            "ETH / Majors": 20,
            "Altcoins": 5,
            "Stablecoins": 15,
        }
        text = "Late Bull / תחילת סיכון – לצמצם אלטים, לחזק BTC וסטייבלים."

    else:  # total < -1.5
        allocation = {
            "BTC": 40,
            "ETH / Majors": 10,
            "Altcoins": 0,
            "Stablecoins": 50,
        }
        text = "מצב מסוכן / בועה או פחד עמוק – עדיפות לסטייבלים ו-BTC, להתרחק מאלטים קטנים."

    return allocation, text, total


# -----------------------
#  Streamlit UI
# -----------------------

def main():
    st.set_page_config(
        page_title="מדד יומי להבנת השוק",
        page_icon="📊",
        layout="wide",
    )

    st.title("📊 מדד יומי להבנת השוק")
    st.caption(f"עדכון בזמן טעינת הדף – {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}")

    # ----- Fetch data -----
    with st.spinner("טוען נתונים מ-API..."):
        try:
            btc_data = get_coingecko_bitcoin()
            global_data = get_coingecko_global()
            fng_data = get_fear_and_greed()
        except Exception as e:
            st.error(f"בעיה בטעינת נתונים: {e}")
            return

    # ----- Parse BTC data -----
    mkt = btc_data.get("market_data", {})
    btc_price = mkt.get("current_price", {}).get("usd")
    btc_ath = mkt.get("ath", {}).get("usd")
    btc_ath_change_pct = mkt.get("ath_change_percentage", {}).get("usd")

    # ----- Parse Global data -----
    global_mkt = global_data.get("data", {})
    btc_dominance = global_mkt.get("market_cap_percentage", {}).get("btc")
    total_mkt_cap = global_mkt.get("total_market_cap", {}).get("usd")

    # ----- Fear & Greed -----
    fng_value = None
    fng_text = "לא ידוע"
    if fng_data:
        fng_value = fng_data.get("value")
        fng_text = fng_data.get("value_classification")

    # ----- Scoring -----
    cycle_score, cycle_label = score_cycle(btc_price, btc_ath)
    sentiment_score, sentiment_label = score_sentiment(fng_value)
    rotation_score, rotation_label = score_rotation(btc_dominance)

    allocation, allocation_text, total_score = decide_allocation(
        cycle_score, sentiment_score, rotation_score
    )

    # -----------------------
    #  TOP: "פסק הדין היומי"
    # -----------------------
    st.subheader("🧭 פסק הדין היומי")

    col1, col2, col3, col4 = st.columns(4)

    with col1:
        st.metric(
            label="מחיר BTC (USD)",
            value=f"{btc_price:,.0f}" if btc_price else "N/A",
            delta=f"{btc_ath_change_pct:.1f}% מה-ATH" if btc_ath_change_pct is not None else None,
        )

    with col2:
        st.metric(
            label="דומיננטיות BTC (%)",
            value=f"{btc_dominance:.1f}" if btc_dominance else "N/A",
        )

    with col3:
        st.metric(
            label="Fear & Greed",
            value=fng_value if fng_value is not None else "N/A",
            delta=fng_text,
        )

    with col4:
        st.metric(
            label="ציון כללי (Total Score)",
            value=f"{total_score:.2f}",
            delta=f"מחזור: {cycle_label}",
        )

    st.markdown("---")

    # -----------------------
    #  Allocation recommendation
    # -----------------------
    st.subheader("📌 המלצת הקצאה ליום זה (BTC / ETH / אלטים / סטייבלים)")
    st.write(allocation_text)

    alloc_cols = st.columns(len(allocation))
    for (name, pct), c in zip(allocation.items(), alloc_cols):
        c.metric(label=name, value=f"{pct}%")

    st.markdown("---")

    # -----------------------
    #  Details section
    # -----------------------
    st.subheader("🔍 פירוט מדדים ופרשנות")

    col_left, col_right = st.columns(2)

    with col_left:
        st.markdown("**מחזור / Valuation (Cycle Score)**")
        st.write(f"ציון: {cycle_score} | מצב: {cycle_label}")
        st.write(
            "- מבוסס בעיקר על מרחק המחיר הנוכחי של BTC מה-ATH.\n"
            "- ציון גבוה = אנחנו רחוקים מאוד מה-ATH (פוטנציאל מאקרו לעליות).\n"
            "- ציון נמוך/שלילי = קרובים או מעל ATH (סיכון בועה/תיקון)."
        )

        st.markdown("**סנטימנט (Sentiment Score)**")
        st.write(f"ציון: {sentiment_score} | מצב: {sentiment_label}")
        st.write(
            "- מבוסס על מדד Fear & Greed.\n"
            "- פחד קיצוני = סיגנל חיובי מנוגד-עדר.\n"
            "- תאוות בצע קיצונית = סיגנל אזהרה."
        )

    with col_right:
        st.markdown("**רוטציה BTC מול אלטים (Rotation Score)**")
        st.write(f"ציון: {rotation_score} | מצב: {rotation_label}")
        st.write(
            "- מבוסס כרגע על דומיננטיות BTC בלבד (V1).\n"
            "- דומיננטיות גבוהה = אלטים בסיכון.\n"
            "- דומיננטיות נמוכה = אזור רגיש של Altseason."
        )

        st.markdown("**שווי שוק כללי**")
        st.write(
            f"סה\"כ שווי שוק קריפטו (הערכה): "
            f"{total_mkt_cap:,.0f} $"
            if total_mkt_cap
            else "N/A"
        )

    st.markdown("---")
    st.caption(
        "גרסת V1 – מבוססת רק על נתוני CoinGecko + Fear & Greed. "
        "בהמשך אפשר להוסיף Open Interest, Funding Rates, On-chain ועוד."
    )


if __name__ == "__main__":
    main()
