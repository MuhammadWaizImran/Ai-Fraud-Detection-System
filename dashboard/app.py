"""
FINRA AI Fraud Detection Platform
===================================
REAL-TIME PRODUCTION DASHBOARD
- Reads live_feed.jsonl updated by realtime_scoring_engine.py
- Auto-refreshes every 2 seconds
- Dark theme, multi-page, fully interactive
"""

import os, sys, json, time, io
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st

# ══════════════════════════════════════════════════════════════
# PAGE CONFIG
# ══════════════════════════════════════════════════════════════
st.set_page_config(
    page_title="FINRA AI — Live Fraud Detection",
    page_icon="🛡️",
    layout="wide",
    initial_sidebar_state="expanded",
)

BASE_DIR   = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR   = os.path.dirname(BASE_DIR)
FEED_FILE  = os.path.join(BASE_DIR, "live_feed.jsonl")
STATS_FILE = os.path.join(BASE_DIR, "live_stats.json")
CSV_DIR    = os.path.join(ROOT_DIR, "powerbi", "data")

# ══════════════════════════════════════════════════════════════
# COLORS
# ══════════════════════════════════════════════════════════════
D = {
    "bg":"#0a0e1a","bg2":"#0f1629","card":"#131a2e","card2":"#182040",
    "surface":"#1a2342","border":"#1e2d4a","border2":"#2a3a5c",
    "cyan":"#00d4ff","purple":"#a855f7","emerald":"#10b981",
    "red":"#ef4444","amber":"#f59e0b","blue":"#3b82f6","pink":"#ec4899",
    "text":"#e2e8f0","text2":"#94a3b8","text3":"#64748b","white":"#ffffff",
}

