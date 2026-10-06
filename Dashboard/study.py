"""Study: pod counts vs arrivals.

Pods = monthly survey (pods per tree): TOTAL = pod load, Settings = Tiny + Small-1 (new fruit set).
Arrivals = monthly, thousand tonnes: ETG (Abidjan + San Pedro week totals summed by the week's month, IVC only, from Sep-23)
or Forestero Stat / Tree (IVC and Ghana, crop year Oct-Sep, from 21/22; the 26/27 column is Forestero's own estimate).
Pods lead arrivals by a few months: the lag study measures by how much, and a one-line regression at that lag gives
the arrivals the current pod load implies for the months not reported yet.
"""
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from plotly.subplots import make_subplots

import monthly
import projection
from pod.data_loader import LTA_YEAR, load_raw

CROP_MONTHS = ["Oct", "Nov", "Dec", "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep"]
MAX_LAG = 8
NAVY, TEAL, ORANGE, GREY = "#0a2463", "#1f8a9c", "#e07b39", "#6b7280"


# ---------------------------------------------------------------------------------------------
# data
# ---------------------------------------------------------------------------------------------
def pods(country: str) -> pd.DataFrame:
    """Monthly pod load (TOTAL) and Settings (Tiny + Small-1), pods per tree, index = month start."""
    d = load_raw()
    d = d[(d.COUNTRY == country) & (d.Year != LTA_YEAR)].dropna(subset=["NUMBER"])
    d = d.assign(date=pd.to_datetime(dict(year=d.Year, month=d.Month, day=1)))
    tot = d[d.CLASS == "TOTAL"].groupby("date").NUMBER.sum()
    sett = d[d.CLASS.isin(["1. Tiny", "2.1 Small-1"])].groupby("date").NUMBER.sum(min_count=1)
    return pd.DataFrame({"pods": tot, "settings": sett}).sort_index()


def forestero(country: str, typ: str) -> tuple[pd.Series, pd.Series]:
    """(actual, Forestero 26/27-style estimate) monthly kt. A crop year is an estimate while its months are still ahead."""
    m = monthly.load()
    m = m[(m.origin == country) & (m.type == typ)]
    mi = {mo: i for i, mo in enumerate(CROP_MONTHS)}
    start = m.crop_year.str[:2].astype(int) + 2000
    month_num = m.month.map({mo: (i + 9) % 12 + 1 for i, mo in enumerate(CROP_MONTHS)})
    year = start + (m.month.map(mi) >= 3).astype(int)                 # Jan-Sep fall in the second calendar year
    s = pd.Series(m.kt.to_numpy(float), index=pd.to_datetime(dict(year=year, month=month_num, day=1))).sort_index()
    today = pd.Timestamp.today().normalize().replace(day=1)
    return s[s.index < today], s[s.index >= today]


def etg_monthly() -> tuple[pd.Series, pd.Series]:
    """(complete-month actuals, running month incl. projected days) in kt from the port weeks, by the week's Monday."""
    data = projection.build()
    ab, sp = data["Abidjan"].set_index("week"), data["San Pedro"].set_index("week")
    tot = (ab["total"] + sp["total"]).dropna() / 1000
    s = tot.groupby(tot.index.to_period("M").to_timestamp()).sum()
    last = s.index.max()
    return s[s.index < last], s[s.index >= last]


def lag_table(p: pd.DataFrame, arr: pd.Series) -> pd.DataFrame:
    rows = []
    for lag in range(MAX_LAG + 1):
        row = {"lag": lag}
        for col in ("pods", "settings"):
            x = p[col].shift(lag, freq="MS").reindex(arr.index)
            ok = x.notna() & arr.notna()
            row[col] = x[ok].corr(arr[ok]) if ok.sum() >= 8 else np.nan
            row[f"n_{col}"] = int(ok.sum())
        rows.append(row)
    return pd.DataFrame(rows)


def fit(p: pd.Series, arr: pd.Series, lag: int):
    """arrivals(t) = a + b * pods(t - lag): returns a, b, r2, n and the implied series for every month pods allow."""
    x = p.shift(lag, freq="MS")
    both = pd.concat([x, arr], axis=1, keys=["x", "y"]).dropna()
    if len(both) < 8:
        return None
    b, a = np.polyfit(both.x, both.y, 1)
    r2 = np.corrcoef(both.x, both.y)[0, 1] ** 2
    implied = (a + b * x).clip(lower=0)
    return a, b, r2, len(both), implied


