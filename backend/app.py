import os, pickle, warnings, io, math
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from flask import Flask, request, jsonify, send_file
from flask_cors import CORS

warnings.filterwarnings("ignore")

# ── Lazy TF import (only if models present) ──────────────────────
tf = None
keras_load = None
MODELS_LOADED = False
trained = {}

def try_load_models():
    global tf, keras_load, MODELS_LOADED, trained
    MODEL_DIR = os.environ.get("MODEL_DIR", os.path.join(os.path.dirname(__file__), "models"))
    crops = ["Onion", "Tomato", "Soybean"]
    files_ok = all(
        os.path.exists(os.path.join(MODEL_DIR, f"model_{c}.keras")) and
        os.path.exists(os.path.join(MODEL_DIR, f"scaler_{c}.pkl")) and
        os.path.exists(os.path.join(MODEL_DIR, f"metrics_{c}.pkl"))
        for c in crops
    )
    if not files_ok:
        print("⚠  Model files not found in", MODEL_DIR, "— running in DEMO mode.")
        return

    try:
        import tensorflow as _tf
        from tensorflow.keras.models import load_model
        tf = _tf
        keras_load = load_model

        for crop in crops:
            m_path = os.path.join(MODEL_DIR, f"model_{crop}.keras")
            s_path = os.path.join(MODEL_DIR, f"scaler_{crop}.pkl")
            me_path = os.path.join(MODEL_DIR, f"metrics_{crop}.pkl")
            model = load_model(m_path)
            with open(s_path,  "rb") as f: scaler  = pickle.load(f)
            with open(me_path, "rb") as f: metrics = pickle.load(f)
            trained[crop] = {"model": model, "scaler": scaler, "metrics": metrics}
            print(f"  ✓ {crop} loaded — MAE=₹{metrics['MAE']:,.0f}  R2={metrics['R2']:.3f}")

        MODELS_LOADED = True
        print("✅ All 3 AI models loaded successfully — AI MODE ACTIVE")
    except Exception as e:
        print(f"⚠  TF load failed: {e} — falling back to DEMO mode.")


# ── Historical data (same as Colab notebook) ─────────────────────
HISTORICAL = {
    "Onion": {
        "labels": ["Apr 24","May 24","Jun 24","Jul 24","Aug 24","Sep 24",
                   "Oct 24","Nov 24","Dec 24","Jan 25","Feb 25","Mar 25"],
        "values": [1076, 1300, 1700, 2400, 3329, 4700, 3141, 2800, 2645, 2200, 1800, 1400],
    },
    "Tomato": {
        "labels": ["Apr 24","May 24","Jun 24","Jul 24","Aug 24","Sep 24",
                   "Oct 24","Nov 24","Dec 24","Jan 25","Feb 25","Mar 25"],
        "values": [800, 700, 900, 2000, 3000, 3526, 2333, 1500, 1200, 1100, 900, 700],
    },
    "Soybean": {
        "labels": ["Apr 24","May 24","Jun 24","Jul 24","Aug 24","Sep 24",
                   "Oct 24","Nov 24","Dec 24","Jan 25","Feb 25","Mar 25"],
        "values": [4355, 4355, 4200, 4300, 4400, 4450, 4500, 4625, 4700, 4800, 4500, 4400],
    },
}

# Monthly modal prices (last known from notebook)
MONTHLY_PRICES = {
    "Onion": {
        "2025-01": 2200, "2025-02": 1800, "2025-03": 1400, "2025-04": 1100,
        "2025-05": 1300, "2025-06": 1600, "2025-07": 1500, "2025-08": 1700,
        "2025-09": 1900, "2025-10": 2100, "2025-11": 1800, "2025-12": 1600,
    },
    "Tomato": {
        "2025-01": 1100, "2025-02": 900,  "2025-03": 700,  "2025-04": 750,
        "2025-05": 900,  "2025-06": 1100, "2025-07": 1300, "2025-08": 1800,
        "2025-09": 2100, "2025-10": 1800, "2025-11": 1400, "2025-12": 1100,
    },
    "Soybean": {
        "2025-01": 4800, "2025-02": 4500, "2025-03": 4400, "2025-04": 4300,
        "2025-05": 4350, "2025-06": 4400, "2025-07": 4450, "2025-08": 4500,
        "2025-09": 4600, "2025-10": 4650, "2025-11": 4700, "2025-12": 4800,
    },
}

MARKET_INFO = {
    "Onion":   "Lasalgaon APMC, Nashik",
    "Tomato":  "Pune APMC",
    "Soybean": "Latur APMC",
}

COST = {"Onion": 850, "Tomato": 620, "Soybean": 3200}
MSP  = {"Onion": None, "Tomato": None, "Soybean": 4892}
LOOKBACK = 60

