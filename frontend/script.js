

'use strict';

const API_BASE = 'http://localhost:5000/api';


window.AGRI_LANG = localStorage.getItem('agri_lang') || 'en';

// Shared translations used across ALL pages
window.SHARED_TRANSLATIONS = {
  en: {
    nav_tech:    'Technology',
    nav_predict: 'Prediction Tool',
    nav_foryou:  'For You',
    // Trend labels
    rising:  'RISING',
    falling: 'FALLING',
    stable:  'STABLE',
    bullish: 'BULLISH',
    bearish: 'BEARISH',
    neutral: 'NEUTRAL',
    // Common UI
    loading:       'Analysing…',
    error_generic: 'Something went wrong. Please try again.',
    sell_now:      'Sell Now',
    wait:          'Wait',
    hold:          'Hold',
    above_msp:     'Above MSP — open market better',
    below_msp:     'BELOW MSP — check NAFED procurement',
    // Profit card
    profit_now:  'Profit Today',
    profit_peak: 'Profit at Peak',
    cost_label:  'Cultivation Cost',
    // Chart labels
    chart_lstm:     'LSTM',
    chart_arima:    'ARIMA',
    chart_ensemble: 'Ensemble',
    chart_historic: 'Historical',
  },
  mr: {
    nav_tech:    'तंत्रज्ञान',
    nav_predict: 'किंमत अंदाज',
    nav_foryou:  'तुमच्यासाठी',
    rising:  'वाढत आहे',
    falling: 'घसरत आहे',
    stable:  'स्थिर',
    bullish: 'तेजी',
    bearish: 'मंदी',
    neutral: 'तटस्थ',
    loading:       'विश्लेषण सुरू…',
    error_generic: 'काहीतरी चुकले. पुन्हा प्रयत्न करा.',
    sell_now:  'आत्ता विका',
    wait:      'थांबा',
    hold:      'साठवा',
    above_msp: 'MSP पेक्षा जास्त — खुली बाजारपेठ चांगली',
    below_msp: 'MSP पेक्षा कमी — NAFED खरेदी तपासा',
    profit_now:  'आजचा नफा',
    profit_peak: 'शिखरावर नफा',
    cost_label:  'उत्पादन खर्च',
    chart_lstm:     'LSTM',
    chart_arima:    'ARIMA',
    chart_ensemble: 'एन्सेम्बल',
    chart_historic: 'ऐतिहासिक',
  },
  hi: {
    nav_tech:    'तकनीक',
    nav_predict: 'मूल्य पूर्वानुमान',
    nav_foryou:  'आपके लिए',
    rising:  'बढ़ रहा है',
    falling: 'गिर रहा है',
    stable:  'स्थिर',
    bullish: 'तेजी',
    bearish: 'मंदी',
    neutral: 'तटस्थ',
    loading:       'विश्लेषण हो रहा है…',
    error_generic: 'कुछ गलत हुआ। फिर से प्रयास करें।',
    sell_now:  'अभी बेचें',
    wait:      'प्रतीक्षा करें',
    hold:      'रोकें',
    above_msp: 'MSP से ऊपर — खुला बाज़ार बेहतर',
    below_msp: 'MSP से नीचे — NAFED खरीद जाँचें',
    profit_now:  'आज का लाभ',
    profit_peak: 'शिखर पर लाभ',
    cost_label:  'उत्पादन लागत',
    chart_lstm:     'LSTM',
    chart_arima:    'ARIMA',
    chart_ensemble: 'एन्सेम्बल',
    chart_historic: 'ऐतिहासिक',
  },
};

/** Helper: get a translation string for the current language */
window.t = function(key) {
  const lang = window.AGRI_LANG || 'en';
  const dict = window.SHARED_TRANSLATIONS[lang] || window.SHARED_TRANSLATIONS['en'];
  return dict[key] || window.SHARED_TRANSLATIONS['en'][key] || key;
};

/** Apply nav translations on any page */
function applyNavTranslations() {
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    const val = window.t(key);
    if (val) el.textContent = val;
  });
}

