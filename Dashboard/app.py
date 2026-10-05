from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Cocoa Arrivals", layout="wide", initial_sidebar_state="collapsed")

NAVY = "#0a2463"
DB = Path(__file__).resolve().parent.parent / "Database"
CROP_MONTHS = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
WEEKS_IN_MONTH = [5, 5] + [4] * 10                      # weeks 1-50; Cecafe-style desk convention, week 51 is left open
# (label, column, colour, dash, width) - same look as the desk Excel
SERIES = [
    ("ETG (24/25)", "etg_2425", "#a6a6a6", "solid", 2.5),
    ("Adj Eikon (25/26)", "eikon_adj_2526", "#c00000", "solid", 2.5),
    ("ETG (25/26)", "etg_2526", "#2e75b6", "solid", 2.5),
    ("Forestero (25/26)", "fo_2526", "#d9d9d9", "dash", 2.5),
    ("Raw Eikon (25/26)", "eikon_raw_2526", "#843c0c", "dot", 2.5),
    ("Forestero (26/27)", "fo_2627", "#9c7a00", "dash", 2.5),
]

st.markdown(
    """
<style>
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main { background: #fafafa !important; }
[data-testid="stHeader"] { background: #fafafa !important; }
h1, h2, h3, h4, h5, h6 { color: #0a2463 !important; }
body, .main { color: #1a1a2e; }
.block-container { padding-top: 2.2rem; }
div[role="radiogroup"] { background: #eef0f6; padding: 4px; border-radius: 999px; gap: 2px; display: inline-flex; flex-wrap: wrap; }
div[role="radiogroup"] label { background: transparent !important; border-radius: 999px !important; padding: 4px 12px !important; margin: 0 !important; }
div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child { display: none; }
div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 12px !important; color: #5a6688; }
div[role="radiogroup"] label:has(input:checked) { background: #0a2463 !important; }
div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; font-weight: 600; }
.st-key-main div[role="radiogroup"] { background: transparent; border-bottom: 2px solid #dfe3ee; border-radius: 0; padding: 0; gap: 6px; display: flex; width: 100%; }
.st-key-main div[role="radiogroup"] label { background: transparent !important; border-radius: 0 !important; padding: 8px 16px !important; margin-bottom: -2px !important; border-bottom: 3px solid transparent; }
.st-key-main div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 17px !important; font-weight: 700; color: #7a86a8 !important; }
.st-key-main div[role="radiogroup"] label:has(input:checked) { background: transparent !important; border-bottom: 3px solid #0a2463 !important; }
.st-key-main div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #0a2463 !important; }
.card-desc { color: #5a6688; font-size: 0.82rem; margin-top: -6px; margin-bottom: 10px; }
.page-title { color: #0a2463; font-weight: 700; font-size: 1.25rem; margin: 0 0 6px 0; }
.card-title { color: #0a2463; font-weight: 700; font-size: 1rem; margin-bottom: 2px; }
[data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) {
    background: #ffffff; border: 1px solid #e3e7f0 !important; border-radius: 12px;
    box-shadow: 0 1px 3px rgba(10,36,99,0.06); }
</style>
""",
    unsafe_allow_html=True,
)


@st.cache_data(ttl=600)
def load():
    return pd.read_csv(DB / "weekly.csv"), pd.read_csv(DB / "monthly.csv")


def forestero_weekly(monthly: pd.DataFrame, origin: str, typ: str, crop_year: str) -> pd.Series:
    """Monthly Forestero figure spread evenly over the weeks of that month -> weekly step series (index = week 1-50)."""
    m = monthly[(monthly.origin == origin) & (monthly.type == typ) & (monthly.crop_year == crop_year)]
    kt = m.set_index("month").kt
    out, wk = {}, 1
    for mon, n in zip(CROP_MONTHS, WEEKS_IN_MONTH):
        for w in range(wk, wk + n):
            out[w] = kt.get(mon, float("nan")) / n
        wk += n
    return pd.Series(out)


def chart(df: pd.DataFrame, cumulative: bool, height: int):
    fig = go.Figure()
    for label, col, colour, dash, width in SERIES:
        if col not in df or df[col].notna().sum() == 0:
            continue
        y = df[col].cumsum(skipna=True).where(df[col].notna()) if cumulative else df[col]
        fig.add_scatter(x=df.week, y=y, name=label, mode="lines", connectgaps=False,
                        line=dict(color=colour, dash=dash, width=width, shape="hv" if (dash == "dash" and not cumulative) else "linear"),
                        hovertemplate="%{y:,.0f}")
    fig.update_layout(
        template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#1a1a2e"), hovermode="x unified", height=height,
        xaxis=dict(title="Week of crop year (1 = first week of October)", gridcolor="rgba(10,36,99,0.08)", color="#4a5578", dtick=2, range=[0.5, 51.5]),
        yaxis=dict(gridcolor="rgba(10,36,99,0.08)", color="#4a5578", tickformat=",", hoverformat=",.0f", rangemode="tozero"),
        legend=dict(orientation="h", x=0, y=-0.2, xanchor="left", yanchor="top", font=dict(size=11), bgcolor="rgba(0,0,0,0)"),
        margin=dict(t=10, b=10, l=10, r=10),
    )
    return fig


def render_weekly(origin: str = "IVC"):
    weekly, monthly = load()
    oc = st.columns([1.3, 6], vertical_alignment="center")
    with oc[0]:
        typ = st.radio("Forestero", ["Stat", "Tree"], horizontal=True, label_visibility="collapsed", key="fo_type",
                       help="Forestero monthly series used for the dashed lines: Stat = statistical, Tree = tree-count based.")
    df = weekly.copy()
    for col, cy in [("fo_2526", "25/26"), ("fo_2627", "26/27")]:
        df[col] = df.week.map(forestero_weekly(monthly, origin, typ, cy))

    with st.container(border=True):
        st.markdown(f"<div class='card-title'>Weekly arrivals 25/26 {origin}</div>"
                    "<div class='card-desc'>Forestero lines are the monthly figure divided over that month's weeks "
                    "(Oct and Nov 5 weeks, the rest 4). Adj Eikon is the Eikon feed after the desk adjustment.</div>",
                    unsafe_allow_html=True)
        st.plotly_chart(chart(df, False, 430), width="stretch")
    with st.container(border=True):
        st.markdown(f"<div class='card-title'>Cumulative arrivals {origin}</div>", unsafe_allow_html=True)
        st.plotly_chart(chart(df, True, 430), width="stretch")


with st.container(key="main"):
    main = st.radio("Section", ["IVC"], horizontal=True, label_visibility="collapsed", key="main_tab")
st.markdown("<div class='page-title'>Cocoa arrivals</div>", unsafe_allow_html=True)
if main == "IVC":
    render_weekly("IVC")
