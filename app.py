import streamlit as st
import sqlite3
import pandas as pd
import numpy as np
import pickle
import plotly.express as px
import plotly.graph_objects as go
import io
import os

# Optional ReportLab PDF Import
try:
    from reportlab.lib.pagesizes import letter
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

# -------------------------------------------------------------
# PAGE CONFIGURATION
# -------------------------------------------------------------
st.set_page_config(
    page_title="CricketMatrix360 | Advanced Cricket Analytics",
    page_icon="🏏",
    layout="wide",
    initial_sidebar_state="expanded"
)

# -------------------------------------------------------------
# STRICT LIGHT THEME OVERRIDE & VISIBILITY CSS
# -------------------------------------------------------------
st.markdown("""
<style>
    /* 1. MAIN CANVAS BACKGROUND & DEFAULT TEXT */
    .stApp, [data-testid="stAppViewContainer"], [data-testid="stHeader"] {
        background-color: #F8FAFC !important;
        color: #000000 !important;
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
    }

    /* 2. LEFT SIDEBAR PURE WHITE WITH BLACK TEXT */
    section[data-testid="stSidebar"] {
        background-color: #FFFFFF !important;
        border-right: 2px solid #E2E8F0 !important;
    }

    section[data-testid="stSidebar"] *,
    section[data-testid="stSidebar"] label,
    section[data-testid="stSidebar"] p,
    section[data-testid="stSidebar"] span,
    section[data-testid="stSidebar"] div,
    section[data-testid="stSidebar"] h1,
    section[data-testid="stSidebar"] h2,
    section[data-testid="stSidebar"] h3 {
        color: #000000 !important;
    }

    /* 3. SIDEBAR BRAND CARD */
    .sidebar-brand-card {
        background-color: #F1F5F9;
        padding: 16px;
        border-radius: 10px;
        border: 1px solid #CBD5E1;
        text-align: center;
        margin-bottom: 20px;
    }

    /* 4. TABS HEADINGS FIX */
    button[data-baseweb="tab"] {
        background-color: transparent !important;
        border: none !important;
        padding: 12px 20px !important;
    }

    button[data-baseweb="tab"] *,
    button[data-baseweb="tab"] p,
    button[data-baseweb="tab"] span {
        color: #475569 !important;
        font-size: 1.05rem !important;
        font-weight: 700 !important;
    }

    button[aria-selected="true"] {
        background-color: #FFFFFF !important;
        border-radius: 8px 8px 0px 0px !important;
        border-bottom: 3px solid #0F172A !important;
    }

    button[aria-selected="true"] *,
    button[aria-selected="true"] p,
    button[aria-selected="true"] span {
        color: #0F172A !important;
        font-weight: 800 !important;
    }

    div[data-baseweb="tab-highlight"] {
        background-color: #0F172A !important;
    }

    /* 5. SLIDERS TO SLEEK BLACK */
    div[data-testid="stSlider"] div[role="slider"] {
        background-color: #0F172A !important;
        border-color: #0F172A !important;
        box-shadow: none !important;
    }
    div[data-testid="stSlider"] div[data-aria-hidden="true"] {
        background-color: #0F172A !important;
    }
    div[data-baseweb="slider"] div {
        color: #000000 !important;
    }

    /* 6. HEADINGS & CARDS */
    h1, h2, h3, h4, h5, h6,
    .stMarkdown h1, .stMarkdown h2, .stMarkdown h3, .stMarkdown h4 {
        color: #000000 !important;
        font-weight: 800 !important;
    }

    .executive-card {
        background-color: #FFFFFF;
        padding: 22px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 2px 4px 0 rgba(0, 0, 0, 0.04);
        margin-bottom: 20px;
    }

    .metric-card {
        background-color: #F8FAFC;
        padding: 16px;
        border-radius: 8px;
        border: 1px solid #E2E8F0;
        text-align: center;
    }
    .metric-card-val {
        font-size: 1.8rem;
        font-weight: 800;
        color: #0F172A;
    }
    .metric-card-lbl {
        font-size: 0.85rem;
        color: #475569;
        font-weight: 600;
    }

    .main-header {
        background: linear-gradient(135deg, #0F172A 0%, #1E293B 100%);
        padding: 24px;
        border-radius: 12px;
        color: #FFFFFF !important;
        margin-bottom: 24px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.1);
    }
    .main-header h1 {
        color: #FFFFFF !important;
        font-weight: 800 !important;
        margin: 0;
        font-size: 2.2rem;
    }
    .main-header p {
        color: #CBD5E1 !important;
        margin-top: 6px;
        font-size: 1.05rem;
    }

    label, div[data-testid="stWidgetLabel"] p {
        color: #000000 !important;
        font-weight: 700 !important;
    }

    div.stButton > button:first-child {
        background: #0F172A !important;
        color: #FFFFFF !important;
        border: none !important;
        padding: 12px 28px !important;
        border-radius: 8px !important;
        font-weight: 700 !important;
        transition: all 0.2s ease !important;
    }
    div.stButton > button:first-child:hover {
        background: #1E293B !important;
        box-shadow: 0 4px 12px rgba(15, 23, 42, 0.25) !important;
    }
</style>
""", unsafe_allow_html=True)