/** Global setLang — works on all pages */
window.setLang = function(lang) {
  window.AGRI_LANG = lang;
  localStorage.setItem('agri_lang', lang);
  document.documentElement.lang = lang;

  if (lang === 'mr' || lang === 'hi') {
    document.body.style.fontFamily = "'Noto Sans Devanagari', 'Plus Jakarta Sans', sans-serif";
  } else {
    document.body.style.fontFamily = '';
  }

  applyNavTranslations();

  document.querySelectorAll('.lang-btn').forEach(btn => {
    btn.classList.toggle('active',
      (btn.textContent.trim() === 'EN'     && lang === 'en') ||
      (btn.textContent.trim() === 'मराठी' && lang === 'mr') ||
      (btn.textContent.trim() === 'हिंदी' && lang === 'hi')
    );
  });

  // Fire custom event so predict.html / foryou.html can react
  window.dispatchEvent(new CustomEvent('langchange', { detail: { lang } }));
};

// ════════════════════════════════════════════════════════════
//  OFFLINE FALLBACK ENGINE (identical logic to backend)
// ════════════════════════════════════════════════════════════

const MARKET_INFO = {
  Onion:   'Lasalgaon APMC, Nashik',
  Tomato:  'Pune APMC',
  Soybean: 'Latur APMC',
};
const COST = { Onion: 850, Tomato: 620, Soybean: 3200 };
const MSP  = { Onion: null, Tomato: null, Soybean: 4892 };

const BOUNDS = {
  1:  { Onion:[700,1400,1000],  Tomato:[500,1200,800],   Soybean:[4300,4900,4600] },
  2:  { Onion:[600,1200,900],   Tomato:[400,1000,700],   Soybean:[4200,4800,4500] },
  3:  { Onion:[600,1300,950],   Tomato:[400,1100,700],   Soybean:[4100,4700,4400] },
  4:  { Onion:[650,1400,1000],  Tomato:[350,1000,650],   Soybean:[4000,4600,4300] },
  5:  { Onion:[700,1500,1100],  Tomato:[400,1200,750],   Soybean:[4100,4700,4400] },
  6:  { Onion:[900,1700,1300],  Tomato:[500,1400,900],   Soybean:[4200,4800,4500] },
  7:  { Onion:[1000,2000,1500], Tomato:[800,4000,1500],  Soybean:[4300,5000,4650] },
  8:  { Onion:[1200,2500,1800], Tomato:[1000,5000,2000], Soybean:[4400,5200,4800] },
  9:  { Onion:[1500,3500,2200], Tomato:[700,3500,1500],  Soybean:[4400,5000,4700] },
  10: { Onion:[1400,3000,2000], Tomato:[600,2500,1200],  Soybean:[4200,4900,4600] },
  11: { Onion:[1000,2200,1500], Tomato:[500,1500,900],   Soybean:[4300,4900,4600] },
  12: { Onion:[800,1800,1200],  Tomato:[600,1600,1000],  Soybean:[4400,5000,4700] },
};

const HISTORICAL = {
  Onion: {
    labels: ['Apr 24','May 24','Jun 24','Jul 24','Aug 24','Sep 24','Oct 24','Nov 24','Dec 24','Jan 25','Feb 25','Mar 25'],
    values: [1076, 1300, 1700, 2400, 3329, 4700, 3141, 2800, 2645, 2200, 1800, 1400],
  },
  Tomato: {
    labels: ['Apr 24','May 24','Jun 24','Jul 24','Aug 24','Sep 24','Oct 24','Nov 24','Dec 24','Jan 25','Feb 25','Mar 25'],
    values: [800, 700, 900, 2000, 3000, 3526, 2333, 1500, 1200, 1100, 900, 700],
  },
  Soybean: {
    labels: ['Apr 24','May 24','Jun 24','Jul 24','Aug 24','Sep 24','Oct 24','Nov 24','Dec 24','Jan 25','Feb 25','Mar 25'],
    values: [4355, 4355, 4200, 4300, 4400, 4450, 4500, 4625, 4700, 4800, 4500, 4400],
  },
};

const CLIMATE_FACTOR = { normal:0.00, sunny:0.02, cold:0.08, rainy:0.12, drought:0.18 };
const CROP_CLIMATE_SENSITIVITY = {
  normal:  { Onion:1.00, Tomato:1.00, Soybean:1.00 },
  sunny:   { Onion:1.03, Tomato:1.04, Soybean:1.06 },
  cold:    { Onion:1.08, Tomato:1.07, Soybean:1.05 },
  rainy:   { Onion:1.08, Tomato:1.05, Soybean:0.94 },
  drought: { Onion:1.10, Tomato:1.08, Soybean:1.09 },
};
const REGION_FACTOR = {
  Onion:   {lasalgaon:1.00,pimpalgaon:0.96,pune:1.08,solapur:0.94,nagpur:1.05,mumbai:1.15,nashik:0.98,vashi:1.15},
  Tomato:  {pune:1.00,nashik:0.94,satara:0.97,mumbai:1.12,nagpur:1.04,aurangabad:0.98},
  Soybean: {latur:1.00,akola:0.97,amravati:0.99,nagpur:1.02,washim:0.96,hingoli:0.98},
};

