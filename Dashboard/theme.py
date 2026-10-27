"""COT_ALL look (light glass, navy) for the Cocoa app: fonts, glass sidebar, pill radios, glass dropdowns, chart cards."""
import streamlit as st

GRID = "rgba(10,36,99,0.08)"
AXIS = "#4a5578"
FONT = "Inter,'Plus Jakarta Sans',-apple-system,BlinkMacSystemFont,'Helvetica Neue',sans-serif"

FONTS = ("<style>@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,wght@0,500;0,600;1,500&"
         "family=Inter:wght@400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');</style>")

CSS = """
<style>
  :root { color-scheme: light !important; }
  html, body, [class*="css"], [data-testid="stAppViewContainer"], .stMarkdown, button, input, textarea {
    font-family:'Inter', system-ui, -apple-system, 'Segoe UI', sans-serif !important; -webkit-font-smoothing:antialiased; }
  .block-container { max-width:1600px; }
  /* sidebar: frosted glass, light */
  [data-testid="stSidebar"] { background:linear-gradient(160deg, rgba(246,248,253,.92) 0%, rgba(233,238,248,.88) 55%, rgba(240,236,246,.9) 100%) !important;
    -webkit-backdrop-filter:blur(24px) saturate(160%); backdrop-filter:blur(24px) saturate(160%);
    border-right:1px solid rgba(255,255,255,.75) !important; box-shadow:inset -1px 0 0 rgba(10,36,99,.06), 6px 0 28px rgba(10,36,99,.06); }
  .sb-brand { font-family:'Plus Jakarta Sans','Inter',sans-serif; font-size:1.12rem; font-weight:800; color:#0a2463; letter-spacing:-.01em; line-height:1.2; margin:0 0 4px 4px; }
  .sb-caption { font-family:'Plus Jakarta Sans','Inter',sans-serif; font-size:10.5px; font-weight:700; letter-spacing:.14em; text-transform:uppercase;
    color:#7a86a8; margin:0 0 14px 4px; }
  .sb-rule { height:1px; background:rgba(43,74,138,.12); margin:0 0 18px; }
  [data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { font-family:'Plus Jakarta Sans','Inter',sans-serif !important; font-size:10.5px !important;
    font-weight:700 !important; letter-spacing:.14em !important; text-transform:uppercase; color:#7a86a8 !important; }
  /* pill tracks (radios): frosted glass, navy gradient pick */
  div[role="radiogroup"] { background:linear-gradient(160deg, rgba(250,252,255,.97), rgba(236,242,251,.93) 60%, rgba(229,237,249,.9)) !important;
    border:1px solid rgba(43,74,138,.14) !important; box-shadow:0 4px 16px rgba(30,58,110,.07), inset 0 1px 0 rgba(255,255,255,.95) !important; }
  div[role="radiogroup"] label p { font-family:'Plus Jakarta Sans','Inter',system-ui,sans-serif !important; letter-spacing:.01em; }
  div[role="radiogroup"] label:has(input:checked) { background:linear-gradient(180deg, #2b4a8a, #1e3a6e) !important; color:#ffffff !important;
    box-shadow:0 2px 8px rgba(30,58,110,.28), inset 0 1px 0 rgba(255,255,255,.18) !important; }
  div[role="radiogroup"] label { transition:background .15s, transform .15s; }
  div[role="radiogroup"] label:not(:has(input:checked)):hover { background:rgba(43,74,138,.07) !important; transform:translateY(-1px); }
  /* sidebar section list: stacked pills on a glass track */
  .st-key-section div[role="radiogroup"] { border-radius:22px !important; padding:4px !important; gap:3px !important; }
  .st-key-section div[role="radiogroup"] label { border-radius:18px !important; border-left:0 !important; padding:9px 14px !important; box-shadow:none; }
  .st-key-section div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { color:#5a6688 !important; font-size:13.5px !important; font-weight:600; }
  .st-key-section div[role="radiogroup"] label:hover { background:rgba(43,74,138,.07) !important; }
  .st-key-section div[role="radiogroup"] label:has(input:checked) { background:linear-gradient(180deg, #2b4a8a, #1e3a6e) !important;
    border-left:0 !important; box-shadow:0 2px 8px rgba(30,58,110,.28), inset 0 1px 0 rgba(255,255,255,.18) !important; }
  .st-key-section div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color:#ffffff !important; font-weight:700; }
  /* Data Entry (4th section): dark orange so it reads apart from the view sections */
  .st-key-section div[role="radiogroup"] label:nth-of-type(4) div[data-testid="stMarkdownContainer"] p { color:#b8560a !important; }
  .st-key-section div[role="radiogroup"] label:nth-of-type(4):hover { background:rgba(194,87,12,.10) !important; }
  .st-key-section div[role="radiogroup"] label:nth-of-type(4):has(input:checked) { background:linear-gradient(180deg, #d9650f, #b8560a) !important;
    box-shadow:0 2px 8px rgba(184,86,10,.35), inset 0 1px 0 rgba(255,255,255,.2) !important; }
  .st-key-section div[role="radiogroup"] label:nth-of-type(4):has(input:checked) div[data-testid="stMarkdownContainer"] p { color:#ffffff !important; }
  /* origin switch (top right) */
  .st-key-main div[role="radiogroup"] { border-radius:999px !important; padding:4px !important; gap:2px !important; }
  .st-key-main div[role="radiogroup"] label { border-radius:999px !important; padding:6px 18px !important; }
  .st-key-main div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { color:#5a6688 !important; font-size:13px !important; }
  .st-key-main div[role="radiogroup"] label:has(input:checked) { background:linear-gradient(180deg, #2b4a8a, #1e3a6e) !important; box-shadow:0 2px 8px rgba(30,58,110,.28) !important; }
  .st-key-main div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color:#ffffff !important; }
  /* page tabs: pill-track tabs like COT's st.tabs */
  [class*='st-key-nav'] div[role="radiogroup"], .st-key-moview div[role="radiogroup"] { border-radius:999px !important;
    padding:4px !important; gap:4px !important; width:fit-content !important; margin-bottom:8px; }
  [class*='st-key-nav'] div[role="radiogroup"] label, .st-key-moview div[role="radiogroup"] label { border-radius:999px !important; padding:8px 20px !important;
    margin-bottom:0 !important; border-bottom:0 !important; }
  [class*='st-key-nav'] div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p,
  .st-key-moview div[role="radiogroup"] label div[data-testid="stMarkdownContainer"] p { font-size:13.6px !important; font-weight:600 !important; color:#5a6688 !important; }
  [class*='st-key-nav'] div[role="radiogroup"] label:has(input:checked), .st-key-moview div[role="radiogroup"] label:has(input:checked) {
    background:linear-gradient(180deg, #2b4a8a, #1e3a6e) !important; border-bottom:0 !important; box-shadow:0 2px 8px rgba(30,58,110,.28), inset 0 1px 0 rgba(255,255,255,.18) !important; }
  [class*='st-key-nav'] div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p,
  .st-key-moview div[role="radiogroup"] label:has(input:checked) div[data-testid="stMarkdownContainer"] p { color:#ffffff !important; font-weight:700 !important; }
  /* dropdowns: glass pill, wine caret */
  [data-baseweb="select"] { background:transparent !important; box-shadow:none !important; }
  [data-baseweb="select"] > div { background:linear-gradient(180deg, rgba(255,255,255,.78), rgba(238,242,250,.62)) !important;
    -webkit-backdrop-filter:blur(14px) saturate(170%); backdrop-filter:blur(14px) saturate(170%);
    border:1px solid rgba(255,255,255,.9) !important; border-radius:999px !important; min-height:34px; color:#0a2463 !important;
    box-shadow:0 1px 2px rgba(10,36,99,.06), 0 6px 18px rgba(10,36,99,.08), inset 0 1px 0 rgba(255,255,255,.95); transition:box-shadow .18s, transform .18s; }
  [data-baseweb="select"] > div:hover { box-shadow:0 0 0 3px rgba(10,36,99,.07), 0 8px 22px rgba(10,36,99,.14), inset 0 1px 0 rgba(255,255,255,.95); transform:translateY(-1px); }
  [data-baseweb="select"] > div:focus-within { box-shadow:0 0 0 3px rgba(123,30,58,.16), 0 8px 22px rgba(10,36,99,.14) !important; }
  [data-baseweb="select"] svg { fill:#7b1e3a !important; }
  /* multiselects (Crop year / Source): deep orange chips */
  [data-testid="stMultiSelect"] span[data-baseweb="tag"], [data-testid="stMultiSelect"] span[data-baseweb="tag"] div,
  [data-testid="stMultiSelect"] span[data-baseweb="tag"] span { background-color:#d9480f !important; color:#ffffff !important; }
  [data-testid="stMultiSelect"] span[data-baseweb="tag"] { border-radius:8px !important; box-shadow:0 1px 3px rgba(217,72,15,.35); }
  [data-testid="stMultiSelect"] span[data-baseweb="tag"] svg { fill:#ffffff !important; }
  [data-testid="stMultiSelect"] [data-baseweb="select"] svg { fill:#d9480f !important; }
  [data-testid="stMultiSelect"] [data-baseweb="select"] > div:focus-within { box-shadow:0 0 0 3px rgba(217,72,15,.18), 0 8px 22px rgba(10,36,99,.14) !important; }
  [data-baseweb="popover"] [data-baseweb="menu"], [data-baseweb="popover"] ul { background:rgba(255,255,255,.82) !important;
    -webkit-backdrop-filter:blur(18px) saturate(170%); backdrop-filter:blur(18px) saturate(170%);
    border:1px solid rgba(255,255,255,.9) !important; border-radius:14px !important; box-shadow:0 14px 40px rgba(10,36,99,.18) !important; }
  [data-baseweb="popover"] li:hover { background:rgba(43,74,138,.07) !important; }
  [data-baseweb="popover"] li[aria-selected="true"] { background:rgba(123,30,58,.10) !important; }
  [data-testid="stMain"] [data-testid="stWidgetLabel"] p { font-family:'Plus Jakarta Sans','Inter',sans-serif !important; font-size:12.5px !important;
    font-weight:600 !important; color:#1e3a6e !important; }
  /* no frames: charts, cards and tables sit straight on the page */
  [data-testid="stMain"] [data-testid="stPlotlyChart"] { background:transparent; border:0; box-shadow:none; padding:0; }
  [data-testid="stVerticalBlockBorderWrapper"]:has(> div > [data-testid="stVerticalBlock"]) { background:transparent !important; border:0 !important;
    box-shadow:none !important; border-radius:0; }
  .card-title, .page-title, .app-title { font-family:'Plus Jakarta Sans','Inter',sans-serif; letter-spacing:-.005em; }
  /* buttons */
  .stButton > button, .stDownloadButton > button { border-radius:999px; border:1px solid rgba(43,74,138,.18); background:linear-gradient(180deg,#ffffff,#eef2fa);
    color:#0a2463; font-weight:600; box-shadow:0 1px 2px rgba(10,36,99,.06); transition:box-shadow .18s, transform .18s; }
  .stButton > button:hover, .stDownloadButton > button:hover { transform:translateY(-1px); box-shadow:0 8px 20px rgba(10,36,99,.14); border-color:rgba(43,74,138,.35); color:#0a2463; }
</style>
"""


def apply():
    st.markdown(FONTS, unsafe_allow_html=True)
    st.markdown(CSS, unsafe_allow_html=True)


def style(fig):
    """COT chart base: white template, transparent bg, navy-grey grid, same font."""
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font=dict(family=FONT, color="#1a1a2e", size=11))
    fig.update_xaxes(gridcolor=GRID, linecolor="rgba(0,0,0,0.08)", tickfont=dict(size=10, color=AXIS))
    fig.update_yaxes(gridcolor=GRID, linecolor="rgba(0,0,0,0.08)", zerolinecolor="rgba(0,0,0,0.12)", tickfont=dict(size=10, color=AXIS))
    return fig
