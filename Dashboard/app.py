import streamlit as st

st.set_page_config(page_title="Cocoa Arrivals", layout="wide", initial_sidebar_state="collapsed")

st.markdown(
    """
<style>
[data-testid="stAppViewContainer"], [data-testid="stMain"], .main { background: #fafafa !important; }
[data-testid="stHeader"] { background: #fafafa !important; }
h1, h2, h3, h4, h5, h6 { color: #0a2463 !important; }
body, .main { color: #1a1a2e; }
.block-container { padding-top: 3.2rem; }
div[role="radiogroup"] { background: #eef0f6; padding: 4px; border-radius: 999px; gap: 2px; display: inline-flex; flex-wrap: wrap; }
div[role="radiogroup"] label { background: transparent !important; border-radius: 999px !important; padding: 4px 12px !important; margin: 0 !important; }
div[role="radiogroup"] label[data-baseweb="radio"] > div:first-child { display: none; }
div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 12px !important; color: #5a6688; }
div[role="radiogroup"] label:has(input:checked) { background: #0a2463 !important; }
div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #ffffff !important; font-weight: 600; }
/* header */
.app-title { color: #0a2463; font-weight: 800; font-size: 1.55rem; letter-spacing: -0.01em; line-height: 1.1; }
/* origin: segmented control */
.st-key-main, .st-key-main [data-testid="stRadio"], .st-key-main [data-testid="stRadio"] > div { width: 100% !important; display: flex; justify-content: flex-end; }
.st-key-main div[role="radiogroup"] { background: #e9ecf4; padding: 4px; border-radius: 12px; gap: 4px; box-shadow: inset 0 1px 2px rgba(10,36,99,0.06); }
.st-key-main div[role="radiogroup"] label { border-radius: 9px !important; padding: 7px 20px !important; transition: background .15s; }
.st-key-main div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 14px !important; font-weight: 600; color: #5a6688 !important; }
.st-key-main div[role="radiogroup"] label:hover { background: rgba(255,255,255,0.6) !important; }
.st-key-main div[role="radiogroup"] label:has(input:checked) { background: #ffffff !important; box-shadow: 0 1px 4px rgba(10,36,99,0.18); }
.st-key-main div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #0a2463 !important; font-weight: 700; }
/* pages: underlined tab strip */
[class*='st-key-nav'] div[role="radiogroup"] { background: transparent; padding: 0; border-radius: 0; gap: 26px; display: flex; width: 100%;
    border-bottom: 1px solid #e3e7f0; margin-bottom: 6px; }
[class*='st-key-nav'] div[role="radiogroup"] label { border-radius: 0 !important; padding: 8px 2px !important; margin-bottom: -1px !important;
    border-bottom: 2.5px solid transparent; }
[class*='st-key-nav'] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size: 14.5px !important; font-weight: 500; color: #7a86a8 !important; }
[class*='st-key-nav'] div[role="radiogroup"] label:hover div[data-testid="stMarkdownContainer"] p { color: #0a2463 !important; }
[class*='st-key-nav'] div[role="radiogroup"] label:has(input:checked) { background: transparent !important; border-bottom: 2.5px solid #1f8a9c !important; }
[class*='st-key-nav'] div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #0a2463 !important; font-weight: 700; }
/* tabs that hold an entry grid: light orange (This week on IVC, Entry Table in Forestero : Monthly) */
.st-key-nav_ivc div[role="radiogroup"] label:first-of-type div[data-testid="stMarkdownContainer"] p { color: #d07a2c !important; }
.st-key-nav_ivc div[role="radiogroup"] label:first-of-type:has(input:checked) { border-bottom-color: #e8913f !important; }
.st-key-nav_ivc div[role="radiogroup"] label:first-of-type:has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #b8621a !important; }
.st-key-moview div[role="radiogroup"] label:nth-of-type(2) div[data-testid="stMarkdownContainer"] p { color: #d07a2c !important; }
.st-key-moview div[role="radiogroup"] label:nth-of-type(2):has(input:checked) { background: #f6c99e !important; }
.st-key-moview div[role="radiogroup"] label:nth-of-type(2):has(input:checked) div[data-testid="stMarkdownContainer"] p { color: #7a3b08 !important; }
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
PAGES = {"IVC": ["This week", "Weekly Arrivals", "Forestero : Monthly"], "Ghana": ["Forestero : Monthly"], monthly.COMBINED: ["Forestero : Monthly"]}

head_l, head_r = st.columns([5, 2], vertical_alignment="center")
with head_r, st.container(key="main"):
    origin = st.radio("Origin", ORIGINS, horizontal=True, label_visibility="collapsed", key="origin")
with head_l:
    st.markdown(f"<div class='app-title'>Cocoa Arrivals</div>", unsafe_allow_html=True)
with st.container(key="nav_ivc" if origin == "IVC" else "nav"):
    page = st.radio("Page", PAGES[origin], horizontal=True, label_visibility="collapsed", key=f"page_{origin}")

if page == "This week":
    projection.render_week()
elif page == "Weekly Arrivals":
    season.render("IVC")
else:
    monthly.render(origin)