function getRegionFactor(crop, location) {
  if (!location) return 1.0;
  const loc = location.toLowerCase();
  const mp  = REGION_FACTOR[crop] || {};
  for (const [key, val] of Object.entries(mp)) {
    if (loc.includes(key) || key.includes(loc.split(' ')[0])) return val;
  }
  return 1.0;
}

function seededRand(seed) {
  let s = Math.abs(seed % 2147483647) + 1;
  return () => { s = (s * 16807) % 2147483647; return (s - 1) / 2147483646; };
}

function realityCheck(crop, price, daysAhead) {
  const m = ((new Date().getMonth()) + Math.floor(daysAhead / 30)) % 12 + 1;
  const [low, high, avg] = BOUNDS[m][crop];
  const conf = daysAhead <= 7 ? 92 : daysAhead <= 30 ? 85 : daysAhead <= 60 ? 72 : 60;
  const unc  = Math.round(Math.min(25, 5 + (daysAhead / 90) * 20));
  let status, adjusted;
  if (price > high * 1.10)     { status = 'OPTIMISTIC';   adjusted = Math.round(price * 0.4 + high * 0.6); }
  else if (price < low * 0.90) { status = 'CONSERVATIVE'; adjusted = Math.round(price * 0.5 + low * 0.5); }
  else                          { status = 'REALISTIC';    adjusted = price; }
  return { status, realistic_low:low, realistic_high:high, realistic_avg:avg,
          adjusted, confidence:conf, uncertainty_pct:unc, forecast_month:m };
}

function offlineForecast(crop, location, climate, days) {
  const today = new Date();
  const month = today.getMonth() + 1;
  const [low, high, avg] = BOUNDS[month][crop];
  const cf_key = climate in CLIMATE_FACTOR ? climate : 'normal';
  const cf  = 1 + (CLIMATE_FACTOR[cf_key] || 0);
  const cs  = CROP_CLIMATE_SENSITIVITY[cf_key][crop];
  const rf  = getRegionFactor(crop, location);
  const tf  = cf * cs * rf;
  const base = HISTORICAL[crop].values.slice(-1)[0] * tf;
  const rand = seededRand(crop.charCodeAt(0) * 31 + month * 97 + days * 13 + Math.round(tf * 100));

  const target    = avg * tf;
  const driftRate = (target - base) / (days * 2.5);
  let lp = base, momentum = 0;
  const lstm = [];
  for (let i = 0; i < days; i++) {
    const seasonal = Math.sin((i / 28) * Math.PI * 2) * (high - low) * 0.07 * cf;
    const noise    = (rand() - 0.5) * (high - low) * 0.035;
    momentum       = 0.88 * momentum + 0.12 * (driftRate + seasonal + noise);
    lp = Math.max(low * 0.80, Math.min(high * 1.20, lp + momentum));
    lstm.push(Math.round(lp));
  }

  const win5 = [...HISTORICAL[crop].values.slice(-5).map(v => v * tf)];
  const AR   = [0.35, 0.25, 0.18, 0.12, 0.10];
  let ap = win5[win5.length - 1];
  const arima = [];
  for (let i = 0; i < days; i++) {
    let arPart = 0;
    for (let k = 0; k < Math.min(5, win5.length); k++) arPart += AR[k] * win5[win5.length - 1 - k];
    const ma = (rand() - 0.5) * (high - low) * 0.025;
    const mr = (avg * tf - ap) * 0.018;
    ap = Math.max(low * 0.80, Math.min(high * 1.20, arPart + ma + mr));
    win5.push(ap); if (win5.length > 5) win5.shift();
    arima.push(Math.round(ap));
  }

  const ensemble = lstm.map((l, i) => Math.round(0.70 * l + 0.30 * arima[i]));
  const dates = [];
  for (let i = 1; i <= days; i++) {
    const d = new Date(today); d.setDate(today.getDate() + i);
    dates.push(d.toLocaleDateString('en-IN', { day:'2-digit', month:'short', year:'numeric' }));
  }

  const peakIdx   = ensemble.indexOf(Math.max(...ensemble));
  const troughIdx = ensemble.indexOf(Math.min(...ensemble));
  const avgPrice  = Math.round(ensemble.reduce((a, b) => a + b, 0) / days);
  const changePct = +((ensemble[days-1] - ensemble[0]) / Math.max(ensemble[0], 1) * 100).toFixed(1);
  const trend     = changePct > 5 ? 'RISING' : changePct < -5 ? 'FALLING' : 'STABLE';
  const sentiment = trend === 'RISING' ? 'BULLISH' : trend === 'FALLING' ? 'BEARISH' : 'NEUTRAL';
  const current   = Math.round(ensemble[0] * rf);
  const peak      = ensemble[peakIdx];
  const rc        = realityCheck(crop, peak, peakIdx + 1);
  const cost      = COST[crop];
  const mspVal    = MSP[crop];

  return {
    crop, days, location, climate,
    market: MARKET_INFO[crop], mode: 'demo', metrics: {},
    forecast: { dates, ensemble, lstm, arima },
    historical: HISTORICAL[crop],
    summary: {
      current_price: current, avg_price: avgPrice,
      peak_price: peak, peak_date: dates[peakIdx], peak_day: peakIdx + 1,
      trough_price: ensemble[troughIdx], trough_date: dates[troughIdx], trough_day: troughIdx + 1,
      change_pct: changePct, trend, sentiment,
    },
    reality_check: rc,
    profit: {
      cost_per_q:  cost,
      profit_now:  Math.round(current - cost),
      profit_peak: Math.round(peak - cost),
      margin_now:  +((current - cost) / cost * 100).toFixed(1),
      margin_peak: +((peak - cost)    / cost * 100).toFixed(1),
      msp: mspVal ? {
        value: mspVal, above: current >= mspVal,
        note: current >= mspVal ? window.t('above_msp') : window.t('below_msp'),
      } : null,
    },
    region_factor: +rf.toFixed(2),
  };
}