# ---------------------------------------------------------------------------------------------
# charts
# ---------------------------------------------------------------------------------------------
def _shade_harvest(fig, start, end, rows=(1, 2)):
    """Oct-Mar = main-crop harvest window."""
    y = start.year - 1
    while pd.Timestamp(y, 10, 1) <= end:
        a, b = pd.Timestamp(y, 10, 1) - pd.Timedelta(days=15), pd.Timestamp(y + 1, 3, 1) + pd.Timedelta(days=15)
        for r in rows:
            fig.add_vrect(x0=a, x1=b, fillcolor="rgba(10,36,99,0.05)", line_width=0, row=r, col=1)
        y += 1


def combined_chart(p, arr_act, arr_est, implied, est_label, lag):
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.07, row_heights=[0.45, 0.55])
    fig.add_scatter(x=p.index, y=p.pods, name="Pod load (TOTAL)", mode="lines+markers", line=dict(color=NAVY, width=2.4),
                    marker=dict(size=4), row=1, col=1, hovertemplate="%{y:.1f}")
    fig.add_scatter(x=p.index, y=p.settings, name="Settings (Tiny + Small-1)", mode="lines+markers",
                    line=dict(color=ORANGE, width=2), marker=dict(size=4), row=1, col=1, hovertemplate="%{y:.1f}")
    fig.add_bar(x=arr_act.index, y=arr_act, name="Arrivals", marker_color=TEAL, row=2, col=1, hovertemplate="%{y:,.0f} kt")
    if len(arr_est):
        fig.add_bar(x=arr_est.index, y=arr_est, name=est_label, marker=dict(color="rgba(31,138,156,0.25)", line=dict(color=TEAL, width=1)),
                    row=2, col=1, hovertemplate="%{y:,.0f} kt")
    if implied is not None and len(implied):
        fig.add_bar(x=implied.index, y=implied, name=f"Pod-implied (lag {lag})",
                    marker=dict(color="rgba(224,123,57,0.15)", line=dict(color=ORANGE, width=1.5), pattern=dict(shape="/", fgcolor=ORANGE)),
                    row=2, col=1, hovertemplate="%{y:,.0f} kt (implied)")
    start = min(p.index.min(), arr_act.index.min())
    end = max(p.index.max(), (implied.index.max() if implied is not None and len(implied) else p.index.max()),
              arr_est.index.max() if len(arr_est) else p.index.max())
    _shade_harvest(fig, start, end)
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", barmode="overlay",
                      height=560, margin=dict(t=10, b=10, l=10, r=10), hovermode="x unified", font=dict(size=11, color="#1a1a2e"),
                      legend=dict(orientation="h", x=0, y=-0.08, yanchor="top", font=dict(size=11)))
    fig.update_yaxes(title_text="pods per tree", row=1, col=1, gridcolor="rgba(10,36,99,0.08)", rangemode="tozero")
    fig.update_yaxes(title_text="arrivals, kt", row=2, col=1, gridcolor="rgba(10,36,99,0.08)", tickformat=",", rangemode="tozero")
    fig.update_xaxes(dtick="M3", tickformat="%b-%y", gridcolor="rgba(10,36,99,0.05)", range=[start - pd.Timedelta(days=20), end + pd.Timedelta(days=20)])
    return fig


def lag_chart(lt: pd.DataFrame, best: int):
    fig = go.Figure()
    fig.add_bar(x=lt.lag, y=lt.pods, name="Pod load", marker_color=[NAVY if l == best else "rgba(10,36,99,0.35)" for l in lt.lag],
                hovertemplate="lag %{x}: r = %{y:.2f}<extra>Pod load</extra>")
    fig.add_bar(x=lt.lag, y=lt.settings, name="Settings", marker_color="rgba(224,123,57,0.55)",
                hovertemplate="lag %{x}: r = %{y:.2f}<extra>Settings</extra>")
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300,
                      margin=dict(t=10, b=10, l=10, r=10), barmode="group", font=dict(size=11, color="#1a1a2e"),
                      legend=dict(orientation="h", x=0, y=-0.2, yanchor="top"),
                      xaxis=dict(title="pods lead arrivals by (months)", dtick=1), yaxis=dict(title="correlation", range=[-1, 1], zeroline=True))
    return fig