BOUNDS = {
    1:  {"Onion":[700,1400,1000],  "Tomato":[500,1200,800],   "Soybean":[4300,4900,4600]},
    2:  {"Onion":[600,1200,900],   "Tomato":[400,1000,700],   "Soybean":[4200,4800,4500]},
    3:  {"Onion":[600,1300,950],   "Tomato":[400,1100,700],   "Soybean":[4100,4700,4400]},
    4:  {"Onion":[650,1400,1000],  "Tomato":[350,1000,650],   "Soybean":[4000,4600,4300]},
    5:  {"Onion":[700,1500,1100],  "Tomato":[400,1200,750],   "Soybean":[4100,4700,4400]},
    6:  {"Onion":[900,1700,1300],  "Tomato":[500,1400,900],   "Soybean":[4200,4800,4500]},
    7:  {"Onion":[1000,2000,1500], "Tomato":[800,4000,1500],  "Soybean":[4300,5000,4650]},
    8:  {"Onion":[1200,2500,1800], "Tomato":[1000,5000,2000], "Soybean":[4400,5200,4800]},
    9:  {"Onion":[1500,3500,2200], "Tomato":[700,3500,1500],  "Soybean":[4400,5000,4700]},
    10: {"Onion":[1400,3000,2000], "Tomato":[600,2500,1200],  "Soybean":[4200,4900,4600]},
    11: {"Onion":[1000,2200,1500], "Tomato":[500,1500,900],   "Soybean":[4300,4900,4600]},
    12: {"Onion":[800,1800,1200],  "Tomato":[600,1600,1000],  "Soybean":[4400,5000,4700]},
}

CLIMATE_FACTOR = {"normal": 0.00, "sunny": 0.02, "cold": 0.08, "rainy": 0.12, "drought": 0.18}

CROP_CLIMATE_SENSITIVITY = {
    "normal":  {"Onion": 1.00, "Tomato": 1.00, "Soybean": 1.00},
    "sunny":   {"Onion": 1.03, "Tomato": 1.04, "Soybean": 1.06},
    "cold":    {"Onion": 1.08, "Tomato": 1.07, "Soybean": 1.05},
    "rainy":   {"Onion": 1.08, "Tomato": 1.05, "Soybean": 0.94},
    "drought": {"Onion": 1.10, "Tomato": 1.08, "Soybean": 1.09},
}

REGION_FACTOR = {
    "Onion":   {"lasalgaon":1.00,"pimpalgaon":0.96,"pune":1.08,"solapur":0.94,"nagpur":1.05,"mumbai":1.15,"nashik":0.98,"vashi":1.15},
    "Tomato":  {"pune":1.00,"nashik":0.94,"satara":0.97,"mumbai":1.12,"nagpur":1.04,"aurangabad":0.98},
    "Soybean": {"latur":1.00,"akola":0.97,"amravati":0.99,"nagpur":1.02,"washim":0.96,"hingoli":0.98},
}


# ── Helpers ───────────────────────────────────────────────────────

def get_region_factor(crop, location):
    if not location:
        return 1.0
    loc = location.lower().strip()
    mp  = REGION_FACTOR.get(crop, {})
    for key, val in mp.items():
        if key in loc or loc.split()[0] in key:
            return val
    return 1.0


def build_daily_series(crop):
    """Reconstruct daily series from monthly anchor points (same as notebook)."""
    mp = MONTHLY_PRICES[crop]
    dates  = [datetime.strptime(k, "%Y-%m") for k in mp.keys()]
    prices = list(mp.values())
    s = pd.Series(prices, index=pd.DatetimeIndex(dates), dtype=float)

    anchors   = s.copy()
    anchors.index = anchors.index + pd.DateOffset(days=14)
    start     = s.index[0]
    end       = s.index[-1] + pd.offsets.MonthEnd(0)
    daily_idx = pd.date_range(start=start, end=end, freq="D")
    resampled = (anchors.reindex(daily_idx).interpolate("linear").ffill().bfill().dropna())
    rng   = np.random.RandomState(42)
    noise = rng.normal(0, float(resampled.values.std()) * 0.02, len(resampled))
    return (resampled + noise).clip(lower=100)


def apply_seasonal_clip(raw_prices, crop, n_days):
    today_dt = datetime.today()
    clipped  = []
    for i, price in enumerate(raw_prices):
        fd    = today_dt + timedelta(days=i + 1)
        month = fd.month
        b     = BOUNDS.get(month, BOUNDS[today_dt.month])
        low, high, _ = b[crop]
        clipped.append(float(np.clip(price, low * 0.80, high * 1.20)))
    return np.array(clipped)