// ════════════════════════════════════════════════════════════
//  BACKEND-AWARE FETCH
// ════════════════════════════════════════════════════════════

let _backendAlive = null;

async function checkBackendAlive() {
  if (_backendAlive !== null) return _backendAlive;
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 3000);
    const res = await fetch(`${API_BASE}/health`, { signal: ctrl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const data = await res.json();
    _backendAlive = true;
    console.log('[AgriPredict] Backend alive. Mode:', data.mode, '| Models loaded:', data.models_loaded);
    return true;
  } catch (e) {
    _backendAlive = false;
    console.warn('[AgriPredict] Backend not reachable:', e.message, '— using offline fallback.');
    return false;
  }
}

async function fetchPrediction(payload) {
  const alive = await checkBackendAlive();
  if (!alive) {
    console.log('[AgriPredict] Skipping backend fetch — using offline engine.');
    return offlineForecast(payload.crop, payload.location, payload.climate, payload.days);
  }

  try {
    const ctrl = new AbortController();
    const tm   = setTimeout(() => ctrl.abort(), 120000);
    console.log('[AgriPredict] Sending to backend:', payload);
    const res = await fetch(`${API_BASE}/predict`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload),
      signal: ctrl.signal,
    });
    clearTimeout(tm);
    if (!res.ok) {
      const errText = await res.text().catch(() => '');
      throw new Error(`HTTP ${res.status}: ${errText}`);
    }
    const data = await res.json();
    console.log('[AgriPredict] Backend response received. mode =', data.mode);
    return data;
  } catch (err) {
    console.error('[AgriPredict] Backend predict failed:', err.message);
    console.warn('[AgriPredict] Falling back to offline engine.');
    _backendAlive = null;
    return offlineForecast(payload.crop, payload.location, payload.climate, payload.days);
  }
}