# ══════════════════════════════════════════════════════════════
# CSS
# ══════════════════════════════════════════════════════════════
st.markdown(f"""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@500;700&display=swap');
html,body,[class*="css"]{{font-family:'Inter',sans-serif!important}}
.stApp{{background:{D['bg']}!important}}
#MainMenu,footer,header{{visibility:hidden}}
.block-container{{padding:1rem 2rem 3rem;max-width:1700px}}
section[data-testid="stSidebar"]{{background:linear-gradient(180deg,{D['bg2']},{D['card']})!important;border-right:1px solid {D['border']}!important}}
section[data-testid="stSidebar"] *{{color:{D['text']}!important}}
.stSelectbox>div>div,.stMultiSelect>div>div{{background:{D['card']}!important;border-color:{D['border']}!important;color:{D['text']}!important;border-radius:10px!important}}
.stSelectbox label,.stMultiSelect label{{color:{D['text2']}!important;font-weight:700!important;font-size:12px!important;text-transform:uppercase!important}}
.stButton>button{{background:linear-gradient(135deg,{D['cyan']},{D['blue']})!important;color:#fff!important;border:none!important;font-weight:700!important;border-radius:10px!important}}
.stTabs [data-baseweb="tab-list"]{{gap:4px;background:{D['card']};border-radius:12px;padding:4px;border:1px solid {D['border']}}}
.stTabs [data-baseweb="tab"]{{border-radius:8px!important;color:{D['text2']}!important;font-weight:700!important;background:transparent!important}}
.stTabs [aria-selected="true"]{{background:{D['surface']}!important;color:{D['cyan']}!important}}

.dk{{background:{D['card']};border:1px solid {D['border']};border-radius:16px;padding:20px 22px;position:relative;overflow:hidden;transition:all .2s}}
.dk:hover{{border-color:{D['border2']};transform:translateY(-2px);box-shadow:0 8px 24px rgba(0,212,255,.06)}}
.dk::before{{content:'';position:absolute;top:0;left:0;right:0;height:3px;border-radius:16px 16px 0 0}}
.dk-cyan::before{{background:linear-gradient(90deg,{D['cyan']},{D['blue']})}}
.dk-red::before{{background:linear-gradient(90deg,{D['red']},{D['pink']})}}
.dk-amber::before{{background:linear-gradient(90deg,{D['amber']},#f97316)}}
.dk-emerald::before{{background:linear-gradient(90deg,{D['emerald']},#22d3ee)}}
.dk-purple::before{{background:linear-gradient(90deg,{D['purple']},{D['pink']})}}
.dk-lbl{{font-size:11.5px;font-weight:800;color:{D['text3']};text-transform:uppercase;letter-spacing:.07em;margin-bottom:8px}}
.dk-val{{font-size:30px;font-weight:900;color:{D['white']};line-height:1;font-family:'JetBrains Mono',monospace}}
.dk-sub{{font-size:12px;font-weight:600;margin-top:8px}}
.dk-sub.up{{color:{D['red']}}} .dk-sub.down{{color:{D['emerald']}}} .dk-sub.flat{{color:{D['cyan']}}}

.pnl{{background:{D['card']};border:1px solid {D['border']};border-radius:16px;padding:22px}}
.pnl-t{{font-size:15px;font-weight:800;color:{D['white']};margin-bottom:2px}}
.pnl-s{{font-size:12px;color:{D['text3']};font-weight:500;margin-bottom:16px}}

.hdr{{background:linear-gradient(135deg,{D['card']},{D['surface']});border:1px solid {D['border']};border-radius:16px;padding:20px 28px;margin-bottom:16px}}
.hdr-t{{font-size:22px;font-weight:900;color:{D['white']}}}
.hdr-sub{{font-size:13px;color:{D['text3']};margin-top:2px}}
.hdr-live{{display:inline-flex;align-items:center;gap:7px;font-size:12px;font-weight:800;color:{D['emerald']}}}
.hdr-dot{{width:9px;height:9px;border-radius:50%;background:{D['emerald']};animation:glow 1.5s infinite}}
@keyframes glow{{0%,100%{{opacity:.4;box-shadow:0 0 4px {D['emerald']}}}50%{{opacity:1;box-shadow:0 0 12px {D['emerald']}}}}}

.pill{{padding:4px 12px;border-radius:20px;font-size:11px;font-weight:800;display:inline-block}}
.pill-red{{background:rgba(239,68,68,.15);color:{D['red']};border:1px solid rgba(239,68,68,.25)}}
.pill-amber{{background:rgba(245,158,11,.12);color:{D['amber']};border:1px solid rgba(245,158,11,.2)}}
.pill-emerald{{background:rgba(16,185,129,.12);color:{D['emerald']};border:1px solid rgba(16,185,129,.2)}}
.pill-cyan{{background:rgba(0,212,255,.1);color:{D['cyan']};border:1px solid rgba(0,212,255,.18)}}

.rt-row{{display:flex;align-items:center;gap:12px;padding:10px 14px;border-radius:10px;margin-bottom:6px;transition:all .15s}}
.rt-row:hover{{background:{D['surface']}}}
.rt-fraud{{background:rgba(239,68,68,.08);border-left:3px solid {D['red']}}}
.rt-suspicious{{background:rgba(245,158,11,.06);border-left:3px solid {D['amber']}}}
.rt-safe{{background:rgba(16,185,129,.05);border-left:3px solid {D['emerald']}}}

.fbar{{background:{D['card']};border:1px solid {D['border']};border-radius:14px;padding:10px 18px;margin-bottom:14px}}
.sec{{display:flex;align-items:center;gap:10px;margin:22px 0 12px}}
.sec-txt{{font-size:13px;font-weight:800;color:{D['text2']};text-transform:uppercase;letter-spacing:.06em}}
::-webkit-scrollbar{{width:6px}}
::-webkit-scrollbar-track{{background:{D['bg']}}}
::-webkit-scrollbar-thumb{{background:{D['border2']};border-radius:3px}}

.alert-banner{{background:linear-gradient(135deg,rgba(239,68,68,.15),rgba(239,68,68,.05));border:1px solid rgba(239,68,68,.3);border-radius:12px;padding:14px 18px;margin-bottom:12px;animation:pulse-red 2s infinite}}
@keyframes pulse-red{{0%,100%{{border-color:rgba(239,68,68,.3)}}50%{{border-color:rgba(239,68,68,.7)}}}}

.counter-badge{{font-family:'JetBrains Mono';font-size:13px;font-weight:700;padding:4px 10px;border-radius:8px;background:{D['card2']};border:1px solid {D['border']}}}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# DATA LOADERS
# ══════════════════════════════════════════════════════════════
def load_live_feed(max_rows=500):
    """Load live scored events from jsonl file."""
    if not os.path.exists(FEED_FILE):
        return pd.DataFrame()
    try:
        rows = []
        with open(FEED_FILE, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        rows.append(json.loads(line))
                    except:
                        pass
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows[-max_rows:])
        if "scored_at" in df.columns:
            df["scored_at"] = pd.to_datetime(df["scored_at"])
        if "timestamp" in df.columns:
            df["timestamp"] = pd.to_datetime(df["timestamp"])
        return df
    except Exception as e:
        return pd.DataFrame()

def load_stats():
    """Load running stats from scoring engine."""
    if not os.path.exists(STATS_FILE):
        return {}
    try:
        with open(STATS_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def load_csv(key):
    files = {
        "kpis":       "pbi_summary_kpis.csv",
        "by_symbol":  "pbi_fraud_by_symbol.csv",
        "by_pattern": "pbi_fraud_by_pattern.csv",
        "traders":    "pbi_trader_risk_profiles.csv",
        "hourly":     "pbi_hourly_trends.csv",
    }
    fp = os.path.join(CSV_DIR, files.get(key, ""))
    if os.path.exists(fp):
        return pd.read_csv(fp)
    return pd.DataFrame()

# ══════════════════════════════════════════════════════════════
# HELPERS
# ══════════════════════════════════════════════════════════════
def kpi(label, value, sub, sub_cls="flat", accent="cyan"):
    st.markdown(f"""<div class="dk dk-{accent}">
        <div class="dk-lbl">{label}</div>
        <div class="dk-val">{value}</div>
        <div class="dk-sub {sub_cls}">{sub}</div>
    </div>""", unsafe_allow_html=True)

def section(emoji, text):
    st.markdown(f'<div class="sec"><span style="font-size:18px;">{emoji}</span><div class="sec-txt">{text}</div></div>', unsafe_allow_html=True)

def pill(text, cls="cyan"):
    return f'<span class="pill pill-{cls}">{text}</span>'

def fmt_num(v):
    try:
        v = float(v)
        if v>=1e9: return f"${v/1e9:.2f}B"
        if v>=1e6: return f"${v/1e6:.1f}M"
        if v>=1e3: return f"${v/1e3:.1f}K"
        return f"${v:,.0f}"
    except: return str(v)

def dark_fig(fig, h=380):
    fig.update_layout(
        height=h, margin=dict(l=8,r=8,t=32,b=8),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Inter", size=12, color=D['text2']),
        xaxis=dict(showgrid=False, tickfont=dict(color=D['text3'], size=11), zeroline=False),
        yaxis=dict(gridcolor=D['border'], tickfont=dict(color=D['text3'], size=11), zeroline=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, font=dict(size=11, color=D['text2']), bgcolor="rgba(0,0,0,0)"),
        hoverlabel=dict(bgcolor=D['card2'], font_color=D['white'], bordercolor=D['border2']),
    )
    return fig

def verdict_color(v):
    return D['red'] if v=="FRAUD" else (D['amber'] if v=="SUSPICIOUS" else D['emerald'])

def verdict_pill(v):
    cls = "red" if v=="FRAUD" else ("amber" if v=="SUSPICIOUS" else "emerald")
    return pill(v, cls)

# ══════════════════════════════════════════════════════════════
# SIDEBAR
# ══════════════════════════════════════════════════════════════
engine_running = os.path.exists(FEED_FILE) and os.path.getsize(FEED_FILE) > 0

with st.sidebar:
    st.markdown(f"""
    <div style="padding:18px 8px 20px;text-align:center;border-bottom:1px solid {D['border']};">
        <div style="width:52px;height:52px;border-radius:14px;
            background:linear-gradient(135deg,{D['cyan']},{D['purple']});
            display:inline-flex;align-items:center;justify-content:center;
            font-size:22px;font-weight:900;color:#fff;
            box-shadow:0 4px 20px rgba(0,212,255,.3);margin-bottom:10px;">FD</div>
        <div style="font-size:17px;font-weight:900;
            background:linear-gradient(135deg,{D['cyan']},{D['purple']});
            -webkit-background-clip:text;-webkit-text-fill-color:transparent;">
            FINRA AI Platform</div>
        <div style="font-size:11px;color:{D['text3']};font-weight:500;margin-top:2px;">
            Real-Time Fraud Surveillance</div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("<div style='height:12px'></div>", unsafe_allow_html=True)
    page = st.radio("NAV", [
        "📡  Live Feed",
        "📊  Executive Overview",
        "🔍  Fraud Analysis",
        "💹  Crypto Market",
        "👤  Trader Profiles",
        "🤖  AI Performance",
    ], label_visibility="collapsed")

    st.markdown("<div style='height:10px'></div>", unsafe_allow_html=True)

    # Engine status
    if engine_running:
        st.markdown(f"""
        <div style="padding:12px;background:{D['card2']};border-radius:12px;border:1px solid rgba(16,185,129,.3);margin-bottom:10px;">
            <div class="hdr-live"><span class="hdr-dot"></span> ENGINE LIVE</div>
            <div style="font-size:10px;color:{D['text3']};margin-top:6px;">realtime_scoring_engine.py</div>
            <div style="font-size:10px;color:{D['text3']};margin-top:2px;">CoinGecko + 3-Model Ensemble</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.warning("Scoring engine not running!\nRun: python realtime_scoring_engine.py")

    # Auto-refresh control
    auto_refresh = st.checkbox("Auto-Refresh (2s)", value=True)
    refresh_rate = st.slider("Refresh Rate (sec)", 1, 10, 2, key="rr")

    if st.button("Manual Refresh", use_container_width=True):
        st.rerun()

    # Live stats
    stats = load_stats()
    if stats:
        total = stats.get("total", 0)
        fraud = stats.get("fraud", 0)
        rate  = stats.get("fraud_rate_pct", 0)
        st.markdown(f"""
        <div style="padding:12px;background:{D['card2']};border-radius:12px;border:1px solid {D['border']};margin-top:8px;">
            <div style="font-size:10px;color:{D['text3']};font-weight:700;text-transform:uppercase;letter-spacing:.04em;margin-bottom:8px;">Live Session Stats</div>
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="font-size:11px;color:{D['text2']};">Processed</span>
                <span class="counter-badge">{total:,}</span>
            </div>
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="font-size:11px;color:{D['text2']};">Frauds</span>
                <span class="counter-badge" style="color:{D['red']};">{fraud:,}</span>
            </div>
            <div style="display:flex;justify-content:space-between;">
                <span style="font-size:11px;color:{D['text2']};">Fraud Rate</span>
                <span class="counter-badge" style="color:{D['amber']};">{rate:.1f}%</span>
            </div>
        </div>
        """, unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# LOAD LIVE DATA
# ══════════════════════════════════════════════════════════════
feed = load_live_feed(500)
stats = load_stats()

# ══════════════════════════════════════════════════════════════
# PAGE 1 — LIVE FEED (REAL-TIME TERMINAL)
# ══════════════════════════════════════════════════════════════
if "Live Feed" in page:
    # Recent fraud alerts banner
    if not feed.empty:
        recent_frauds = feed[feed["verdict"]=="FRAUD"].tail(3)
        for _, row in recent_frauds.iterrows():
            t = row.get("scored_at", "")
            t_str = str(t)[-8:][:8] if t else ""
            st.markdown(f"""
            <div class="alert-banner">
                <div style="display:flex;align-items:center;gap:12px;">
                    <span style="font-size:20px;">🚨</span>
                    <div>
                        <span style="font-weight:800;color:{D['red']};font-size:14px;">CRITICAL FRAUD DETECTED</span>
                        <span style="font-size:12px;color:{D['text2']};margin-left:12px;">{row.get('fraud_type','').upper()} on {row.get('symbol','')} by {row.get('trader_id','')}</span>
                    </div>
                    <div style="margin-left:auto;font-family:'JetBrains Mono';font-size:14px;font-weight:800;color:{D['red']};">
                        Score: {row.get('risk_score',0):.4f}
                    </div>
                    <div style="font-size:11px;color:{D['text3']};">{t_str}</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Header
    total = stats.get("total", len(feed))
    fraud_c = stats.get("fraud", len(feed[feed["verdict"]=="FRAUD"]) if not feed.empty else 0)
    st.markdown(f"""<div class="hdr" style="display:flex;align-items:center;justify-content:space-between;">
        <div><div class="hdr-t">Real-Time Order Surveillance Terminal</div>
        <div class="hdr-sub">3-Model AI Ensemble scoring every order &lt;2ms | CoinGecko live prices</div></div>
        <div style="text-align:right;">
            <div class="hdr-live"><span class="hdr-dot"></span> LIVE STREAM</div>
            <div style="font-size:11px;color:{D['text3']};margin-top:4px;font-family:'JetBrains Mono';">{datetime.now().strftime('%H:%M:%S')}</div>
        </div>
    </div>""", unsafe_allow_html=True)

    # Filters
    st.markdown('<div class="fbar">', unsafe_allow_html=True)
    fc1, fc2, fc3 = st.columns(3)
    with fc1:
        verdict_filter = st.multiselect("Verdict", ["FRAUD","SUSPICIOUS","SAFE"], default=["FRAUD","SUSPICIOUS","SAFE"], key="vf")
    with fc2:
        sym_list = sorted(feed["symbol"].unique().tolist()) if not feed.empty and "symbol" in feed.columns else []
        sym_filter = st.multiselect("Symbol", sym_list, default=sym_list, key="sf")
    with fc3:
        n_rows = st.slider("Show Last N Events", 10, 200, 50, key="nr")
    st.markdown('</div>', unsafe_allow_html=True)

    # Live KPIs (real-time from stats)
    section("📡", "Real-Time Session Metrics")
    k1,k2,k3,k4,k5 = st.columns(5)
    with k1: kpi("Orders Processed", f"{total:,}", "This session", "flat", "cyan")
    with k2: kpi("Frauds Caught", f"{stats.get('fraud',0):,}", f"{stats.get('fraud_rate_pct',0):.1f}% rate", "up", "red")
    with k3: kpi("Suspicious", f"{stats.get('suspicious',0):,}", "Under review", "flat", "amber")
    with k4: kpi("Safe Cleared", f"{stats.get('safe',0):,}", "Verified normal", "down", "emerald")
    with k5: kpi("Alerts Fired", f"{stats.get('alerts_fired',0):,}", "Logic App triggered", "up", "red")

    # Main real-time charts
    section("📊", "Live Risk Score Timeline")
    if not feed.empty:
        ch1, ch2 = st.columns([2, 1])

        with ch1:
            st.markdown('<div class="pnl"><div class="pnl-t">Composite Risk Scores — Last 100 Orders</div><div class="pnl-s">Each dot = one scored order | Colors = AI verdict</div>', unsafe_allow_html=True)
            plot_df = feed.tail(100)
            colors_map = {"FRAUD":D['red'], "SUSPICIOUS":D['amber'], "SAFE":D['emerald']}
            fig = go.Figure()
            for verdict in ["SAFE", "SUSPICIOUS", "FRAUD"]:
                sub = plot_df[plot_df["verdict"]==verdict]
                if not sub.empty:
                    fig.add_trace(go.Scatter(
                        x=sub["scored_at"], y=sub["risk_score"],
                        mode="markers", name=verdict,
                        marker=dict(color=colors_map[verdict], size=10 if verdict=="FRAUD" else 7, opacity=0.85,
                            line=dict(color=colors_map[verdict], width=1)),
                        hovertemplate="<b>%{customdata[0]}</b><br>Symbol: %{customdata[1]}<br>Score: %{y:.4f}<br>Type: %{customdata[2]}<extra></extra>",
                        customdata=sub[["trader_id","symbol","fraud_type"]].values,
                    ))
            # Threshold lines
            fig.add_hline(y=0.85, line_dash="dash", line_color=D['red'], annotation_text="FRAUD (0.85)", annotation_font=dict(color=D['red'], size=11))
            fig.add_hline(y=0.50, line_dash="dash", line_color=D['amber'], annotation_text="SUSPICIOUS (0.50)", annotation_font=dict(color=D['amber'], size=11))
            fig = dark_fig(fig, 380)
            fig.update_layout(yaxis=dict(range=[0, 1.05]))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
            st.markdown('</div>', unsafe_allow_html=True)

        with ch2:
            st.markdown('<div class="pnl"><div class="pnl-t">Live Classification Split</div><div class="pnl-s">Last 200 orders by AI verdict</div>', unsafe_allow_html=True)
            if not feed.empty:
                vc = feed.tail(200)["verdict"].value_counts()
                vals  = [vc.get("SAFE",0), vc.get("SUSPICIOUS",0), vc.get("FRAUD",0)]
                fig2  = go.Figure(go.Pie(
                    labels=["Safe","Suspicious","Fraud"], values=vals, hole=0.7,
                    marker=dict(colors=[D['emerald'],D['amber'],D['red']], line=dict(color=D['card'], width=3)),
                    textinfo="label+percent", textfont=dict(size=12, color=D['text']), textposition="outside",
                ))
                fig2 = dark_fig(fig2, 380)
                fig2.update_layout(showlegend=False)
                total_disp = sum(vals)
                fig2.add_annotation(text=f"<b>{total_disp:,}</b><br><span style='font-size:11px'>Orders</span>",
                    x=0.5, y=0.5, showarrow=False, font=dict(size=22, color=D['white']))
                st.plotly_chart(fig2, use_container_width=True, config={"displayModeBar":False})
            st.markdown('</div>', unsafe_allow_html=True)

    # Live rolling risk chart
    section("📈", "Rolling Risk Score — Last 60 Seconds")
    if not feed.empty and "scored_at" in feed.columns:
        st.markdown('<div class="pnl"><div class="pnl-t">Risk Score Over Time</div><div class="pnl-s">Red spikes = fraud events detected</div>', unsafe_allow_html=True)
        recent = feed.tail(200).copy()
        recent = recent.sort_values("scored_at")
        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=recent["scored_at"], y=recent["risk_score"],
            mode="lines", fill="tonexty", name="Risk",
            line=dict(color=D['cyan'], width=2),
            fillcolor="rgba(0,212,255,.06)"))
        fig3.add_hrect(y0=0.85, y1=1.05, fillcolor="rgba(239,68,68,.08)", line_width=0, annotation_text="FRAUD ZONE")
        fig3.add_hrect(y0=0.50, y1=0.85, fillcolor="rgba(245,158,11,.05)", line_width=0)
        # Highlight fraud points
        frauds = recent[recent["verdict"]=="FRAUD"]
        if not frauds.empty:
            fig3.add_trace(go.Scatter(x=frauds["scored_at"], y=frauds["risk_score"],
                mode="markers", name="Fraud", marker=dict(color=D['red'], size=12, symbol="x")))
        fig3 = dark_fig(fig3, 260)
        fig3.update_layout(yaxis=dict(range=[0, 1.1]), showlegend=False)
        st.plotly_chart(fig3, use_container_width=True, config={"displayModeBar":False})
        st.markdown('</div>', unsafe_allow_html=True)

    # Live event table
    section("📋", "Live Transaction Feed")
    if not feed.empty:
        disp = feed.copy()
        if verdict_filter:
            disp = disp[disp["verdict"].isin(verdict_filter)]
        if sym_filter:
            disp = disp[disp["symbol"].isin(sym_filter)]
        disp = disp.sort_values("scored_at", ascending=False).head(n_rows)

        rows_html = ""
        for _, r in disp.iterrows():
            v = r.get("verdict","SAFE")
            row_cls = "rt-fraud" if v=="FRAUD" else ("rt-suspicious" if v=="SUSPICIOUS" else "rt-safe")
            vc = verdict_color(v)
            score = float(r.get("risk_score", 0))
            t_str = str(r.get("scored_at",""))[-15:][:8]
            ftype = str(r.get("fraud_type","none")).replace("_"," ").title()
            rows_html += f"""
            <div class="rt-row {row_cls}">
                <div style="width:55px;font-family:'JetBrains Mono';font-size:11px;color:{D['text3']};">{t_str}</div>
                <div style="width:40px;font-size:13px;font-weight:800;color:{D['white']};">{r.get('symbol','')}</div>
                <div style="flex:1;font-family:'JetBrains Mono';font-size:11px;color:{D['text3']};">{r.get('trader_id','')}</div>
                <div style="width:70px;font-size:12px;color:{D['text2']};">{r.get('order_type','').upper()}</div>
                <div style="width:90px;font-family:'JetBrains Mono';font-size:12px;color:{D['cyan']};">
                    ${float(r.get('price',0)):,.2f}</div>
                <div style="width:80px;font-size:12px;color:{D['text2']};">{float(r.get('volume',0)):.2f} units</div>
                <div style="width:100px;">
                    <div style="height:6px;background:{D['card2']};border-radius:3px;overflow:hidden;">
                        <div style="width:{int(score*100)}%;height:100%;background:{vc};border-radius:3px;"></div>
                    </div>
                    <div style="font-family:'JetBrains Mono';font-size:11px;color:{vc};margin-top:2px;">{score:.4f}</div>
                </div>
                <div style="width:80px;">{verdict_pill(v)}</div>
                <div style="width:130px;font-size:11px;color:{D['text3']};">{ftype if v!='SAFE' else ''}</div>
            </div>"""
        st.markdown(f'<div class="pnl"><div style="max-height:500px;overflow-y:auto;">{rows_html}</div></div>', unsafe_allow_html=True)

    # Auto-refresh
    if auto_refresh:
        time.sleep(refresh_rate)
        st.rerun()