def ai_forecast(crop, climate, location, n_days):
    """Run real LSTM model forecast."""
    data   = trained[crop]
    series = build_daily_series(crop)

    cf_key = climate if climate in CROP_CLIMATE_SENSITIVITY else "normal"
    cf_base = 1 + (CLIMATE_FACTOR.get(cf_key, 0))
    cs      = CROP_CLIMATE_SENSITIVITY[cf_key][crop]
    rf      = get_region_factor(crop, location)
    total_f = round(cf_base * cs * rf, 3)

    scaler  = data["scaler"]
    model   = data["model"]
    prices  = series.values.astype(float).reshape(-1, 1)
    scaled  = scaler.transform(prices).flatten()
    window  = list(scaled[-LOOKBACK:])

    today      = datetime.today().date()
    last_train = series.index[-1].date()
    gap_days   = max(0, (today - last_train).days)

    for _ in range(gap_days):
        inp = np.array(window[-LOOKBACK:]).reshape(1, LOOKBACK, 1)
        p   = model.predict(inp, verbose=0)[0][0]
        window.append(p)

    # Today's estimated price
    today_p = float(scaler.inverse_transform([[window[-1]]])[0][0]) * rf

    # LSTM forecast
    lstm_raw = []
    win2     = window[:]
    for _ in range(n_days):
        inp = np.array(win2[-LOOKBACK:]).reshape(1, LOOKBACK, 1)
        p   = model.predict(inp, verbose=0)[0][0]
        lstm_raw.append(p)
        win2.append(p)

    lstm_prices = scaler.inverse_transform(np.array(lstm_raw).reshape(-1, 1)).flatten()
    lstm_prices = (lstm_prices * total_f).clip(min=50)
    lstm_prices = apply_seasonal_clip(lstm_prices, crop, n_days)

    # ARIMA-like path (server-side simplified AR)
    arima_prices = arima_simple(series, n_days, total_f, crop)

    # Ensemble 70/30
    ensemble = (0.70 * lstm_prices + 0.30 * arima_prices).clip(min=50)

    return today_p, lstm_prices.tolist(), arima_prices.tolist(), ensemble.tolist()


def arima_simple(series, n_days, climate_factor, crop):
    """Simplified AR(5) forecast matching notebook ARIMA."""
    recent = series[-365:].values if len(series) > 365 else series.values
    AR     = [0.35, 0.25, 0.18, 0.12, 0.10]
    window = list(recent[-5:] * climate_factor)
    out    = []
    month  = datetime.today().month
    b      = BOUNDS.get(month, BOUNDS[4])
    low, high, avg = b[crop]

    for i in range(n_days):
        ar_part = sum(AR[k] * window[-(k + 1)] for k in range(min(5, len(window))))
        mr      = (avg * climate_factor - window[-1]) * 0.018
        p       = float(np.clip(ar_part + mr, low * 0.80, high * 1.20))
        out.append(round(p))
        window.append(p)

    return np.array(out, dtype=float)


def demo_forecast(crop, climate, location, n_days):
    """Seeded statistical simulation — identical output for same inputs."""
    month       = datetime.today().month
    b           = BOUNDS.get(month, BOUNDS[4])
    low, high, avg = b[crop]

    cf_key = climate if climate in CLIMATE_FACTOR else "normal"
    cf  = 1 + CLIMATE_FACTOR[cf_key]
    cs  = CROP_CLIMATE_SENSITIVITY[cf_key][crop]
    rf  = get_region_factor(crop, location)
    tf  = cf * cs * rf

    hist_last = HISTORICAL[crop]["values"][-1] * tf
    seed = int(crop[0]) * 31 + month * 97 + n_days * 13 + round(tf * 100)
    rng  = np.random.RandomState(abs(seed) % (2**31 - 1))

    target    = avg * tf
    driftRate = (target - hist_last) / (n_days * 2.5)

    # LSTM-like
    lp, momentum = hist_last, 0
    lstm = []
    for i in range(n_days):
        seasonal = math.sin((i / 28) * math.pi * 2) * (high - low) * 0.07 * cf
        noise    = (rng.random() - 0.5) * (high - low) * 0.035
        momentum = 0.88 * momentum + 0.12 * (driftRate + seasonal + noise)
        lp       = float(np.clip(lp + momentum, low * 0.80, high * 1.20))
        lstm.append(round(lp))

    # ARIMA-like
    win5  = [HISTORICAL[crop]["values"][-i-1] * tf for i in range(4, -1, -1)]
    AR    = [0.35, 0.25, 0.18, 0.12, 0.10]
    ap    = win5[-1]
    arima = []
    for _ in range(n_days):
        ar_part = sum(AR[k] * win5[-(k+1)] for k in range(5))
        ma      = (rng.random() - 0.5) * (high - low) * 0.025
        mr      = (avg * tf - ap) * 0.018
        ap      = float(np.clip(ar_part + ma + mr, low * 0.80, high * 1.20))
        win5.append(ap)
        if len(win5) > 5: win5.pop(0)
        arima.append(round(ap))

    ensemble = [round(0.70 * l + 0.30 * a) for l, a in zip(lstm, arima)]
    current  = ensemble[0]
    return current, lstm, arima, ensemble