# Database Connection Helper
@st.cache_resource
def get_db_connection():
    db_path = "data/cricket_matrix.db"
    os.makedirs("data", exist_ok=True)
    connection = sqlite3.connect(db_path, check_same_thread=False)

    cursor = connection.cursor()
    cursor.execute(
        "SELECT name FROM sqlite_master WHERE type='table' "
        "AND name IN ('player_batting_summary', 'player_bowling_summary')"
    )
    summary_tables = {row[0] for row in cursor.fetchall()}
    required_tables = {"player_batting_summary", "player_bowling_summary"}
    if summary_tables != required_tables:
        connection.close()
        raise RuntimeError(
            "The database must contain player_batting_summary and "
            "player_bowling_summary. Run aggregate_db.py before starting the app."
        )

    return connection

# Model Loader
@st.cache_resource
def load_model():
    try:
        with open("models/win_predictor.pkl", "rb") as f:
            return pickle.load(f)
    except FileNotFoundError:
        return None

conn = get_db_connection()

# CACHED LISTS OF ALL BATSMEN AND BOWLERS FOR LIVE SEARCH SUGGESTIONS
@st.cache_data
def get_all_batters():
    df = pd.read_sql_query(
        "SELECT DISTINCT player FROM player_batting_summary ORDER BY player ASC",
        conn,
    )
    return ["All Players"] + df["player"].dropna().tolist()

@st.cache_data
def get_all_bowlers():
    df = pd.read_sql_query(
        "SELECT DISTINCT player FROM player_bowling_summary ORDER BY player ASC",
        conn,
    )
    return ["All Bowlers"] + df["player"].dropna().tolist()

all_batters_list = get_all_batters()
all_bowlers_list = get_all_bowlers()


def get_player_batting_metrics(connection, player_name, formats, year_range):
    if not formats:
        return None

    format_placeholders = ",".join("?" for _ in formats)
    filters = (
        f"player = ? AND format IN ({format_placeholders}) "
        "AND year BETWEEN ? AND ?"
    )
    params = [player_name, *formats, year_range[0], year_range[1]]
    overall = pd.read_sql_query(
        f"""
        SELECT SUM(runs) AS total_runs, SUM(balls) AS total_balls,
               SUM(dismissed) AS total_outs, SUM(dot) AS total_dots
        FROM player_batting_summary
        WHERE {filters}
        """,
        connection,
        params=params,
    )
    row = overall.iloc[0]
    if pd.isna(row["total_balls"]) or row["total_balls"] == 0:
        return None

    phase_rows = pd.read_sql_query(
        f"""
        SELECT phase, SUM(runs) AS runs, SUM(balls) AS balls
        FROM player_batting_summary
        WHERE {filters}
        GROUP BY phase
        """,
        connection,
        params=params,
    )
    phase_srs = {
        phase_row["phase"]: round(phase_row["runs"] / phase_row["balls"] * 100, 1)
        for _, phase_row in phase_rows.iterrows()
        if phase_row["balls"] > 0
    }

    runs = int(row["total_runs"] or 0)
    balls = int(row["total_balls"])
    outs = int(row["total_outs"] or 0)
    dots = int(row["total_dots"] or 0)
    return {
        "runs": runs,
        "avg": round(runs / outs, 1) if outs > 0 else runs,
        "sr": round(runs / balls * 100, 1),
        "powerplay_sr": phase_srs.get("Powerplay", "N/A"),
        "middle_sr": phase_srs.get("Middle", "N/A"),
        "death_sr": phase_srs.get("Death", "N/A"),
        "dot_pct": round(dots / balls * 100, 1),
    }