async function fetchWatchlist() {
  try {
    const ctrl = new AbortController();
    setTimeout(() => ctrl.abort(), 5000);
    const res  = await fetch(`${API_BASE}/watchlist`, { signal: ctrl.signal });
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return await res.json();
  } catch (e) {
    console.warn('[AgriPredict] Watchlist fallback:', e.message);
    const today = new Date();
    const m     = today.getMonth() + 1;
    return ['Onion', 'Tomato', 'Soybean'].map(crop => {
      const [low, high, avg] = BOUNDS[m][crop];
      const rand  = seededRand(crop.charCodeAt(0) * 7 + today.getDate() * 3);
      const price = Math.round(avg + (rand() - 0.5) * (high - low) * 0.14);
      const change = +((rand() - 0.47) * 7).toFixed(1);
      return { crop, price, change, trend: change >= 0 ? 'up' : 'down', market: MARKET_INFO[crop] };
    });
  }
}

// ════════════════════════════════════════════════════════════
//  PDF REPORT DOWNLOAD
// ════════════════════════════════════════════════════════════

async function downloadReport(payload) {
  const btn = document.getElementById('downloadReportBtn');
  if (btn) { btn.classList.add('loading'); btn.disabled = true; }
  try {
    const ctrl = new AbortController();
    const tm   = setTimeout(() => ctrl.abort(), 20000);
    const res  = await fetch(`${API_BASE}/report`, {
      method:  'POST',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify(payload),
      signal:  ctrl.signal,
    });
    clearTimeout(tm);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    const blob = await res.blob();
    const url  = URL.createObjectURL(blob);
    const a    = document.createElement('a');
    a.href     = url;
    a.download = `AgriPredict_${payload.crop}_${new Date().toISOString().slice(0,10)}.pdf`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  } catch (e) {
    showPrintFallback(payload);
  } finally {
    if (btn) { btn.classList.remove('loading'); btn.disabled = false; }
  }
}