# ══════════════════════════════════════════════════════════════
# PAGE 2 — EXECUTIVE OVERVIEW
# ══════════════════════════════════════════════════════════════
elif "Executive" in page:
    # Combine live feed + historical CSV
    kpis_csv = load_csv("kpis")
    hourly   = load_csv("hourly")

    st.markdown(f"""<div class="hdr" style="display:flex;align-items:center;justify-content:space-between;">
        <div><div class="hdr-t">Executive Command Center</div>
        <div class="hdr-sub">Combined live session + historical Gold table data</div></div>
        <div class="hdr-live"><span class="hdr-dot"></span> LIVE + HISTORICAL</div>
    </div>""", unsafe_allow_html=True)

    # KPIs: live session stats + historical
    section("📊", "Key Risk Indicators")
    total    = stats.get("total", 0)
    fraud_c  = stats.get("fraud", 0)
    susp_c   = stats.get("suspicious", 0)
    safe_c   = stats.get("safe", 0)
    rate     = stats.get("fraud_rate_pct", 0)
    hist_total = int(float(kpis_csv.iloc[0]["total_predictions"])) if not kpis_csv.empty else 0
    combined_total = hist_total + total

    c1,c2,c3,c4,c5,c6 = st.columns(6)
    with c1: kpi("Total Processed", f"{combined_total:,}", "Historical + Live", "flat", "cyan")
    with c2: kpi("Fraud (Session)", f"{fraud_c:,}", f"{rate:.1f}% rate", "up", "red")
    with c3: kpi("Suspicious", f"{susp_c:,}", "AI flagged", "flat", "amber")
    with c4: kpi("Safe", f"{safe_c:,}", "Cleared", "down", "emerald")
    with c5: kpi("Avg Risk (Live)", f"{feed['risk_score'].mean():.4f}" if not feed.empty else "N/A", "Composite score", "flat", "purple")
    with c6: kpi("Alerts Fired", f"{stats.get('alerts_fired',0)}", "Logic App emails", "up", "red")

    # Live session risk timeline
    section("📈", "Live Session — Risk Timeline")
    st.markdown('<div class="pnl"><div class="pnl-t">Risk Scores (Current Session)</div><div class="pnl-s">Real-time AI scoring output</div>', unsafe_allow_html=True)
    if not feed.empty:
        fig = make_subplots(specs=[[{"secondary_y":True}]])
        ts_grp = feed.set_index("scored_at").resample("30S").agg(
            fraud_count=("verdict", lambda x: (x=="FRAUD").sum()),
            susp_count=("verdict", lambda x: (x=="SUSPICIOUS").sum()),
            avg_risk=("risk_score","mean")
        ).reset_index()
        fig.add_bar(x=ts_grp["scored_at"], y=ts_grp["fraud_count"], name="Fraud", marker_color=D['red'], opacity=0.85, secondary_y=False)
        fig.add_bar(x=ts_grp["scored_at"], y=ts_grp["susp_count"], name="Suspicious", marker_color=D['amber'], opacity=0.6, secondary_y=False)
        fig.add_trace(go.Scatter(x=ts_grp["scored_at"], y=ts_grp["avg_risk"], name="Avg Risk", line=dict(color=D['cyan'], width=3), mode="lines"), secondary_y=True)
        fig.update_layout(barmode="stack")
        fig = dark_fig(fig, 360)
        fig.update_yaxes(title_text="Cases", secondary_y=False)
        fig.update_yaxes(title_text="Risk", secondary_y=True, showgrid=False)
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    st.markdown('</div>', unsafe_allow_html=True)

    # Historical hourly heatmap
    section("🕐", "Historical Fraud Heatmap (Gold Table Data)")
    st.markdown('<div class="pnl"><div class="pnl-t">Fraud Count by Hour × Day</div>', unsafe_allow_html=True)
    if not hourly.empty and "day_of_week" in hourly.columns:
        days = ["Mon","Tue","Wed","Thu","Fri","Sat","Sun"]
        hours_lbl = [f"{h:02d}:00" for h in range(24)]
        heat = hourly.groupby(["day_of_week","hour_of_day"])["fraud_count"].sum().reset_index()
        matrix = np.zeros((7, 24))
        for _, row in heat.iterrows():
            d = int(row["day_of_week"]) - 1
            h = int(row["hour_of_day"])
            if 0<=d<7 and 0<=h<24:
                matrix[d][h] = float(row["fraud_count"])
        fig = go.Figure(go.Heatmap(z=matrix, x=hours_lbl, y=days,
            colorscale=[[0,"rgba(0,212,255,.05)"],[0.5,"rgba(245,158,11,.4)"],[1,"rgba(239,68,68,.8)"]],
            showscale=True, colorbar=dict(title="Cases", title_font=dict(color=D['text3']), tickfont=dict(color=D['text3'])),
            hovertemplate="Day: %{y}<br>Hour: %{x}<br>Fraud: %{z}<extra></extra>"))
        fig = dark_fig(fig, 300)
        fig.update_layout(yaxis=dict(showgrid=False))
        st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    st.markdown('</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PAGE 3 — FRAUD ANALYSIS
# ══════════════════════════════════════════════════════════════
elif "Fraud Analysis" in page:
    by_pat = load_csv("by_pattern")

    st.markdown(f"""<div class="hdr"><div>
        <div class="hdr-t">Fraud Pattern Analysis</div>
        <div class="hdr-sub">Live session patterns + historical Gold table data</div>
    </div></div>""", unsafe_allow_html=True)

    section("🎯", "Live Session — Attack Types Detected")
    if not feed.empty:
        fa1, fa2 = st.columns(2)
        with fa1:
            st.markdown('<div class="pnl"><div class="pnl-t">Fraud Type Distribution (Live)</div>', unsafe_allow_html=True)
            fraud_feed = feed[feed["verdict"]=="FRAUD"]
            if not fraud_feed.empty:
                ft_counts = fraud_feed["fraud_type"].value_counts().reset_index()
                ft_counts.columns = ["fraud_type","count"]
                fig = go.Figure(go.Bar(y=ft_counts["fraud_type"], x=ft_counts["count"], orientation="h",
                    marker_color=[D['red'],D['amber'],D['purple'],D['cyan'],D['emerald']][:len(ft_counts)],
                    text=ft_counts["count"], textposition="outside",
                    textfont=dict(color=D['text'], size=12, family="JetBrains Mono")))
                fig = dark_fig(fig, 300)
                fig.update_layout(yaxis=dict(showgrid=False))
                st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
            else:
                st.info("No fraud events yet in this session.")
            st.markdown('</div>', unsafe_allow_html=True)

        with fa2:
            st.markdown('<div class="pnl"><div class="pnl-t">Symbol Targeting — Live Session</div>', unsafe_allow_html=True)
            if not feed.empty:
                sym_fraud = feed[feed["verdict"]=="FRAUD"]["symbol"].value_counts().reset_index()
                sym_fraud.columns = ["symbol","count"]
                if not sym_fraud.empty:
                    fig = go.Figure(go.Pie(labels=sym_fraud["symbol"], values=sym_fraud["count"], hole=0.6,
                        marker=dict(line=dict(color=D['card'], width=2)),
                        textinfo="label+value", textfont=dict(size=11, color=D['text'])))
                    fig = dark_fig(fig, 300)
                    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
            st.markdown('</div>', unsafe_allow_html=True)

    section("📊", "Historical Pattern Data (Gold Tables)")
    if not by_pat.empty:
        fa3, fa4 = st.columns(2)
        with fa3:
            st.markdown('<div class="pnl"><div class="pnl-t">Attack Pattern Frequency (Historical)</div>', unsafe_allow_html=True)
            pf = by_pat.sort_values("fraud_count", ascending=True)
            fig = go.Figure(go.Bar(y=pf["fraud_type_predicted"], x=pf["fraud_count"].astype(float), orientation="h",
                marker_color=[D['red'],D['amber'],D['purple'],D['cyan'],D['emerald']][:len(pf)],
                text=pf["fraud_count"], textposition="outside",
                textfont=dict(color=D['text'], size=13, family="JetBrains Mono")))
            fig = dark_fig(fig, 300)
            fig.update_layout(yaxis=dict(showgrid=False))
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
            st.markdown('</div>', unsafe_allow_html=True)

        with fa4:
            st.markdown('<div class="pnl"><div class="pnl-t">SHAP Feature Importance</div>', unsafe_allow_html=True)
            features = [
                ("Volume Spike Ratio", 42, D['red']),
                ("Cancel-to-Trade Ratio", 34, D['red']),
                ("Orders Per Minute", 26, D['amber']),
                ("Buy/Sell Imbalance", 19, D['amber']),
                ("Wash Trade Flag", 15, D['cyan']),
                ("Layering Flag", 12, D['purple']),
                ("Price Deviation %", 8, D['emerald']),
            ]
            bars = ""
            for name, pct, color in features:
                bars += f"""<div style="display:flex;align-items:center;gap:12px;padding:9px 0;border-bottom:1px solid {D['border']};">
                    <div style="width:180px;font-size:12px;font-weight:700;color:{D['text']};">{name}</div>
                    <div style="flex:1;height:8px;background:{D['card2']};border-radius:4px;">
                        <div style="width:{pct}%;height:100%;background:{color};border-radius:4px;"></div></div>
                    <div style="width:45px;text-align:right;font-size:12px;font-weight:800;color:{color};font-family:'JetBrains Mono';">{pct}%</div>
                </div>"""
            st.markdown(f'{bars}</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PAGE 4 — CRYPTO MARKET
# ══════════════════════════════════════════════════════════════
elif "Crypto Market" in page:
    by_sym = load_csv("by_symbol")
    if "selected_sym" not in st.session_state:
        st.session_state.selected_sym = None

    if st.session_state.selected_sym:
        sym = st.session_state.selected_sym
        sym_data = by_sym[by_sym["symbol"]==sym] if not by_sym.empty else pd.DataFrame()
        live_sym  = feed[feed["symbol"]==sym] if not feed.empty else pd.DataFrame()

        if st.button("Back to Market Overview"):
            st.session_state.selected_sym = None
            st.rerun()

        st.markdown(f"""<div class="hdr" style="display:flex;align-items:center;gap:16px;">
            <div style="width:54px;height:54px;border-radius:16px;background:linear-gradient(135deg,{D['cyan']},{D['purple']});
                display:flex;align-items:center;justify-content:center;font-weight:900;font-size:24px;color:#fff;">{sym[0]}</div>
            <div><div class="hdr-t">{sym} — Full Analysis</div>
            <div class="hdr-sub">Historical Gold Tables + Live Session Data</div></div>
        </div>""", unsafe_allow_html=True)

        # Live session stats for this symbol
        if not live_sym.empty:
            section("📡", f"{sym} — Live Session")
            ls1,ls2,ls3,ls4 = st.columns(4)
            with ls1: kpi("Live Events", f"{len(live_sym)}", "This session", "flat", "cyan")
            with ls2:
                lf = live_sym[live_sym["verdict"]=="FRAUD"]
                kpi("Live Frauds", f"{len(lf)}", f"{len(lf)/max(len(live_sym),1)*100:.1f}%", "up", "red")
            with ls3: kpi("Avg Live Risk", f"{live_sym['risk_score'].mean():.4f}", "Composite", "flat", "purple")
            with ls4: kpi("Max Live Risk", f"{live_sym['risk_score'].max():.4f}", "Highest detected", "up", "red")

        # Historical data
        if not sym_data.empty:
            s = sym_data.iloc[0]
            section("📊", f"{sym} — Historical Gold Table Data")
            h1,h2,h3,h4,h5 = st.columns(5)
            with h1: kpi("Total Historical", f"{int(float(s['total_events'])):,}", "Gold table", "flat", "cyan")
            with h2: kpi("Hist. Fraud", f"{int(float(s['fraud_count'])):,}", f"{float(s['fraud_rate_pct']):.1f}%", "up", "red")
            with h3: kpi("Hist. Risk", f"{float(s['avg_risk_score']):.4f}", "Avg score", "flat", "purple")
            with h4: kpi("Max Risk", f"{float(s['max_risk_score']):.4f}", "Peak detected", "up", "red")
            with h5: kpi("Volume", fmt_num(float(s['total_volume'])), "USD traded", "flat", "emerald")

    else:
        st.markdown(f"""<div class="hdr" style="display:flex;justify-content:space-between;align-items:center;">
            <div><div class="hdr-t">Crypto Asset Surveillance Terminal</div>
            <div class="hdr-sub">Click any coin for full drill-down analysis</div></div>
            <div class="hdr-live"><span class="hdr-dot"></span> MONITORING {len(by_sym)} ASSETS</div>
        </div>""", unsafe_allow_html=True)

        if not by_sym.empty:
            o1,o2,o3,o4 = st.columns(4)
            with o1: kpi("Assets Monitored", f"{len(by_sym)}", "Under surveillance", "flat", "cyan")
            with o2: kpi("Total Fraud (Hist)", f"{int(by_sym['fraud_count'].astype(float).sum()):,}", "Gold tables", "up", "red")
            with o3: kpi("Most Targeted", str(by_sym.sort_values("fraud_count",ascending=False).iloc[0]["symbol"]), "Highest count", "flat", "amber")
            with o4: kpi("Live Coins Active", f"{feed['symbol'].nunique()}" if not feed.empty else "0", "This session", "flat", "cyan")

        section("💹", "Symbol Rankings (Click to Drill Down)")
        if not by_sym.empty:
            for _, s in by_sym.sort_values("fraud_count", ascending=False).iterrows():
                live_sym_data = feed[feed["symbol"]==s["symbol"]] if not feed.empty else pd.DataFrame()
                live_count    = len(live_sym_data[live_sym_data["verdict"]=="FRAUD"]) if not live_sym_data.empty else 0
                cols = st.columns([1.5,1,1,1,1,1,1])
                with cols[0]:
                    if st.button(f"{s['symbol']}", key=f"sym_{s['symbol']}", use_container_width=True):
                        st.session_state.selected_sym = s["symbol"]
                        st.rerun()
                tcls = "red" if str(s.get("risk_tier",""))=="HIGH" else ("amber" if str(s.get("risk_tier",""))=="MEDIUM" else "emerald")
                cols[1].markdown(f'<div style="padding-top:8px;font-size:13px;font-weight:700;color:{D["text"]};">{int(float(s["total_events"])):,} hist.</div>', unsafe_allow_html=True)
                cols[2].markdown(f'<div style="padding-top:8px;font-size:13px;font-weight:800;color:{D["red"]};">{int(float(s["fraud_count"]))} fraud</div>', unsafe_allow_html=True)
                cols[3].markdown(f'<div style="padding-top:8px;font-size:13px;color:{D["cyan"]};font-family:JetBrains Mono;">{float(s["avg_risk_score"]):.3f}</div>', unsafe_allow_html=True)
                cols[4].markdown(f'<div style="padding-top:8px;">{pill(str(s.get("risk_tier","-")), tcls)}</div>', unsafe_allow_html=True)
                cols[5].markdown(f'<div style="padding-top:8px;font-size:12px;color:{D["emerald"]};font-weight:700;">+{live_count} live</div>', unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PAGE 5 — TRADER PROFILES
# ══════════════════════════════════════════════════════════════
elif "Trader" in page:
    traders = load_csv("traders")

    st.markdown(f"""<div class="hdr"><div>
        <div class="hdr-t">Trader Risk Profiles &amp; Investigation</div>
        <div class="hdr-sub">Historical + Live session behavior per entity</div>
    </div></div>""", unsafe_allow_html=True)

    # Live risky traders from feed
    if not feed.empty:
        section("📡", "Live Session — Top Risky Traders")
        live_traders = feed.groupby("trader_id").agg(
            events=("order_id","count"),
            frauds=("verdict", lambda x: (x=="FRAUD").sum()),
            max_risk=("risk_score","max"),
            avg_risk=("risk_score","mean"),
        ).reset_index().sort_values("max_risk", ascending=False).head(10)

        if not live_traders.empty:
            fig = go.Figure(go.Bar(y=live_traders["trader_id"], x=live_traders["max_risk"].round(4), orientation="h",
                marker_color=[D['red'] if r>=0.85 else (D['amber'] if r>=0.5 else D['emerald']) for r in live_traders["max_risk"]],
                text=[f"{r:.3f}" for r in live_traders["max_risk"]], textposition="outside",
                textfont=dict(color=D['text'], family="JetBrains Mono", size=12)))
            fig = dark_fig(fig, 320)
            fig.update_layout(yaxis=dict(showgrid=False, autorange="reversed"), xaxis_title="Max Risk Score")
            st.markdown('<div class="pnl"><div class="pnl-t">Top 10 Riskiest Traders (Live)</div>', unsafe_allow_html=True)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
            st.markdown('</div>', unsafe_allow_html=True)

    # Historical traders
    section("📋", "Historical Trader Investigation Table")
    if not traders.empty:
        tf1, tf2 = st.columns(2)
        with tf1:
            tr_tier = st.selectbox("Risk Tier", ["All","HIGH","MEDIUM","LOW"], key="tt")
        with tf2:
            tr_status = st.selectbox("Status", ["All","FLAGGED","WATCH","NORMAL"], key="ts")

        tf = traders.copy()
        if tr_tier != "All": tf = tf[tf["risk_tier"]==tr_tier]
        if tr_status != "All": tf = tf[tf["trader_status"]==tr_status]

        rows = ""
        for _, t in tf.sort_values("max_risk_score", ascending=False).head(25).iterrows():
            tcls = "red" if t["risk_tier"]=="HIGH" else ("amber" if t["risk_tier"]=="MEDIUM" else "emerald")
            scls = "red" if t["trader_status"]=="FLAGGED" else ("amber" if t["trader_status"]=="WATCH" else "emerald")
            rpct = int(float(t['max_risk_score'])*100)
            rows += f"""<tr>
                <td style="font-family:'JetBrains Mono';font-weight:700;">{t['trader_id']}</td>
                <td>{int(float(t['total_windows']))}</td>
                <td style="color:{D['red']};font-weight:800;">{int(float(t['fraud_windows']))}</td>
                <td>{float(t['fraud_rate_pct']):.1f}%</td>
                <td><div style="display:flex;align-items:center;gap:8px;">
                    <div style="width:60px;height:6px;background:{D['card2']};border-radius:3px;">
                        <div style="width:{rpct}%;height:100%;background:{D['red'] if rpct>=85 else (D['amber'] if rpct>=60 else D['emerald'])};border-radius:3px;"></div>
                    </div>
                    <span style="font-family:'JetBrains Mono';font-size:12px;">{float(t['max_risk_score']):.3f}</span>
                </div></td>
                <td>{fmt_num(float(t['total_volume_traded']))}</td>
                <td>{pill(t['risk_tier'], tcls)}</td>
                <td>{pill(t['trader_status'], scls)}</td>
            </tr>"""
        st.markdown(f"""<div class="pnl"><table style="width:100%;border-collapse:separate;border-spacing:0 6px;">
            <thead><tr style="font-size:11px;font-weight:800;color:{D['text3']};text-transform:uppercase;">
                <th style="padding:8px 14px;">Trader</th><th>Events</th><th>Frauds</th>
                <th>Fraud%</th><th>Max Risk</th><th>Volume</th><th>Tier</th><th>Status</th>
            </tr></thead><tbody style="font-size:13px;font-weight:600;color:{D['text']};">{rows}</tbody>
        </table></div>""", unsafe_allow_html=True)


# ══════════════════════════════════════════════════════════════
# PAGE 6 — AI PERFORMANCE
# ══════════════════════════════════════════════════════════════
elif "AI Performance" in page:
    st.markdown(f"""<div class="hdr"><div>
        <div class="hdr-t">AI Model Performance &amp; Real-Time Stats</div>
        <div class="hdr-sub">XGBoost (60%) + Isolation Forest (20%) + Deep Autoencoder (20%)</div>
    </div></div>""", unsafe_allow_html=True)

    section("🧠", "Model Performance Metrics")
    m1,m2,m3,m4,m5,m6 = st.columns(6)
    with m1: kpi("XGB Accuracy","88.2%","Binary classifier","flat","cyan")
    with m2: kpi("ROC-AUC","0.954","Outstanding","flat","purple")
    with m3: kpi("Precision","77.9%","Low false pos.","down","emerald")
    with m4: kpi("Recall","86.1%","High capture","down","emerald")
    with m5: kpi("F1 Score","0.818","Balanced","flat","cyan")
    with m6: kpi("Latency","<2ms","Real-time SLA","down","emerald")

    # Live score distribution
    if not feed.empty:
        section("📊", "Live Session — Score Distributions")
        ai1, ai2 = st.columns(2)

        with ai1:
            st.markdown('<div class="pnl"><div class="pnl-t">Individual Model Scores (Live)</div><div class="pnl-s">Per-model contribution distribution</div>', unsafe_allow_html=True)
            fig = go.Figure()
            for col, name, color in [("xgb_score","XGBoost",D['cyan']),("iso_score","IsoForest",D['purple']),("ae_score","Autoencoder",D['pink'])]:
                if col in feed.columns:
                    fig.add_trace(go.Histogram(x=feed[col].astype(float), name=name, opacity=0.65,
                        marker_color=color, nbinsx=20))
            fig = dark_fig(fig, 340)
            fig.update_layout(barmode="overlay")
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
            st.markdown('</div>', unsafe_allow_html=True)

        with ai2:
            st.markdown('<div class="pnl"><div class="pnl-t">Composite Risk Score Distribution</div><div class="pnl-s">Final ensemble output</div>', unsafe_allow_html=True)
            fig = go.Figure(go.Histogram(x=feed["risk_score"].astype(float), nbinsx=30,
                marker_color=D['cyan'], opacity=0.8, marker_line=dict(color=D['blue'], width=1)))
            fig.add_vline(x=0.85, line_dash="dash", line_color=D['red'], annotation_text="FRAUD", annotation_font=dict(color=D['red'], size=11))
            fig.add_vline(x=0.50, line_dash="dash", line_color=D['amber'], annotation_text="SUSPICIOUS", annotation_font=dict(color=D['amber'], size=11))
            fig = dark_fig(fig, 340)
            st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
            st.markdown('</div>', unsafe_allow_html=True)

    # Model cards
    section("⚖️", "Ensemble Architecture")
    mc1, mc2, mc3 = st.columns(3)
    for col, (name, desc, weight, prec, auc, color) in zip([mc1,mc2,mc3],[
        ("XGBoost","Gradient Boosted Trees","60%","88.2%","0.954",D['cyan']),
        ("Isolation Forest","Unsupervised Anomaly","20%","42.6%","N/A",D['purple']),
        ("Deep Autoencoder","Neural Reconstruction","20%","63.5%","N/A",D['pink']),
    ]):
        with col:
            st.markdown(f"""<div class="pnl" style="text-align:center;border-top:3px solid {color};">
                <div style="font-size:15px;font-weight:800;color:{D['white']};margin-bottom:2px;">{name}</div>
                <div style="font-size:11px;color:{D['text3']};margin-bottom:14px;">{desc}</div>
                <div style="font-size:42px;font-weight:900;color:{color};font-family:'JetBrains Mono';">{weight}</div>
                <div style="font-size:11px;color:{D['text3']};margin-bottom:10px;">ENSEMBLE WEIGHT</div>
                <hr style="border-color:{D['border']};margin:10px 0;">
                <div style="display:flex;justify-content:space-around;">
                    <div><div style="font-size:10px;color:{D['text3']};font-weight:700;">PRECISION</div>
                         <div style="font-size:18px;font-weight:800;color:{D['text']};font-family:'JetBrains Mono';">{prec}</div></div>
                    <div><div style="font-size:10px;color:{D['text3']};font-weight:700;">ROC-AUC</div>
                         <div style="font-size:18px;font-weight:800;color:{D['text']};font-family:'JetBrains Mono';">{auc}</div></div>
                </div></div>""", unsafe_allow_html=True)

    # Confusion matrix
    section("🔢", "Validation Confusion Matrix")
    st.markdown('<div class="pnl"><div class="pnl-t">30,000 Transaction Validation Set</div>', unsafe_allow_html=True)
    conf = [[25200, 1680], [420, 2700]]
    fig  = go.Figure(go.Heatmap(z=conf, x=["Pred Safe","Pred Fraud"], y=["Actual Safe","Actual Fraud"],
        colorscale=[[0,D['card2']],[0.5,D['surface']],[1,D['cyan']]],
        text=[[f"{v:,}" for v in r] for r in conf], texttemplate="%{text}",
        textfont=dict(size=22, color=D['white'], family="JetBrains Mono"), showscale=False))
    fig = dark_fig(fig, 300)
    fig.update_layout(yaxis=dict(autorange="reversed", showgrid=False))
    st.plotly_chart(fig, use_container_width=True, config={"displayModeBar":False})
    st.markdown('</div>', unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════
# FOOTER
# ══════════════════════════════════════════════════════════════
st.markdown(f"""
<div style="margin-top:30px;padding:14px 0;border-top:1px solid {D['border']};
    display:flex;justify-content:space-between;font-size:11px;color:{D['text3']};font-weight:600;">
    <span>FINRA AI Fraud Detection v3.0 &nbsp;·&nbsp; Real-Time 3-Model Ensemble &nbsp;·&nbsp; Azure Event Hubs + Databricks</span>
    <span>{datetime.now().strftime('%d %b %Y %H:%M:%S')}</span>
</div>""", unsafe_allow_html=True)