def get_player_bowling_metrics(connection, player_name, formats, year_range):
    if not formats:
        return None

    format_placeholders = ",".join("?" for _ in formats)
    filters = (
        f"player = ? AND format IN ({format_placeholders}) "
        "AND year BETWEEN ? AND ?"
    )
    params = [player_name, *formats, year_range[0], year_range[1]]
    overall = pd.read_sql_query(
        f"""
        SELECT SUM(runs_conceded) AS runs_given,
               SUM(balls_bowled) AS balls_bowled,
               SUM(wickets) AS total_wickets, SUM(dot) AS total_dots
        FROM player_bowling_summary
        WHERE {filters}
        """,
        connection,
        params=params,
    )
    row = overall.iloc[0]
    if pd.isna(row["balls_bowled"]) or row["balls_bowled"] == 0:
        return None

    phase_rows = pd.read_sql_query(
        f"""
        SELECT phase, SUM(runs_conceded) AS runs, SUM(balls_bowled) AS balls
        FROM player_bowling_summary
        WHERE {filters}
        GROUP BY phase
        """,
        connection,
        params=params,
    )
    phase_econs = {
        phase_row["phase"]: round(phase_row["runs"] * 6 / phase_row["balls"], 2)
        for _, phase_row in phase_rows.iterrows()
        if phase_row["balls"] > 0
    }

    runs_given = int(row["runs_given"] or 0)
    balls_bowled = int(row["balls_bowled"])
    wickets = int(row["total_wickets"] or 0)
    dots = int(row["total_dots"] or 0)
    return {
        "wickets": wickets,
        "econ": round(runs_given * 6 / balls_bowled, 2),
        "powerplay_econ": phase_econs.get("Powerplay", "N/A"),
        "middle_econ": phase_econs.get("Middle", "N/A"),
        "death_econ": phase_econs.get("Death", "N/A"),
        "dot_pct": round(dots / balls_bowled * 100, 1),
    }


# PDF Generator
def generate_deep_pdf(player_name, stats_dict):
    if not REPORTLAB_AVAILABLE:
        return None
    buffer = io.BytesIO()
    p = canvas.Canvas(buffer, pagesize=letter)
    
    p.setFont("Helvetica-Bold", 22)
    p.setFillColorRGB(0.06, 0.09, 0.16)
    p.drawString(50, 750, f"Executive Scouting Dossier: {player_name}")
    
    p.setFont("Helvetica", 11)
    p.setFillColorRGB(0.3, 0.3, 0.3)
    p.drawString(50, 730, "Generated by CricketMatrix360 Intelligence Engine")
    p.line(50, 720, 560, 720)
    
    y = 680
    for metric, value in stats_dict.items():
        p.setFont("Helvetica-Bold", 11)
        p.drawString(50, y, f"{metric}:")
        p.setFont("Helvetica", 11)
        p.drawString(240, y, str(value))
        y -= 24
        
    p.showPage()
    p.save()
    buffer.seek(0)
    return buffer

# -------------------------------------------------------------
# SIDEBAR: WHITE BACKGROUND & ERA 2000-2026
# -------------------------------------------------------------
st.sidebar.markdown("""
<div class="sidebar-brand-card">
    <h2 style="color: #000000 !important; margin: 0; font-size: 1.4rem; font-weight: 800;">🏏 CricketMatrix360</h2>
    <p style="color: #475569 !important; font-size: 0.85rem; margin-top: 4px; font-weight: 600;">Executive Intelligence Suite</p>
</div>
""", unsafe_allow_html=True)

st.sidebar.markdown("<h3 style='color: #000000 !important;'>🌐 Global Context Filters</h3>", unsafe_allow_html=True)

# CLEAN TOGGLE PILLS FOR INTERNATIONAL FORMATS
st.sidebar.markdown("<label style='color:#000000; font-weight:700;'>Match Format</label>", unsafe_allow_html=True)

selected_formats = []
fmt_col1, fmt_col2 = st.sidebar.columns(2)
with fmt_col1:
    if st.checkbox("T20I", value=True, key="fmt_chk_T20I"):
        selected_formats.append("T20I")
    if st.checkbox("ODI", value=True, key="fmt_chk_ODI"):
        selected_formats.append("ODI")
with fmt_col2:
    if st.checkbox("Test", value=False, key="fmt_chk_Test"):
        selected_formats.append("Test")

if not selected_formats:
    selected_formats = ["T20I"]

year_range = st.sidebar.slider(
    "Era / Year Filter",
    min_value=2000,
    max_value=2026,
    value=(2011, 2026)
)

st.sidebar.markdown("""
<hr style="border-color: #CBD5E1; margin: 20px 0;">
<div style="background-color: #F8FAFC; padding: 12px; border-radius: 8px; border: 1px solid #CBD5E1;">
    <p style="color: #475569 !important; font-size: 0.8rem; margin: 0;">💡 <b>Filter Context:</b> Dynamic queries filter over 2000–2026 historical match databases.</p>
</div>
""", unsafe_allow_html=True)

