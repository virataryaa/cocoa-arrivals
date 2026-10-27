import plotly.graph_objects as go

import theme

# Validated categorical slots (dark-mode steps) from the dataviz reference palette.
SERIES = {
    "blue": "#3987e5",
    "green": "#008300",
    "magenta": "#d55181",
    "yellow": "#c98500",
    "aqua": "#199e70",
    "orange": "#d95926",
    "violet": "#9085e9",
    "red": "#e66767",
}
GOOD = "#006300"
CRITICAL = "#d03b3b"
MUTED = "#898781"
GRID = "#e1e0d9"
INK = "#0b0b0b"
SURFACE = "#fcfcfb"
NAVY_SOFT = "#3d5d85"


def _layout(title, height=None):
    # Legend y is a fraction of the plot's own domain height (height minus
    # margins), not a fixed pixel offset — a constant fraction like -0.3 puts
    # the legend a tiny gap below short charts but a huge gap below tall ones.
    # Solve for the fraction that yields a constant ~40px visual gap instead.
    margin = dict(l=50, r=20, t=50, b=100)
    if height:
        domain_h = max(height - margin["t"] - margin["b"], 50)
        legend_y = -40.0 / domain_h
    else:
        legend_y = -0.3
    layout = dict(
        title=dict(text=title, x=0.01, xanchor="left", y=0.97, yanchor="top",
                   font=dict(size=15)),
        paper_bgcolor=SURFACE,
        plot_bgcolor=SURFACE,
        font=dict(color=INK, family="system-ui, -apple-system, Segoe UI, sans-serif"),
        margin=margin,
        legend=dict(orientation="h", yanchor="top", y=legend_y, xanchor="left", x=0,
                    bgcolor="rgba(0,0,0,0)"),
        xaxis=dict(gridcolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED)),
        yaxis=dict(gridcolor=GRID, linecolor=GRID, tickfont=dict(color=MUTED),
                   tickformat=",.1f"),
    )
    if height:
        layout["height"] = height
    return layout


# ColorBrewer "Set1" — a categorical palette specifically validated for
# maximum perceptual distinctness between adjacent slots (unlike the SERIES
# dict above, where blue/violet and green/aqua read as near-identical hues
# at thin line widths). Yellow omitted: too low-contrast on a white background.
YEAR_PALETTE = ["#e41a1c", "#377eb8", "#4daf4a", "#ff7f00", "#984ea3", "#f781bf", "#a65628"]


def _recent_year_cols(year_cols, n=6):
    return year_cols[-n:]


def _shown_years_with_lta(year_cols, n):
    """Like _recent_year_cols, but keeps LTA pinned in view even once there
    are more real crop years than fit in the window (a plain last-N slice
    would eventually push LTA — the oldest column — out of frame)."""
    if "LTA" in year_cols:
        others = [y for y in year_cols if y != "LTA"]
        return ["LTA"] + others[-(n - 1):]
    return year_cols[-n:]


def _cumulative(df_wide, year_cols):
    cum = df_wide[year_cols].cumsum(skipna=True)
    return cum


def _projection_trace_xy(periods, actual_series, proj_vals, cumulative_base=None):
    """Builds the (x, y) for a dotted projection line that starts at the
    last actual data point and continues through proj_vals for whichever
    trailing periods it covers. If cumulative_base is given, y accumulates
    (running sum) instead of using proj_vals directly."""
    last_pos = actual_series.last_valid_index()
    if last_pos is None:
        return None, None
    x = [periods[last_pos]]
    running = cumulative_base[last_pos] if cumulative_base is not None else actual_series.iloc[last_pos]
    y = [running]
    for i in range(last_pos + 1, len(periods)):
        p = periods[i]
        if p not in proj_vals:
            break
        if cumulative_base is not None:
            running = running + proj_vals[p]
            y.append(running)
        else:
            y.append(proj_vals[p])
        x.append(p)
    if len(x) < 2:
        return None, None
    return x, y


def monthly_comparison(df_wide, year_cols, title="Monthly Comparison", height=None, proj_vals=None):
    periods = df_wide["Period"].tolist()
    shown_years = _shown_years_with_lta(year_cols, 6)
    color_idx = 0
    fig = go.Figure()
    for i, yr in enumerate(shown_years):
        is_lta = yr == "LTA"
        is_last = (not is_lta) and i == len(shown_years) - 1
        if not is_lta and not is_last:
            color = YEAR_PALETTE[color_idx % len(YEAR_PALETTE)]
            color_idx += 1
        else:
            color = None
        fig.add_trace(go.Scatter(
            x=periods, y=df_wide[yr],
            mode="lines+markers" if (is_last or is_lta) else "lines",
            name=yr, connectgaps=True,
            line=dict(width=2 if is_lta else (4 if is_last else 2),
                       color=MUTED if is_lta else (INK if is_last else color),
                       dash="dot" if is_lta else "solid"),
            marker=(dict(size=6, symbol="diamond-open", color=MUTED) if is_lta
                    else dict(size=7, color=INK) if is_last else dict(size=0)),
        ))
    if proj_vals:
        current_year = year_cols[-1]
        x, y = _projection_trace_xy(periods, df_wide[current_year], proj_vals)
        if x:
            fig.add_trace(go.Scatter(
                x=x, y=y, name=f"{current_year} (proj)", mode="lines+markers",
                line=dict(width=2, color=INK, dash="dot"),
                marker=dict(size=6, symbol="circle-open", color=INK),
            ))
    fig.update_layout(**_layout(title, height))
    return theme.style(fig)


def cumulative_forecast(df_wide, year_cols, title="Cumulative (to date)", height=None, proj_vals=None):
    periods = df_wide["Period"].tolist()
    cum = _cumulative(df_wide, year_cols)
    shown_years = _shown_years_with_lta(year_cols, 7)
    color_idx = 0
    fig = go.Figure()
    for i, yr in enumerate(shown_years):
        is_lta = yr == "LTA"
        is_last = (not is_lta) and i == len(shown_years) - 1
        if not is_lta and not is_last:
            color = YEAR_PALETTE[color_idx % len(YEAR_PALETTE)]
            color_idx += 1
        else:
            color = None
        fig.add_trace(go.Scatter(
            x=periods, y=cum[yr],
            mode="lines",
            name=yr, connectgaps=True,
            line=dict(width=2 if is_lta else (4 if is_last else 2),
                       color=MUTED if is_lta else (INK if is_last else color),
                       dash="dot" if is_lta else "solid"),
        ))
    if proj_vals:
        current_year = year_cols[-1]
        x, y = _projection_trace_xy(periods, df_wide[current_year], proj_vals,
                                     cumulative_base=cum[current_year])
        if x:
            fig.add_trace(go.Scatter(
                x=x, y=y, name=f"{current_year} (proj)", mode="lines+markers",
                line=dict(width=2, color=INK, dash="dot"),
                marker=dict(size=6, symbol="circle-open", color=INK),
            ))
    fig.update_layout(**_layout(title, height))
    return theme.style(fig)