function showPrintFallback(payload) {
  const win = window.open('', '_blank', 'width=800,height=900');
  const d   = window._lastPredictionData;
  if (!d || !win) { alert('Please start the backend server for PDF download, or use Ctrl+P to print this page.'); return; }
  const s = d.summary, pf = d.profit, rc = d.reality_check, fc = d.forecast;

  const lang = window.AGRI_LANG || 'en';
  const reportLabels = {
    en: { title:'Farmer Report', crop:'Crop', market:'Market', location:'Location', date:'Date',
          priceSummary:'Price Summary', today:'Today Est.', peakPrice:'Peak Price', peakDay:'Peak Day',
          avgForecast:'Avg Forecast', trend:'Trend', pl:'Profit & Loss (per Quintal)',
          cultCost:'Cultivation Cost', profitToday:'Profit Today', profitPeak:'Profit at Peak',
          forecast:'Day-by-Day Forecast', day:'Day', note:'Always verify with your local mandi before final decisions.' },
    mr: { title:'शेतकरी अहवाल', crop:'पीक', market:'बाजार', location:'ठिकाण', date:'तारीख',
          priceSummary:'किंमत सारांश', today:'आजचा अंदाज', peakPrice:'शिखर किंमत', peakDay:'शिखर दिवस',
          avgForecast:'सरासरी अंदाज', trend:'ट्रेंड', pl:'नफा/तोटा (प्रति क्विंटल)',
          cultCost:'उत्पादन खर्च', profitToday:'आजचा नफा', profitPeak:'शिखरावर नफा',
          forecast:'दिवसवार अंदाज', day:'दिवस', note:'अंतिम निर्णयापूर्वी नेहमी तुमच्या स्थानिक मंडईशी तपासा.' },
    hi: { title:'किसान रिपोर्ट', crop:'फसल', market:'बाज़ार', location:'स्थान', date:'तारीख',
          priceSummary:'मूल्य सारांश', today:'आज का अनुमान', peakPrice:'शिखर मूल्य', peakDay:'शिखर दिन',
          avgForecast:'औसत अनुमान', trend:'ट्रेंड', pl:'लाभ/हानि (प्रति क्विंटल)',
          cultCost:'उत्पादन लागत', profitToday:'आज का लाभ', profitPeak:'शिखर पर लाभ',
          forecast:'दिन-दर-दिन अनुमान', day:'दिन', note:'अंतिम निर्णय से पहले हमेशा अपनी स्थानिक मंडी से जाँचें।' },
  };
  const L = reportLabels[lang] || reportLabels['en'];

  win.document.write(`<!DOCTYPE html><html lang="${lang}"><head>
    <meta charset="UTF-8"/>
    <title>AgriPredict — ${d.crop}</title>
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Noto+Sans+Devanagari:wght@400;700&display=swap"/>
    <style>
      body { font-family: 'Noto Sans Devanagari', Arial, sans-serif; color: #111; background: #fff; padding: 24px; }
      h1   { color: #16a870; border-bottom: 2px solid #16a870; padding-bottom: 8px; }
      h2   { color: #0a7048; margin-top: 20px; }
      table { width: 100%; border-collapse: collapse; margin: 8px 0 16px; }
      th,td { border: 1px solid #ccc; padding: 6px 10px; font-size: 12px; }
      th   { background: #e8f7f0; }
      .green { color: #16a870; } .red { color: #d63031; }
      @media print { body { padding: 0; } }
    </style>
  </head><body>
    <h1>AgriPredict.ai — ${L.title}</h1>
    <p><b>${L.crop}:</b> ${d.crop} &nbsp;|&nbsp; <b>${L.market}:</b> ${d.market} &nbsp;|&nbsp;
      <b>${L.location}:</b> ${d.location || '—'} &nbsp;|&nbsp; <b>${L.date}:</b> ${new Date().toLocaleDateString('en-IN')}</p>
    <h2>${L.priceSummary}</h2>
    <table>
      <tr><th>${L.today}</th><th>${L.peakPrice}</th><th>${L.peakDay}</th><th>${L.avgForecast}</th><th>${L.trend}</th></tr>
      <tr><td>₹${s.current_price.toLocaleString('en-IN')}</td>
          <td class="green"><b>₹${s.peak_price.toLocaleString('en-IN')}</b></td>
          <td>${L.day} ${s.peak_day} · ${s.peak_date}</td>
          <td>₹${s.avg_price.toLocaleString('en-IN')}</td>
          <td class="${s.trend==='RISING'?'green':'red'}">${s.trend} ${s.change_pct>0?'+':''}${s.change_pct}%</td>
      </tr>
    </table>
    <h2>${L.pl}</h2>
    <table>
      <tr><th>${L.cultCost}</th><th>${L.profitToday}</th><th>${L.profitPeak}</th></tr>
      <tr><td>₹${pf.cost_per_q.toLocaleString('en-IN')}</td>
          <td class="${pf.profit_now>=0?'green':'red'}">₹${pf.profit_now>0?'+':''}${pf.profit_now.toLocaleString('en-IN')} (${pf.margin_now}%)</td>
          <td class="${pf.profit_peak>=0?'green':'red'}">₹${pf.profit_peak>0?'+':''}${pf.profit_peak.toLocaleString('en-IN')} (${pf.margin_peak}%)</td>
      </tr>
    </table>
    <h2>${L.forecast}</h2>
    <table>
      <tr><th>${L.day}</th><th>Date</th><th>LSTM</th><th>ARIMA</th><th>Ensemble</th></tr>
      ${fc.dates.map((dt,i)=>`<tr><td>${i+1}</td><td>${dt}</td><td>${fc.lstm[i].toLocaleString('en-IN')}</td><td>${fc.arima[i].toLocaleString('en-IN')}</td><td><b>${fc.ensemble[i].toLocaleString('en-IN')}</b></td></tr>`).join('')}
    </table>
    <p style="font-size:10px;color:#666;margin-top:20px">
      Data: agmarknet.gov.in · NHRDF · CACP 2024-25 · BiLSTM+ARIMA Ensemble<br/>
      ${L.note}
    </p>
  </body></html>`);
  win.document.close();
  win.print();
}

// ════════════════════════════════════════════════════════════
//  INTERSECTION OBSERVER — scroll reveal
// ════════════════════════════════════════════════════════════

function initReveal() {
  const obs = new IntersectionObserver(entries => {
    entries.forEach(e => {
      if (e.isIntersecting) { e.target.classList.add('visible'); obs.unobserve(e.target); }
    });
  }, { rootMargin: '0px 0px -60px 0px', threshold: 0.1 });
  document.querySelectorAll('.reveal').forEach(el => obs.observe(el));
}

// ════════════════════════════════════════════════════════════
//  INIT
// ════════════════════════════════════════════════════════════

function init() {
  initReveal();
  // Apply saved language on load for pages that include this script
  const saved = localStorage.getItem('agri_lang') || 'en';
  window.AGRI_LANG = saved;
  if (saved !== 'en') {
    // index.html has its own setLang call; other pages use this
    if (typeof window.setLang === 'function') window.setLang(saved);
  }
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}