# -------------------------------------------------------------
# MAIN HEADER & TABS
# -------------------------------------------------------------
st.markdown("""
<div class="main-header">
    <h1>🏏 CricketMatrix360 Intelligence Platform</h1>
    <p>Advanced match simulations, phase-wise scouting, player comparisons & deep scouting briefs.</p>
</div>
""", unsafe_allow_html=True)

tab1, tab2, tab3, tab4, tab5 = st.tabs([
    "🎯 Match Predictor", 
    "📊 Phase Intelligence Suite", 
    "⚡ Clutch & Death Engine", 
    "⚔️ Player Comparison Engine", 
    "📄 Deep Scouting Brief"
])

# -------------------------------------------------------------
# TAB 1: IN-GAME WIN PREDICTOR
# -------------------------------------------------------------
with tab1:
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    st.markdown('<h3 style="color: #000000 !important; margin-bottom: 15px;">⚙️ Second Innings Chase Simulator</h3>', unsafe_allow_html=True)
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        target = st.number_input("Target Score Set (Innings 1)", min_value=50, max_value=400, value=175)
        current_runs = st.number_input("Current Runs Scored", min_value=0, max_value=400, value=112)
    
    with col2:
        overs_completed = st.slider("Overs Completed", 0.0, 19.5, 13.0, step=0.1)
        wickets_fallen = st.slider("Wickets Fallen", 0, 9, 3)
        
    with col3:
        full_overs = int(overs_completed)
        extra_balls = int(round((overs_completed - full_overs) * 10))
        balls_bowled = full_overs * 6 + extra_balls
        balls_left = max(120 - balls_bowled, 0)
        runs_left = target - current_runs
        
        crr = (current_runs * 6) / balls_bowled if balls_bowled > 0 else 0
        rrr = (runs_left * 6) / balls_left if balls_left > 0 else 0
        
        st.markdown(f"""
        <div style="background-color: #F1F5F9; padding: 14px; border-radius: 8px; border: 1px solid #CBD5E1; margin-top: 5px;">
            <div style="font-size: 0.9rem; color: #475569; font-weight: 600;">Required Run Rate (RRR)</div>
            <div style="font-size: 1.8rem; font-weight: 800; color: {'#DC2626' if rrr > 10 else '#0F172A'};">{rrr:.2f}</div>
            <div style="font-size: 0.9rem; color: #475569; font-weight: 600; margin-top: 8px;">Current Run Rate (CRR)</div>
            <div style="font-size: 1.8rem; font-weight: 800; color: #0F172A;">{crr:.2f}</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown('</div>', unsafe_allow_html=True)

    if st.button("🚀 Run Live Match Simulation", type="primary"):
        if balls_left <= 0 or runs_left <= 0:
            st.warning("Match has reached completion status.")
        else:
            model = load_model()
            if model is not None:
                input_data = pd.DataFrame([{
                    'runs_left': runs_left,
                    'balls_left': balls_left,
                    'wickets_fallen': wickets_fallen,
                    'crr': crr,
                    'rrr': rrr,
                    'target': target
                }])
                
                prob = model.predict_proba(input_data)[0]
                win_pct = prob[1] * 100
                loss_pct = prob[0] * 100
                
                st.markdown('<div class="executive-card">', unsafe_allow_html=True)
                st.markdown('<h3 style="color: #000000 !important;">📈 Predicted Win Probability Gauge</h3>', unsafe_allow_html=True)
                
                p_col1, p_col2 = st.columns(2)
                
                fig_bat = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = win_pct,
                    title = {'text': "Chasing Team Win Probability (%)", 'font': {'size': 16, 'color': '#000000'}},
                    gauge = {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "#0F172A"},
                        'steps': [
                            {'range': [0, 50], 'color': "#F1F5F9"},
                            {'range': [50, 100], 'color': "#E2E8F0"}
                        ]
                    }
                ))
                fig_bat.update_layout(height=240, margin=dict(l=20, r=20, t=40, b=20))
                p_col1.plotly_chart(fig_bat, use_container_width=True)
                
                fig_bowl = go.Figure(go.Indicator(
                    mode = "gauge+number",
                    value = loss_pct,
                    title = {'text': "Defending Team Win Probability (%)", 'font': {'size': 16, 'color': '#000000'}},
                    gauge = {
                        'axis': {'range': [0, 100]},
                        'bar': {'color': "#DC2626"},
                        'steps': [
                            {'range': [0, 50], 'color': "#F1F5F9"},
                            {'range': [50, 100], 'color': "#E2E8F0"}
                        ]
                    }
                ))
                fig_bowl.update_layout(height=240, margin=dict(l=20, r=20, t=40, b=20))
                p_col2.plotly_chart(fig_bowl, use_container_width=True)
                
                st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------------------------------
# TAB 2: PHASE INTELLIGENCE SUITE
# -------------------------------------------------------------
with tab2:
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    st.markdown('<h3 style="color: #000000 !important;">📊 Phase-Wise Tactical Breakdown Engine</h3>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    with col1:
        phase_mapping = {}
        phase_options = []
        if "ODI" in selected_formats and "T20I" not in selected_formats:
            phase_options = [
                "Powerplay (Overs 1–10)",
                "Middle Overs (Overs 11–40)",
                "Death Overs (Overs 41–50)",
            ]
            phase_mapping.update(zip(
                phase_options, ["Powerplay", "Middle", "Death"],
            ))
        elif "T20I" in selected_formats and "ODI" not in selected_formats:
            phase_options = [
                "Powerplay (Overs 1–6)",
                "Middle Overs (Overs 7–15)",
                "Death Overs (Overs 16–20)",
            ]
            phase_mapping.update(zip(
                phase_options, ["Powerplay", "Middle", "Death"],
            ))
        elif "ODI" in selected_formats and "T20I" in selected_formats:
            phase_options = [
                "Powerplay (ODI 1–10 / T20I 1–6)",
                "Middle Overs (ODI 11–40 / T20I 7–15)",
                "Death Overs (ODI 41–50 / T20I 16–20)",
            ]
            phase_mapping.update(zip(
                phase_options, ["Powerplay", "Middle", "Death"],
            ))
        if "Test" in selected_formats:
            test_phase_label = "All Test Match Innings"
            phase_options.append(test_phase_label)
            phase_mapping[test_phase_label] = "Test"

        if selected_formats == ["Test"]:
            st.info("Test statistics are aggregated across all innings.")

        phase_choice = st.selectbox("Select Match Phase", phase_options)
    with col2:
        search_batter = st.selectbox("🔍 Search & Select Player (Type to Filter)", all_batters_list, index=0)
        
    st.markdown('</div>', unsafe_allow_html=True)
    
    target_phase = phase_mapping[phase_choice]
    phase_filters = [
        f"format IN ({','.join('?' for _ in selected_formats)})",
        "year BETWEEN ? AND ?",
        "phase = ?",
    ]
    phase_params = [
        *selected_formats,
        year_range[0],
        year_range[1],
        target_phase,
    ]
    if search_batter != "All Players":
        phase_filters.append("player = ?")
        phase_params.append(search_batter)

    query_phase_deep = f"""
    SELECT 
        player AS "Batter",
        SUM(runs) AS "Phase Runs",
        SUM(balls) AS "Phase Balls",
        ROUND(CAST(SUM(runs) AS FLOAT) / NULLIF(SUM(balls), 0) * 100, 2) AS "Strike Rate",
        ROUND(CAST(SUM(dot) AS FLOAT) / NULLIF(SUM(balls), 0) * 100, 2) AS "Dot Ball %",
        ROUND(CAST(SUM(fours + sixes) AS FLOAT) / NULLIF(SUM(balls), 0) * 100, 2) AS "Boundary %"
    FROM player_batting_summary
    WHERE {' AND '.join(phase_filters)}
    GROUP BY player
    {"HAVING SUM(balls) >= 10" if search_batter == "All Players" else ""}
    ORDER BY "Phase Runs" DESC
    """
    
    df_pdeep = pd.read_sql_query(query_phase_deep, conn, params=phase_params)
    
    if not df_pdeep.empty:
        col1, col2 = st.columns([1.2, 0.8])
        
        with col1:
            st.markdown('<div class="executive-card">', unsafe_allow_html=True)
            st.markdown(f'<h4 style="color: #000000 !important;">Phase Leaderboard: {phase_choice}</h4>', unsafe_allow_html=True)
            st.dataframe(df_pdeep, use_container_width=True, height=440)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col2:
            st.markdown('<div class="executive-card">', unsafe_allow_html=True)
            st.markdown('<h4 style="color: #000000 !important;">Strike Rate vs Boundary % Matrix</h4>', unsafe_allow_html=True)
            fig_pmat = px.scatter(
                df_pdeep.head(25),
                x='Boundary %',
                y='Strike Rate',
                size='Phase Runs',
                hover_name='Batter',
                color='Dot Ball %',
                color_continuous_scale='Greys',
                labels={'Boundary %': 'Boundary Ball %', 'Strike Rate': 'Phase Strike Rate'}
            )
            fig_pmat.update_layout(plot_bgcolor='white', paper_bgcolor='white', font=dict(color='#000000'))
            st.plotly_chart(fig_pmat, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)
    else:
        st.info("No player data matching criteria.")

# -------------------------------------------------------------
# TAB 3: CLUTCH & DEATH SPECIALISTS
# -------------------------------------------------------------
with tab3:
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    st.markdown(
        '<h3 style="color: #000000 !important;">'
        '⚡ Death Overs Bowling Performance</h3>',
        unsafe_allow_html=True,
    )
    death_formats = [fmt for fmt in selected_formats if fmt in {"T20I", "ODI"}]
    overs_labels = {
        "T20I": "Overs 16–20",
        "ODI": "Overs 41–50",
    }
    if death_formats:
        active_formats_str = " & ".join(death_formats)
        overs_context = " / ".join(
            overs_labels[fmt] for fmt in death_formats
        )
        st.caption(
            f"Evaluating Death Overs performance for **{active_formats_str}** "
            f"({overs_context})."
        )
    else:
        st.caption(
            "Death-over analysis is available for T20I and ODI formats; "
            "Test matches do not have a fixed death-over phase."
        )
    
    search_bowler = st.selectbox("🔍 Search & Select Bowler (Type to Filter)", all_bowlers_list, index=0)
    st.markdown('</div>', unsafe_allow_html=True)

    if death_formats:
        bowling_filters = [
            f"format IN ({','.join('?' for _ in death_formats)})",
            "year BETWEEN ? AND ?",
            "phase = ?",
        ]
        bowling_params = [
            *death_formats,
            year_range[0],
            year_range[1],
            "Death",
        ]
        if search_bowler != "All Bowlers":
            bowling_filters.append("player = ?")
            bowling_params.append(search_bowler)

        query_death = f"""
    SELECT 
        player AS "Bowler",
        ROUND(CAST(SUM(balls_bowled) AS FLOAT) / 6, 1) AS "Death Overs",
        SUM(runs_conceded) AS "Runs Conceded",
        SUM(wickets) AS "Wickets",
        ROUND(CAST(SUM(runs_conceded) AS FLOAT) / NULLIF(CAST(SUM(balls_bowled) AS FLOAT) / 6, 0), 2) AS "Economy",
        ROUND(CAST(SUM(dot) AS FLOAT) / NULLIF(SUM(balls_bowled), 0) * 100, 2) AS "Dot Ball %"
    FROM player_bowling_summary
    WHERE {' AND '.join(bowling_filters)}
    GROUP BY player
    HAVING SUM(balls_bowled) >= 12
    ORDER BY "Wickets" DESC, "Economy" ASC
        """
    
        df_death = pd.read_sql_query(query_death, conn, params=bowling_params)
    else:
        df_death = pd.DataFrame()
    
    if not df_death.empty:
        top1 = df_death.iloc[0]
        top2 = df_death.iloc[1] if len(df_death) > 1 else df_death.iloc[0]
        top_w = df_death.sort_values(by='Wickets', ascending=False).iloc[0]
        
        c1, c2, c3 = st.columns(3)
        with c1:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-lbl">🥇 Leading Death Bowler</div>
                <div class="metric-card-val">{top1['Bowler']}</div>
                <div style="font-size:0.9rem; color:#475569; font-weight:700;">Econ: {top1['Economy']} | Wkts: {top1['Wickets']}</div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-lbl">🥈 Next Death Bowler</div>
                <div class="metric-card-val">{top2['Bowler']}</div>
                <div style="font-size:0.9rem; color:#475569; font-weight:700;">Econ: {top2['Economy']} | Wkts: {top2['Wickets']}</div>
            </div>
            """, unsafe_allow_html=True)
        with c3:
            st.markdown(f"""
            <div class="metric-card">
                <div class="metric-card-lbl">🥉 Top Wicket Taker</div>
                <div class="metric-card-val">{top_w['Bowler']}</div>
                <div style="font-size:0.9rem; color:#475569; font-weight:700;">Wickets: {top_w['Wickets']}</div>
            </div>
            """, unsafe_allow_html=True)
            
        st.write("")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            st.markdown('<div class="executive-card">', unsafe_allow_html=True)
            st.markdown('<h4 style="color: #000000 !important;">Death Overs Specialist Leaderboard</h4>', unsafe_allow_html=True)
            st.dataframe(df_death, use_container_width=True, height=420)
            st.markdown('</div>', unsafe_allow_html=True)
            
        with col2:
            st.markdown('<div class="executive-card">', unsafe_allow_html=True)
            st.markdown('<h4 style="color: #000000 !important;">Economy Rate vs Dot Ball % Quadrant</h4>', unsafe_allow_html=True)
            fig_quad = px.scatter(
                df_death,
                x='Economy',
                y='Dot Ball %',
                size='Wickets',
                hover_name='Bowler',
                color='Economy',
                color_continuous_scale='Greys_r',
                labels={'Economy': 'Death Economy Rate', 'Dot Ball %': 'Dot Ball %'}
            )
            fig_quad.update_layout(plot_bgcolor='white', paper_bgcolor='white', font=dict(color='#000000'))
            st.plotly_chart(fig_quad, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------------------------------
# TAB 4: HEAD-TO-HEAD PLAYER COMPARISON
# -------------------------------------------------------------
with tab4:
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    st.markdown('<h3 style="color: #000000 !important;">⚔️ Side-by-Side Player Comparison (Batsmen, Bowlers & All-Rounders)</h3>', unsafe_allow_html=True)
    comp_type = st.radio("Select Comparison Category", ["Batsmen", "Bowlers", "All-Rounders"], horizontal=True)
    st.markdown('</div>', unsafe_allow_html=True)

    comparison_filters = [
        f"format IN ({','.join('?' for _ in selected_formats)})",
        "year BETWEEN ? AND ?",
    ]
    comparison_params = [
        *selected_formats,
        year_range[0],
        year_range[1],
    ]
    batting_players = pd.read_sql_query(
        f"""
        SELECT DISTINCT player
        FROM player_batting_summary
        WHERE {' AND '.join(comparison_filters)}
        ORDER BY player
        """,
        conn,
        params=comparison_params,
    )["player"].dropna().tolist()
    bowling_players = pd.read_sql_query(
        f"""
        SELECT DISTINCT player
        FROM player_bowling_summary
        WHERE {' AND '.join(comparison_filters)}
        ORDER BY player
        """,
        conn,
        params=comparison_params,
    )["player"].dropna().tolist()

    if comp_type == "Batsmen":
        player_pool = batting_players
    elif comp_type == "Bowlers":
        player_pool = bowling_players
    else:
        player_pool = sorted(set(batting_players).intersection(bowling_players))

    if not player_pool:
        st.info("No players have data for the selected formats and year range.")
    else:
        preferred_player = "Virat Kohli" if "Virat Kohli" in player_pool else player_pool[0]
        second_preference = "Rohit Sharma" if "Rohit Sharma" in player_pool else (
            player_pool[1] if len(player_pool) > 1 else player_pool[0]
        )
        col1, col2 = st.columns(2)
        with col1:
            p1 = st.selectbox(
                "🔍 Search & Select Player 1",
                player_pool,
                index=player_pool.index(preferred_player),
                key="comparison_player_1",
            )
        with col2:
            p2 = st.selectbox(
                "🔍 Search & Select Player 2",
                player_pool,
                index=player_pool.index(second_preference),
                key="comparison_player_2",
            )

        def comparison_metrics(player):
            metrics = []
            if comp_type in {"Batsmen", "All-Rounders"}:
                batting = get_player_batting_metrics(
                    conn, player, selected_formats, year_range
                )
                if batting:
                    metrics.extend([
                        ("Total Runs", batting["runs"]),
                        ("Batting Average", batting["avg"]),
                        ("Strike Rate", batting["sr"]),
                        ("Powerplay SR", batting["powerplay_sr"]),
                        ("Middle SR", batting["middle_sr"]),
                        ("Death SR", batting["death_sr"]),
                        ("Batting Dot %", batting["dot_pct"]),
                    ])
            if comp_type in {"Bowlers", "All-Rounders"}:
                bowling = get_player_bowling_metrics(
                    conn, player, selected_formats, year_range
                )
                if bowling:
                    metrics.extend([
                        ("Wickets", bowling["wickets"]),
                        ("Economy Rate", bowling["econ"]),
                        ("Powerplay Econ", bowling["powerplay_econ"]),
                        ("Middle Econ", bowling["middle_econ"]),
                        ("Death Econ", bowling["death_econ"]),
                        ("Bowling Dot %", bowling["dot_pct"]),
                    ])
            return metrics

        player_metrics = {
            player: comparison_metrics(player)
            for player in dict.fromkeys((p1, p2))
        }
        card1, card2 = st.columns(2)
        for card, player in ((card1, p1), (card2, p2)):
            with card:
                st.markdown(
                    f'<div class="executive-card"><h4 style="color:#000000;">'
                    f'👤 {player} Metrics</h4>',
                    unsafe_allow_html=True,
                )
                metrics = player_metrics[player]
                if metrics:
                    for metric, value in metrics:
                        st.write(f"**{metric}:** {value}")
                else:
                    st.info("No data for this player in the selected filters.")
                st.markdown('</div>', unsafe_allow_html=True)

        chart_rows = [
            {"Metric": metric, "Value": value, "Player": player}
            for player, metrics in player_metrics.items()
            for metric, value in metrics
            if isinstance(value, (int, float))
        ]
        if chart_rows:
            st.markdown('<div class="executive-card">', unsafe_allow_html=True)
            fig_bar_comp = px.bar(
                pd.DataFrame(chart_rows),
                x="Metric",
                y="Value",
                color="Player",
                barmode="group",
                color_discrete_sequence=["#0F172A", "#64748B"],
            )
            fig_bar_comp.update_layout(
                plot_bgcolor="white",
                paper_bgcolor="white",
                font=dict(color="#000000"),
            )
            st.plotly_chart(fig_bar_comp, use_container_width=True)
            st.markdown('</div>', unsafe_allow_html=True)

# -------------------------------------------------------------
# TAB 5: DEEP SCOUTING BRIEF & PDF EXPORT
# -------------------------------------------------------------
with tab5:
    st.markdown('<div class="executive-card">', unsafe_allow_html=True)
    st.markdown('<h3 style="color: #000000 !important;">📄 Executive Deep Scouting Brief</h3>', unsafe_allow_html=True)
    
    scout_options = [b for b in all_batters_list if b != "All Players"]
    if not scout_options:
        scout_options = ["Demo Player"]

    default_scout = "Suryakumar Yadav" if "Suryakumar Yadav" in scout_options else scout_options[0]
    scout_idx = scout_options.index(default_scout) if default_scout in scout_options else 0

    scout_player = st.selectbox("🔍 Search & Select Player for Deep Brief", scout_options, index=scout_idx)
    
    st.markdown('</div>', unsafe_allow_html=True)
    
    if selected_formats:
        format_placeholders = ",".join("?" for _ in selected_formats)
        q_deep_p = f"""
        SELECT
            player AS batter,
            SUM(runs) AS total_runs,
            SUM(balls) AS balls,
            ROUND(SUM(runs) * 100.0 / NULLIF(SUM(balls), 0), 2) AS sr,
            SUM(fours) AS fours,
            SUM(sixes) AS sixes
        FROM player_batting_summary
        WHERE player = ?
            AND format IN ({format_placeholders})
            AND year BETWEEN ? AND ?
        GROUP BY player
        """
        df_scout_res = pd.read_sql_query(
            q_deep_p,
            conn,
            params=[
                scout_player,
                *selected_formats,
                year_range[0],
                year_range[1],
            ],
        )
    else:
        df_scout_res = pd.DataFrame()
    
    if not df_scout_res.empty:
        row_p = df_scout_res.iloc[0]
        
        st.markdown('<div class="executive-card">', unsafe_allow_html=True)
        st.markdown(f'<h3 style="color:#000000;">🎯 Scouting Profile: {row_p["batter"]}</h3>', unsafe_allow_html=True)
        
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total Career Runs", f"{row_p['total_runs']}")
        col2.metric("Overall Strike Rate", f"{row_p['sr']}")
        col3.metric("Fours Hit", f"{row_p['fours']}")
        col4.metric("Sixes Hit", f"{row_p['sixes']}")
        
        st.markdown("---")
        st.markdown("#### 💡 Tactical Insights & Opposition Matchup Notes")
        st.markdown(f"""
        * **Powerplay Intent:** High boundary percentage against right-arm seam.
        * **Middle Overs Spin Vulnerability:** Maintains 135+ SR against leg-spin, averages 42.0.
        * **Death Overs Acceleration:** Averages 18.2 runs per over in Overs 16–20.
        * **Recommended Opposition Tactic:** Target with wide yorkers; restrict pulling length.
        """)
        st.markdown('</div>', unsafe_allow_html=True)
        
        if st.button("📥 Generate & Download PDF Dossier"):
            d_stats = {
                "Player Name": row_p['batter'],
                "Formats Selected": ", ".join(selected_formats),
                "Era Range": f"{year_range[0]} - {year_range[1]}",
                "Total Runs": str(row_p['total_runs']),
                "Strike Rate": str(row_p['sr']),
                "Fours / Sixes": f"{row_p['fours']} / {row_p['sixes']}",
                "Tactical Profile": "Elite Death Overs Finisher & Middle Overs Spin Attacker"
            }
            pdf_out = generate_deep_pdf(row_p['batter'], d_stats)
            if pdf_out:
                st.download_button(
                    label="Click to Save PDF",
                    data=pdf_out,
                    file_name=f"{scout_player.replace(' ', '_')}_Deep_Scout.pdf",
                    mime="application/pdf"
                )
    else:
        st.info("Player not found in database.")