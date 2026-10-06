import streamlit as st

st.set_page_config(page_title="Cocoa Arrivals", layout="wide", initial_sidebar_state="collapsed")

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

import monthly
import projection
import season

ORIGINS = ["IVC", "Ghana", monthly.COMBINED]
PAGES = {"IVC": ["This week", "Weekly Arrivals", "Forestero : Monthly", "Accuracy"], "Ghana": ["Forestero : Monthly"], monthly.COMBINED: ["Forestero : Monthly"]}

with st.container(key="main"):
    origin = st.radio("Origin", ORIGINS, horizontal=True, label_visibility="collapsed", key="origin")
st.markdown(f"<div class='page-title'>Cocoa arrivals - {origin}</div>", unsafe_allow_html=True)
with st.container(key="nav"):
    page = st.radio("Page", PAGES[origin], horizontal=True, label_visibility="collapsed", key=f"page_{origin}")

if page == "This week":
    projection.render_week()
elif page == "Weekly Arrivals":
    season.render("IVC")
elif page == "Accuracy":
    projection.render_accuracy(projection.build())
else:
    monthly.render(origin)
