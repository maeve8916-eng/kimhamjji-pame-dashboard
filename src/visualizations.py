"""Plotly 기반 학술 대시보드 시각화."""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from src.data_validator import code_label
from src.interpretation import format_p_value
from src.statistics import AssociationResult

BLUE = "#2F6F9F"
ORANGE = "#C56A2D"
GRID = "#D9DEE5"
TEXT = "#2C3138"


def residual_heatmap(result: AssociationResult, codebook_map: dict[str, dict[str, str]]) -> go.Figure:
    residuals = result.adjusted_residuals.to_numpy(dtype=float)
    p_holm = result.cell_p_holm.to_numpy(dtype=float)
    significant = p_holm < 0.05
    display_values = np.where(significant, residuals, residuals * 0.18)
    max_abs = max(2.0, float(np.nanmax(np.abs(residuals))))
    signs = np.where(significant & (residuals > 0), "+", np.where(significant & (residuals < 0), "-", ""))

    custom = np.empty(residuals.shape + (5,), dtype=object)
    custom[:, :, 0] = result.observed.to_numpy()
    custom[:, :, 1] = result.expected.to_numpy()
    custom[:, :, 2] = residuals
    custom[:, :, 3] = p_holm
    for i, x_code in enumerate(result.observed.index):
        for j, y_code in enumerate(result.observed.columns):
            custom[i, j, 4] = f"{x_code} × {y_code}"

    figure = go.Figure(
        go.Heatmap(
            z=display_values,
            x=[code_label(code, codebook_map) for code in result.observed.columns],
            y=[code_label(code, codebook_map) for code in result.observed.index],
            zmin=-max_abs,
            zmax=max_abs,
            zmid=0,
            colorscale=[[0, ORANGE], [0.5, "#F5F6F8"], [1, BLUE]],
            text=signs,
            texttemplate="<b>%{text}</b>",
            textfont={"size": 22},
            customdata=custom,
            hovertemplate=(
                "<b>%{customdata[4]}</b><br>관측빈도 %{customdata[0]:,.0f}<br>"
                "기대빈도 %{customdata[1]:,.2f}<br>조정 잔차 %{customdata[2]:.2f}<br>"
                "Holm 보정 p값 %{customdata[3]:.4f}<extra></extra>"
            ),
            colorbar={"title": "조정 잔차"},
        )
    )
    figure.update_layout(
        height=max(380, 92 * len(result.observed.index)),
        margin={"l": 20, "r": 20, "t": 20, "b": 20},
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"color": TEXT},
        xaxis={"title": "", "side": "bottom", "tickangle": -18, "showgrid": False},
        yaxis={"title": "", "autorange": "reversed", "showgrid": False},
    )
    return figure


def context_cramers_bar(comparison_frame) -> go.Figure:
    if "Cramér’s V" not in comparison_frame:
        return go.Figure()
    usable = comparison_frame.loc[comparison_frame["Cramér’s V"].notna()].copy()
    figure = go.Figure(
        go.Bar(
            x=usable["CDE 맥락"],
            y=usable["Cramér’s V"],
            marker_color=BLUE,
            text=usable["Cramér’s V"].map(lambda value: f"{value:.3f}"),
            textposition="outside",
            hovertemplate="%{x}<br>Cramér’s V %{y:.3f}<extra></extra>",
        )
    )
    figure.update_layout(
        height=390,
        margin={"l": 20, "r": 20, "t": 30, "b": 90},
        paper_bgcolor="white",
        plot_bgcolor="white",
        font={"color": TEXT},
        xaxis={"title": "", "tickangle": -15},
        yaxis={"title": "Cramér’s V", "rangemode": "tozero", "gridcolor": GRID},
        showlegend=False,
    )
    return figure