def scatter_chart(p: pd.Series, arr: pd.Series, lag: int, res):
    """Each point = one month: arrivals vs the pod load `lag` months earlier, coloured by crop season (Oct-Sep)."""
    x = p.shift(lag, freq="MS").reindex(arr.index)
    d = pd.DataFrame({"x": x, "y": arr}).dropna()
    d["season"] = [f"{(t.year if t.month >= 10 else t.year - 1) % 100:02d}/{(t.year + (t.month >= 10)) % 100:02d}" for t in d.index]
    pal = ["#a6a6a6", "#c98a1f", "#1f9d6f", "#2e75b6", NAVY]
    fig = go.Figure()
    for i, (cy, g) in enumerate(d.groupby("season")):
        fig.add_scatter(x=g.x, y=g.y, mode="markers", name=cy, marker=dict(size=8, color=pal[i % len(pal)], line=dict(color="#fff", width=1)),
                        text=[t.strftime("%b-%y") for t in g.index], hovertemplate="%{text}: pods %{x:.1f} -> %{y:,.0f} kt<extra></extra>")
    if res:
        a, b = res[0], res[1]
        xs = np.linspace(d.x.min(), d.x.max(), 20)
        fig.add_scatter(x=xs, y=a + b * xs, mode="lines", name="fit", line=dict(color=ORANGE, dash="dash", width=2), hoverinfo="skip")
    fig.update_layout(template="plotly_white", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", height=300,
                      margin=dict(t=10, b=10, l=10, r=10), font=dict(size=11, color="#1a1a2e"),
                      legend=dict(orientation="h", x=0, y=-0.2, yanchor="top"),
                      xaxis=dict(title=f"pod load {lag} months earlier (per tree)"), yaxis=dict(title="arrivals, kt", rangemode="tozero"))
    return fig


# ---------------------------------------------------------------------------------------------
# season view: Apr-Sep pods (survey ahead of the harvest) vs the Oct-Mar arrivals that follow
# ---------------------------------------------------------------------------------------------
def season_table(p: pd.DataFrame, arr: pd.Series, est: pd.Series, implied) -> str:
    rows = []
    first = arr.dropna().index.min()
    years = sorted({d.year for d in p.index})
    years = [y for y in years if pd.Timestamp(y + 1, 3, 1) >= first]
    last_year = years[-1] if years else None
    ratios = []
    for y in years:
        pw = p.pods[(p.index >= pd.Timestamp(y, 4, 1)) & (p.index <= pd.Timestamp(y, 9, 1))]
        win = pd.date_range(pd.Timestamp(y, 10, 1), pd.Timestamp(y + 1, 3, 1), freq="MS")
        act = arr.reindex(win)
        full = act.notna().all()
        a_sum = act.sum() if full else np.nan
        e_sum = est.reindex(win).sum(min_count=1) if est is not None and len(est) else np.nan
        i_sum = implied.reindex(win).sum(min_count=1) if implied is not None else np.nan
        i_n = int(implied.reindex(win).notna().sum()) if implied is not None else 0
        ratio = a_sum / pw.mean() if full and len(pw) else np.nan
        if pd.notna(ratio):
            ratios.append(ratio)
        rows.append((f"{y % 100:02d}/{(y + 1) % 100:02d}", pw.mean() if len(pw) else np.nan, len(pw), pw.max() if len(pw) else np.nan,
                     a_sum, ratio, e_sum, i_sum, i_n))
    avg_ratio = np.mean(ratios) if ratios else np.nan
    f = lambda v, d=0: "-" if v is None or pd.isna(v) else f"{v:,.{d}f}"
    head = ("<tr><th>Season</th><th>Apr-Sep pod load<br>(avg, months)</th><th>Peak pod load</th><th>Oct-Mar arrivals<br>actual, kt</th>"
            "<th>kt per pod</th><th>Ratio-implied<br>Oct-Mar, kt</th><th>Model-implied<br>Oct-Mar, kt</th><th>Forestero estimate<br>Oct-Mar, kt</th></tr>")
    body = ""
    for cy, pm, n, pk, a, r, e, i, i_n in rows:
        latest = cy == rows[-1][0]
        r_imp = pm * avg_ratio if latest and pd.isna(a) and pd.notna(pm) and pd.notna(avg_ratio) else np.nan
        i_txt = f"{f(i)} <span style='color:#7a86a8'>({i_n}/6 mo)</span>" if latest and pd.isna(a) and i_n else "-"
        body += (f"<tr><td class='cy'>{cy}</td><td>{f(pm, 1)} <span style='color:#7a86a8'>({n})</span></td><td>{f(pk, 1)}</td>"
                 f"<td class='tot'>{f(a)}</td><td>{f(r, 1)}</td><td>{f(r_imp)}</td><td>{i_txt}</td><td>{f(e) if latest and pd.isna(a) else '-'}</td></tr>")
    return (monthly.CSS + f"<div class='mt-wrap' style='display:inline-block;max-width:100%'><table class='mt' style='width:auto'>{head}{body}"
            f"</table></div>")