def reality_check(crop, price, days_ahead):
    fm = ((datetime.today().month - 1 + (days_ahead // 30)) % 12) + 1
    b  = BOUNDS.get(fm, BOUNDS[datetime.today().month])
    low, high, avg = b[crop]
    conf = 92 if days_ahead <= 7 else 85 if days_ahead <= 30 else 72 if days_ahead <= 60 else 60
    unc  = round(min(25, 5 + (days_ahead / 90) * 20))

    if price > high * 1.10:
        status   = "OPTIMISTIC"
        adjusted = round(price * 0.4 + high * 0.6)
    elif price < low * 0.90:
        status   = "CONSERVATIVE"
        adjusted = round(price * 0.5 + low * 0.5)
    else:
        status   = "REALISTIC"
        adjusted = price

    return {
        "status": status, "realistic_low": low, "realistic_high": high,
        "realistic_avg": avg, "adjusted": adjusted, "confidence": conf,
        "uncertainty_pct": unc, "forecast_month": fm,
    }


def build_response(crop, location, climate, n_days, current_price,
                   lstm_list, arima_list, ensemble_list, mode):
    today = datetime.today()
    dates = [(today + timedelta(days=i+1)).strftime("%d %b %Y") for i in range(n_days)]

    peak_idx   = int(np.argmax(ensemble_list))
    trough_idx = int(np.argmin(ensemble_list))
    avg_price  = int(np.mean(ensemble_list))
    change_pct = round((ensemble_list[-1] - ensemble_list[0]) / max(ensemble_list[0], 1) * 100, 1)
    trend      = "RISING" if change_pct > 5 else "FALLING" if change_pct < -5 else "STABLE"
    sentiment  = "BULLISH" if trend == "RISING" else "BEARISH" if trend == "FALLING" else "NEUTRAL"
    peak_price = ensemble_list[peak_idx]

    rc   = reality_check(crop, peak_price, peak_idx + 1)
    cost = COST[crop]
    msp  = MSP[crop]
    rf   = get_region_factor(crop, location)

    profit = {
        "cost_per_q":  cost,
        "profit_now":  round(current_price - cost),
        "profit_peak": round(peak_price - cost),
        "margin_now":  round((current_price - cost) / cost * 100, 1),
        "margin_peak": round((peak_price - cost) / cost * 100, 1),
        "msp": {
            "value": msp,
            "above": current_price >= msp,
            "note": ("Above MSP — open market better" if current_price >= msp
                     else "BELOW MSP — check NAFED procurement"),
        } if msp else None,
    }

    metrics_info = {}
    if MODELS_LOADED and crop in trained:
        m = trained[crop]["metrics"]
        metrics_info = {
            "MAE":  round(m["MAE"], 1),
            "RMSE": round(m["RMSE"], 1),
            "R2":   round(m["R2"],   3) if not math.isnan(m["R2"]) else None,
        }

    return {
        "crop": crop, "location": location, "climate": climate,
        "days": n_days, "market": MARKET_INFO[crop], "mode": mode,
        "metrics": metrics_info,
        "forecast": {
            "dates":    dates,
            "lstm":     [round(p) for p in lstm_list],
            "arima":    [round(p) for p in arima_list],
            "ensemble": [round(p) for p in ensemble_list],
        },
        "historical": HISTORICAL[crop],
        "summary": {
            "current_price": round(current_price),
            "avg_price":     avg_price,
            "peak_price":    round(peak_price),
            "peak_date":     dates[peak_idx],
            "peak_day":      peak_idx + 1,
            "trough_price":  round(ensemble_list[trough_idx]),
            "trough_date":   dates[trough_idx],
            "trough_day":    trough_idx + 1,
            "change_pct":    change_pct,
            "trend": trend, "sentiment": sentiment,
        },
        "reality_check": rc,
        "profit": profit,
        "region_factor": round(rf, 2),
    }


# ── Flask App ─────────────────────────────────────────────────────
app = Flask(__name__)

# Explicit CORS - critical for file:// and localhost origins
CORS(app, resources={r"/api/*": {
    "origins": "*",
    "methods": ["GET", "POST", "OPTIONS"],
    "allow_headers": ["Content-Type", "Accept", "Authorization"],
    "expose_headers": ["Content-Disposition"],
    "supports_credentials": False,
    "max_age": 600,
}})


@app.after_request
def add_cors_headers(response):
    """Force CORS headers on every response - belt and suspenders."""
    response.headers["Access-Control-Allow-Origin"]   = "*"
    response.headers["Access-Control-Allow-Methods"]  = "GET, POST, OPTIONS"
    response.headers["Access-Control-Allow-Headers"]  = "Content-Type, Accept, Authorization"
    response.headers["Access-Control-Expose-Headers"] = "Content-Disposition"
    return response


@app.route("/api/predict", methods=["GET", "POST", "OPTIONS"])
def predict():
    if request.method == "OPTIONS":
        return "", 204

    data     = request.get_json(force=True, silent=True) or {}
    crop     = data.get("crop",     "Onion")
    location = data.get("location", "")
    climate  = data.get("climate",  "normal")
    n_days   = int(data.get("days", 60))
    n_days   = max(7, min(90, n_days))

    print(f"\n-> /api/predict  crop={crop}  location={location}  climate={climate}  days={n_days}")

    if MODELS_LOADED:
        try:
            current, lstm, arima, ensemble = ai_forecast(crop, climate, location, n_days)
            mode = "ai"
            print(f"   AI forecast OK. Today est=Rs{current:.0f}  peak=Rs{max(ensemble):.0f}")
        except Exception as e:
            print(f"   AI forecast FAILED: {e} -- using demo")
            import traceback; traceback.print_exc()
            current, lstm, arima, ensemble = demo_forecast(crop, climate, location, n_days)
            mode = "demo"
    else:
        print("   Models not loaded -- using demo")
        current, lstm, arima, ensemble = demo_forecast(crop, climate, location, n_days)
        mode = "demo"

    print(f"   -> Returning mode={mode}")
    return jsonify(build_response(crop, location, climate, n_days,
                                  current, lstm, arima, ensemble, mode))


@app.route("/api/watchlist", methods=["GET", "OPTIONS"])
def watchlist():
    if request.method == "OPTIONS":
        return "", 204
    today  = datetime.today()
    month  = today.month
    result = []
    for crop in ["Onion", "Tomato", "Soybean"]:
        b = BOUNDS.get(month, BOUNDS[4])
        low, high, avg = b[crop]
        rng    = np.random.RandomState(crop.__hash__() % (2**31-1) + today.day)
        price  = int(avg + (rng.random() - 0.5) * (high - low) * 0.14)
        change = round(float((rng.random() - 0.47) * 7), 1)
        result.append({
            "crop": crop, "price": price, "change": change,
            "trend": "up" if change >= 0 else "down",
            "market": MARKET_INFO[crop],
        })
    return jsonify(result)


@app.route("/api/report", methods=["POST", "OPTIONS"])
def generate_report():
    """Generate a PDF report from prediction results."""
    if request.method == "OPTIONS":
        return "", 204

def generate_report():
    """Generate a PDF report from prediction results."""
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.lib.units import cm
    from reportlab.lib import colors
    from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer,
                                    Table, TableStyle, HRFlowable)
    from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

    data     = request.get_json(force=True) or {}
    crop     = data.get("crop", "Onion")
    location = data.get("location", "")
    climate  = data.get("climate",  "normal")
    n_days   = int(data.get("days", 60))
    n_days   = max(7, min(90, n_days))

    # Run forecast
    if MODELS_LOADED:
        try:
            current, lstm, arima, ensemble = ai_forecast(crop, climate, location, n_days)
            mode = "ai"
        except:
            current, lstm, arima, ensemble = demo_forecast(crop, climate, location, n_days)
            mode = "demo"
    else:
        current, lstm, arima, ensemble = demo_forecast(crop, climate, location, n_days)
        mode = "demo"

    resp_data = build_response(crop, location, climate, n_days,
                               current, lstm, arima, ensemble, mode)

    # ── Build PDF ────────────────────────────────────────────────
    buf = io.BytesIO()
    doc = SimpleDocTemplate(
        buf, pagesize=A4,
        leftMargin=2*cm, rightMargin=2*cm,
        topMargin=2*cm, bottomMargin=2*cm,
    )

    GREEN  = colors.HexColor("#22d492")
    DARK   = colors.HexColor("#0a1420")
    MIDGR  = colors.HexColor("#1a3020")
    GRAY   = colors.HexColor("#7da898")
    WHITE  = colors.white

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Title"],
        textColor=WHITE, fontSize=22, spaceAfter=4,
        fontName="Helvetica-Bold", alignment=TA_CENTER)
    sub_style = ParagraphStyle("Sub", parent=styles["Normal"],
        textColor=GREEN, fontSize=11, spaceBefore=0, spaceAfter=2,
        fontName="Helvetica", alignment=TA_CENTER)
    h2_style = ParagraphStyle("H2", parent=styles["Normal"],
        textColor=GREEN, fontSize=13, spaceBefore=12, spaceAfter=4,
        fontName="Helvetica-Bold")
    body_style = ParagraphStyle("Body", parent=styles["Normal"],
        textColor=colors.HexColor("#ccddcc"), fontSize=9.5, leading=14,
        fontName="Helvetica")
    mono_style = ParagraphStyle("Mono", parent=styles["Normal"],
        textColor=WHITE, fontSize=9, fontName="Courier")

    s   = resp_data["summary"]
    rc  = resp_data["reality_check"]
    pf  = resp_data["profit"]
    fc  = resp_data["forecast"]

    # Verdict
    change_pct = s["change_pct"]
    if s["trend"] == "RISING" and change_pct > 8:
        verdict = "STORE — Prices forecast to rise %.1f%%" % change_pct
        action  = "Consider storing up to %d days. Target: Rs %s/q" % (
            min(s["peak_day"], 30), f"{s['peak_price']:,}")
    elif s["trend"] == "FALLING":
        verdict = "SELL NOW — Prices falling %.1f%%" % change_pct
        action  = "Market trend is downward. Do not hold stock."
    elif pf["profit_now"] < 0:
        verdict = "CAUTION — Selling today = LOSS"
        action  = "Check government MSP procurement." if pf.get("msp") else "Wait for seasonal recovery."
    else:
        verdict = "STABLE — Sell when price reaches Rs %s+" % f"{int(s['current_price']*1.05):,}"
        action  = "Prices stable. Do not wait indefinitely — sell within 2 weeks."

    story = []

    # ── Header banner ────────────────────────────────────────────
    header_data = [[
        Paragraph("KISANMIND · AgriPredict.ai", title_style),
    ]]
    header_tbl = Table(header_data, colWidths=[17*cm])
    header_tbl.setStyle(TableStyle([
        ("BACKGROUND",  (0,0), (-1,-1), DARK),
        ("TOPPADDING",  (0,0), (-1,-1), 16),
        ("BOTTOMPADDING",(0,0),(-1,-1), 16),
        ("ROUNDEDCORNERS", [8]),
    ]))
    story.append(header_tbl)
    story.append(Spacer(1, 4))
    story.append(Paragraph(
        f"Farmer Profit Recommendation Report  |  {datetime.today().strftime('%d %B %Y')}",
        sub_style))
    story.append(Spacer(1, 10))
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN))
    story.append(Spacer(1, 10))

    # ── Meta info table ──────────────────────────────────────────
    meta = [
        ["Crop", crop, "Market", MARKET_INFO[crop]],
        ["Location", location or "—", "Climate", climate.title()],
        ["Forecast Days", f"{n_days} days", "Model", f"BiLSTM 70% + ARIMA 30% ({'AI Mode' if mode == 'ai' else 'Demo Mode'})"],
        ["Analysis Date", datetime.today().strftime("%d %b %Y"),
         "Forecast End", (datetime.today() + timedelta(days=n_days)).strftime("%d %b %Y")],
    ]
    meta_tbl = Table(meta, colWidths=[3.5*cm, 5*cm, 3.5*cm, 5*cm])
    meta_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (0,-1), MIDGR),
        ("BACKGROUND",   (2,0), (2,-1), MIDGR),
        ("TEXTCOLOR",    (0,0), (-1,-1), WHITE),
        ("FONTNAME",     (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTNAME",     (2,0), (2,-1), "Helvetica-Bold"),
        ("FONTNAME",     (1,0), (1,-1), "Helvetica"),
        ("FONTNAME",     (3,0), (3,-1), "Helvetica"),
        ("FONTSIZE",     (0,0), (-1,-1), 9),
        ("GRID",         (0,0), (-1,-1), 0.3, colors.HexColor("#22d49240")),
        ("ROWBACKGROUNDS",(0,0),(-1,-1), [colors.HexColor("#0d1e2e"), colors.HexColor("#0a1820")]),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
    ]))
    story.append(meta_tbl)
    story.append(Spacer(1, 14))

    # ── KPI cards ────────────────────────────────────────────────
    story.append(Paragraph("Price Summary", h2_style))
    kpi_data = [[
        Paragraph(f"<font color='#22d492'><b>Rs {s['current_price']:,}</b></font><br/>"
                  f"<font size=8 color='#7da898'>Today's Est. Price</font>", body_style),
        Paragraph(f"<font color='#22d492'><b>Rs {s['peak_price']:,}</b></font><br/>"
                  f"<font size=8 color='#7da898'>Peak Forecast (Day {s['peak_day']})</font>", body_style),
        Paragraph(f"<font color='#22d492'><b>Rs {s['avg_price']:,}</b></font><br/>"
                  f"<font size=8 color='#7da898'>Average Forecast</font>", body_style),
        Paragraph(f"<font color='{'#22d492' if change_pct >= 0 else '#f05265'}'>"
                  f"<b>{'+' if change_pct >= 0 else ''}{change_pct}%</b></font><br/>"
                  f"<font size=8 color='#7da898'>{s['trend']} · {s['sentiment']}</font>", body_style),
    ]]
    kpi_tbl = Table(kpi_data, colWidths=[4.25*cm]*4)
    kpi_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), DARK),
        ("GRID",         (0,0), (-1,-1), 0.5, GREEN),
        ("ALIGN",        (0,0), (-1,-1), "CENTER"),
        ("VALIGN",       (0,0), (-1,-1), "MIDDLE"),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 10),
    ]))
    story.append(kpi_tbl)
    story.append(Spacer(1, 12))

    # ── Model comparison ─────────────────────────────────────────
    story.append(Paragraph("Model Comparison (Endpoint Values)", h2_style))
    lstm_end    = fc["lstm"][-1]
    arima_end   = fc["arima"][-1]
    ens_end     = fc["ensemble"][-1]
    mc_data = [
        ["Model", "Day-1 Price", f"Day-{n_days} Price", "Change", "Weight"],
        ["LSTM (Bidirectional)",
         f"Rs {fc['lstm'][0]:,}", f"Rs {lstm_end:,}",
         f"{round((lstm_end-fc['lstm'][0])/fc['lstm'][0]*100,1):+.1f}%", "70%"],
        ["ARIMA (5,1,2)",
         f"Rs {fc['arima'][0]:,}", f"Rs {arima_end:,}",
         f"{round((arima_end-fc['arima'][0])/fc['arima'][0]*100,1):+.1f}%", "30%"],
        ["ENSEMBLE (Final)",
         f"Rs {fc['ensemble'][0]:,}", f"Rs {ens_end:,}",
         f"{change_pct:+.1f}%", "USE THIS"],
    ]
    mc_tbl = Table(mc_data, colWidths=[5*cm, 3*cm, 3*cm, 3*cm, 3*cm])
    mc_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  GREEN),
        ("TEXTCOLOR",     (0,0), (-1,0),  DARK),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("BACKGROUND",    (0,3), (-1,3),  MIDGR),
        ("TEXTCOLOR",     (0,1), (-1,-1), WHITE),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 9),
        ("GRID",          (0,0), (-1,-1), 0.3, colors.HexColor("#22d49240")),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.HexColor("#0d1e2e"), colors.HexColor("#0a1820")]),
        ("TOPPADDING",    (0,0), (-1,-1), 6),
        ("BOTTOMPADDING", (0,0), (-1,-1), 6),
        ("LEFTPADDING",   (0,0), (-1,-1), 8),
        ("ALIGN",         (1,0), (-1,-1), "CENTER"),
    ]))
    story.append(mc_tbl)
    story.append(Spacer(1, 12))

    # ── Day-by-day table ─────────────────────────────────────────
    story.append(Paragraph("Day-by-Day Forecast (Selected Days)", h2_style))
    best_idx  = int(np.argmax(fc["ensemble"]))
    worst_idx = int(np.argmin(fc["ensemble"]))
    tbl_rows  = [["Day", "Date", "LSTM (Rs)", "ARIMA (Rs)", "Ensemble (Rs)", "Conf", "Note"]]
    for i in range(n_days):
        if i != 0 and i % 10 != 9 and i != n_days - 1 and i != best_idx and i != worst_idx:
            continue
        note = "◆ BEST SELL" if i == best_idx else "▼ AVOID" if i == worst_idx else ""
        conf = max(60, round(92 - i * 0.4))
        tbl_rows.append([
            str(i+1), fc["dates"][i],
            f"{fc['lstm'][i]:,}", f"{fc['arima'][i]:,}", f"{fc['ensemble'][i]:,}",
            f"{conf}%", note,
        ])
    day_tbl = Table(tbl_rows, colWidths=[1*cm, 3.5*cm, 2.5*cm, 2.5*cm, 2.8*cm, 1.5*cm, 3.2*cm])
    day_tbl.setStyle(TableStyle([
        ("BACKGROUND",    (0,0), (-1,0),  colors.HexColor("#1a3020")),
        ("TEXTCOLOR",     (0,0), (-1,0),  GREEN),
        ("FONTNAME",      (0,0), (-1,0),  "Helvetica-Bold"),
        ("TEXTCOLOR",     (0,1), (-1,-1), WHITE),
        ("FONTNAME",      (0,1), (-1,-1), "Helvetica"),
        ("FONTSIZE",      (0,0), (-1,-1), 8),
        ("GRID",          (0,0), (-1,-1), 0.2, colors.HexColor("#22d49230")),
        ("ROWBACKGROUNDS",(0,1), (-1,-1), [colors.HexColor("#0d1e2e"), colors.HexColor("#0a1820")]),
        ("TOPPADDING",    (0,0), (-1,-1), 5),
        ("BOTTOMPADDING", (0,0), (-1,-1), 5),
        ("LEFTPADDING",   (0,0), (-1,-1), 6),
        ("ALIGN",         (0,0), (-1,-1), "CENTER"),
    ]))
    story.append(day_tbl)
    story.append(Spacer(1, 12))

    # ── Reality check + Profit side by side ──────────────────────
    story.append(Paragraph("Market Reality Check", h2_style))
    status_color = "#22d492" if rc["status"] == "REALISTIC" else "#f0b429" if rc["status"] == "OPTIMISTIC" else "#4d9fff"
    rc_rows = [
        ["Status", f"<font color='{status_color}'><b>{rc['status']}</b></font>"],
        ["Seasonal Range", f"Rs {rc['realistic_low']:,} – Rs {rc['realistic_high']:,}/q  (avg Rs {rc['realistic_avg']:,}/q)"],
        ["Confidence", f"{rc['confidence']}%  (±{rc['uncertainty_pct']}% uncertainty band)"],
        ["Conservative Est.", f"Rs {rc['adjusted']:,}/q"],
    ]
    rc_tbl = Table([[Paragraph(k, body_style), Paragraph(v, body_style)] for k, v in rc_rows],
                   colWidths=[4*cm, 13*cm])
    rc_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (0,-1), MIDGR),
        ("TEXTCOLOR",    (0,0), (-1,-1), WHITE),
        ("FONTNAME",     (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 9),
        ("GRID",         (0,0), (-1,-1), 0.3, colors.HexColor("#22d49230")),
        ("ROWBACKGROUNDS",(1,0),(-1,-1), [colors.HexColor("#0d1e2e"), colors.HexColor("#0a1820")]),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
    ]))
    story.append(rc_tbl)
    story.append(Spacer(1, 12))

    # ── Profit & Loss ────────────────────────────────────────────
    story.append(Paragraph("Profit & Loss per Quintal  (CACP 2024-25 Cultivation Costs)", h2_style))
    pnow_c  = "#22d492" if pf["profit_now"]  >= 0 else "#f05265"
    ppeak_c = "#22d492" if pf["profit_peak"] >= 0 else "#f05265"
    pl_rows = [
        ["Cost of Cultivation", f"Rs {pf['cost_per_q']:,}/q"],
        ["Sell TODAY profit", f"<font color='{pnow_c}'><b>Rs {pf['profit_now']:+,}/q  ({pf['margin_now']:+.1f}%)</b></font>"],
        ["Sell at PEAK profit", f"<font color='{ppeak_c}'><b>Rs {pf['profit_peak']:+,}/q  ({pf['margin_peak']:+.1f}%)</b></font>"],
        ["Best Sell Day", f"Day {s['peak_day']}  ·  {s['peak_date']}  ·  Rs {s['peak_price']:,}/q"],
    ]
    if pf.get("msp"):
        msp_c = "#22d492" if pf["msp"]["above"] else "#f05265"
        pl_rows.append(["Govt MSP (Soybean)",
                         f"<font color='{msp_c}'><b>Rs {pf['msp']['value']:,}/q  —  {pf['msp']['note']}</b></font>"])

    pl_tbl = Table([[Paragraph(k, body_style), Paragraph(v, body_style)] for k, v in pl_rows],
                   colWidths=[5*cm, 12*cm])
    pl_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (0,-1), MIDGR),
        ("TEXTCOLOR",    (0,0), (-1,-1), WHITE),
        ("FONTNAME",     (0,0), (0,-1), "Helvetica-Bold"),
        ("FONTSIZE",     (0,0), (-1,-1), 9),
        ("GRID",         (0,0), (-1,-1), 0.3, colors.HexColor("#22d49230")),
        ("ROWBACKGROUNDS",(1,0),(-1,-1), [colors.HexColor("#0d1e2e"), colors.HexColor("#0a1820")]),
        ("TOPPADDING",   (0,0), (-1,-1), 6),
        ("BOTTOMPADDING",(0,0), (-1,-1), 6),
        ("LEFTPADDING",  (0,0), (-1,-1), 8),
    ]))
    story.append(pl_tbl)
    story.append(Spacer(1, 12))

    # ── Verdict ──────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=1, color=GREEN))
    story.append(Spacer(1, 8))
    story.append(Paragraph("Farmer Recommendation", h2_style))
    verdict_tbl = Table([
        [Paragraph(f"<font color='#22d492'><b>{verdict}</b></font>", body_style)],
        [Paragraph(action, body_style)],
    ], colWidths=[17*cm])
    verdict_tbl.setStyle(TableStyle([
        ("BACKGROUND",   (0,0), (-1,-1), DARK),
        ("TOPPADDING",   (0,0), (-1,-1), 10),
        ("BOTTOMPADDING",(0,0), (-1,-1), 10),
        ("LEFTPADDING",  (0,0), (-1,-1), 14),
        ("BOX",          (0,0), (-1,-1), 1, GREEN),
    ]))
    story.append(verdict_tbl)
    story.append(Spacer(1, 12))

    # ── Footer ───────────────────────────────────────────────────
    story.append(HRFlowable(width="100%", thickness=0.5, color=GRAY))
    story.append(Spacer(1, 6))
    footer_txt = (
        "Data Sources: agmarknet.gov.in · NHRDF · Business Standard · CEIC/Directorate of Economics &amp; Statistics · KhetiVyapar<br/>"
        "Costs: CACP 2024-25 Maharashtra Cost of Cultivation Report   |   "
        "NOTE: Always verify with your local mandi before final decisions.<br/>"
        "© 2026 AgriPredict Engineering · BiLSTM + ARIMA Ensemble"
    )
    story.append(Paragraph(footer_txt, ParagraphStyle("Footer", parent=styles["Normal"],
        textColor=GRAY, fontSize=7.5, leading=11, fontName="Helvetica")))

    doc.build(story)
    buf.seek(0)
    fname = f"AgriPredict_{crop}_{datetime.today().strftime('%Y%m%d')}.pdf"
    return send_file(buf, as_attachment=True, download_name=fname, mimetype="application/pdf")


@app.route("/api/health", methods=["GET"])
def health():
    return jsonify({"status": "ok", "models_loaded": MODELS_LOADED,
                    "mode": "ai" if MODELS_LOADED else "demo"})


@app.route("/", methods=["GET"])
def index():
    return "AgriPredict.ai backend is running. Use /api/predict, /api/watchlist, /api/report"


if __name__ == "__main__":
    try_load_models()
    app.run(host="0.0.0.0", port=5000, debug=False, threaded=True)