# ---------------------------------------------------------------------------------------------
# page
# ---------------------------------------------------------------------------------------------
def render():
    country = "IVC"                                       # Ivory Coast first: it has the port (ETG) arrivals
    c = st.columns([0.01, 2.6, 1.8, 3.6], vertical_alignment="center")
    sources = ["ETG (ports)", "Forestero Stat", "Forestero Tree"]
    with c[1]:
        source = st.radio("Arrivals", sources, horizontal=True, label_visibility="collapsed", key=f"st_src_{country}")
    p = pods(country)
    if source.startswith("ETG"):
        arr, running = etg_monthly()
        est, est_label = running, "ETG running month (projected)"
    else:
        arr, est = forestero("Ghana" if country == "GH" else "IVC", source.split()[-1])
        est_label = "Forestero estimate"
    lt = lag_table(p, arr)
    best = int(lt.loc[lt.pods.idxmax(), "lag"]) if lt.pods.notna().any() else 4
    with c[2]:
        lag = st.selectbox("Lag", list(range(MAX_LAG + 1)), index=best, key=f"st_lag_{country}_{source}", label_visibility="collapsed",
                           format_func=lambda k: f"Lag  |  {k} months" + ("  (best)" if k == best else ""))
    res = fit(p.pods, arr, lag)
    implied = None
    if res:
        a, b, r2, n, imp = res
        implied = imp[imp.index > arr.index.max()].dropna()
    with c[3]:
        if res:
            st.markdown(f"<div class='card-desc' style='margin:0'>arrivals = {a:,.0f} + {b:,.1f} x pod load (t-{lag}) &middot; "
                        f"R&sup2; {r2:.2f} &middot; {n} months</div>", unsafe_allow_html=True)

    name = "Ivory Coast"
    with st.container(border=True):
        st.markdown(f"<div class='card-title'>{name}: pods per tree (top) and arrivals (bottom)</div>"
                    "<div class='card-desc'>Shaded = Oct-Mar main-crop harvest. Hatched = arrivals implied by the pod load "
                    f"{lag} months earlier, for months not reported yet.</div>", unsafe_allow_html=True)
        st.plotly_chart(combined_chart(p, arr, est, implied, est_label, lag), width="stretch")
    left, right = st.columns(2)
    with left, st.container(border=True):
        st.markdown("<div class='card-title'>How far do pods lead arrivals?</div>"
                    "<div class='card-desc'>Correlation of monthly arrivals with the pod count k months earlier. "
                    f"Few seasons on file, so read it as a guide.</div>", unsafe_allow_html=True)
        st.plotly_chart(lag_chart(lt, best), width="stretch")
    with right, st.container(border=True):
        st.markdown(f"<div class='card-title'>Pods {lag} months earlier vs arrivals</div>"
                    "<div class='card-desc'>One dot per month, coloured by season; dashed = the fitted line.</div>", unsafe_allow_html=True)
        st.plotly_chart(scatter_chart(p.pods, arr, lag, res), width="stretch")
    with st.container(border=True):
        st.markdown("<div class='card-title'>Season view: survey ahead of the harvest</div>", unsafe_allow_html=True)
        st.markdown(season_table(p, arr, est if not source.startswith("ETG") else None, implied), unsafe_allow_html=True)
