"""방향성을 가정하지 않는 범주형 연관성 분석."""

from __future__ import annotations

from dataclasses import dataclass
from itertools import product
from math import sqrt
from typing import Any

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

from src.config import CONTEXT_LABELS, VARIABLE_COLUMNS, VARIABLE_PAIRS


class AnalysisUnavailable(ValueError):
    """표가 너무 작거나 비어 있어 검정할 수 없는 경우."""


@dataclass
class AssociationResult:
    variable_x: str
    variable_y: str
    n: int
    excluded_n: int
    observed: pd.DataFrame
    row_percent: pd.DataFrame
    column_percent: pd.DataFrame
    expected: pd.DataFrame
    adjusted_residuals: pd.DataFrame
    cell_p_raw: pd.DataFrame
    cell_p_holm: pd.DataFrame
    chi2: float
    dof: int
    p_value: float
    cramers_v: float
    expected_below_one: int
    expected_below_five: int
    expected_below_five_ratio: float
    expected_condition_ok: bool
    fisher_p_value: float | None = None

    @property
    def positive_significant_count(self) -> int:
        return int(((self.adjusted_residuals > 0) & (self.cell_p_holm < 0.05)).sum().sum())

    @property
    def negative_significant_count(self) -> int:
        return int(((self.adjusted_residuals < 0) & (self.cell_p_holm < 0.05)).sum().sum())


@dataclass
class ContextDifferenceResult:
    statistic: float
    dof: int
    p_value: float
    n: int
    converged: bool
    note: str = ""


def _sort_codes(values: pd.Series) -> list[str]:
    def key(value: str):
        text = str(value)
        prefix = "".join(ch for ch in text if not ch.isdigit())
        digits = "".join(ch for ch in text if ch.isdigit())
        return prefix, int(digits) if digits else -1, text

    return sorted(values.astype(str).unique().tolist(), key=key)


def adjusted_standardized_residuals(observed: np.ndarray, expected: np.ndarray) -> np.ndarray:
    observed = np.asarray(observed, dtype=float)
    expected = np.asarray(expected, dtype=float)
    total = observed.sum()
    row_proportions = observed.sum(axis=1, keepdims=True) / total
    column_proportions = observed.sum(axis=0, keepdims=True) / total
    denominator = np.sqrt(expected * (1 - row_proportions) * (1 - column_proportions))
    with np.errstate(divide="ignore", invalid="ignore"):
        residuals = np.divide(
            observed - expected,
            denominator,
            out=np.full_like(expected, np.nan),
            where=denominator > 0,
        )
    return residuals


def holm_adjust(p_values: np.ndarray) -> np.ndarray:
    flat = np.asarray(p_values, dtype=float).ravel()
    adjusted = np.full(flat.shape, np.nan)
    finite = np.isfinite(flat)
    if finite.any():
        adjusted[finite] = multipletests(flat[finite], method="holm")[1]
    return adjusted.reshape(np.asarray(p_values).shape)


def association_analysis(frame: pd.DataFrame, variable_x: str, variable_y: str) -> AssociationResult:
    if variable_x == variable_y:
        raise ValueError("서로 다른 두 변수를 선택해야 합니다.")
    x_column, y_column = VARIABLE_COLUMNS[variable_x], VARIABLE_COLUMNS[variable_y]
    x = frame[x_column].fillna("").astype(str).str.strip()
    y = frame[y_column].fillna("").astype(str).str.strip()
    valid = x.ne("") & y.ne("")
    used = pd.DataFrame({variable_x: x.loc[valid], variable_y: y.loc[valid]})
    if used.empty:
        raise AnalysisUnavailable("선택한 두 변수에 함께 사용할 수 있는 댓글이 없습니다.")

    x_order, y_order = _sort_codes(used[variable_x]), _sort_codes(used[variable_y])
    observed = pd.crosstab(used[variable_x], used[variable_y]).reindex(index=x_order, columns=y_order, fill_value=0)
    if observed.shape[0] < 2 or observed.shape[1] < 2:
        raise AnalysisUnavailable("각 변수에 관측된 범주가 두 개 이상이어야 카이제곱 검정을 계산할 수 있습니다.")

    chi2, p_value, dof, expected_array = stats.chi2_contingency(observed.to_numpy(), correction=False)
    n = int(observed.to_numpy().sum())
    expected = pd.DataFrame(expected_array, index=observed.index, columns=observed.columns)
    residual_array = adjusted_standardized_residuals(observed.to_numpy(), expected_array)
    cell_p_array = 2 * stats.norm.sf(np.abs(residual_array))
    cell_holm_array = holm_adjust(cell_p_array)
    residuals = pd.DataFrame(residual_array, index=observed.index, columns=observed.columns)
    cell_p = pd.DataFrame(cell_p_array, index=observed.index, columns=observed.columns)
    cell_holm = pd.DataFrame(cell_holm_array, index=observed.index, columns=observed.columns)

    denominator_dimension = min(observed.shape[0] - 1, observed.shape[1] - 1)
    cramers_v = sqrt(chi2 / (n * denominator_dimension)) if denominator_dimension > 0 else np.nan
    below_one = int((expected_array < 1).sum())
    below_five = int((expected_array < 5).sum())
    below_five_ratio = below_five / expected_array.size
    fisher_p = None
    if observed.shape == (2, 2):
        fisher_p = float(stats.fisher_exact(observed.to_numpy()).pvalue)

    return AssociationResult(
        variable_x=variable_x,
        variable_y=variable_y,
        n=n,
        excluded_n=int(len(frame) - n),
        observed=observed,
        row_percent=observed.div(observed.sum(axis=1), axis=0).mul(100),
        column_percent=observed.div(observed.sum(axis=0), axis=1).mul(100),
        expected=expected,
        adjusted_residuals=residuals,
        cell_p_raw=cell_p,
        cell_p_holm=cell_holm,
        chi2=float(chi2),
        dof=int(dof),
        p_value=float(p_value),
        cramers_v=float(cramers_v),
        expected_below_one=below_one,
        expected_below_five=below_five,
        expected_below_five_ratio=float(below_five_ratio),
        expected_condition_ok=below_one == 0 and below_five_ratio <= 0.20,
        fisher_p_value=fisher_p,
    )


def significant_cells(result: AssociationResult) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for x_code in result.observed.index:
        for y_code in result.observed.columns:
            residual = float(result.adjusted_residuals.loc[x_code, y_code])
            p_holm = float(result.cell_p_holm.loc[x_code, y_code])
            if p_holm < 0.05:
                rows.append(
                    {
                        "x_code": x_code,
                        "y_code": y_code,
                        "observed": int(result.observed.loc[x_code, y_code]),
                        "expected": float(result.expected.loc[x_code, y_code]),
                        "residual": residual,
                        "p_holm": p_holm,
                        "direction": "+" if residual > 0 else "-",
                    }
                )
    return pd.DataFrame(rows).sort_values("residual", ascending=False).reset_index(drop=True) if rows else pd.DataFrame(
        columns=["x_code", "y_code", "observed", "expected", "residual", "p_holm", "direction"]
    )


def _extreme_pair(result: AssociationResult, largest: bool) -> tuple[str, str, float]:
    array = result.adjusted_residuals.to_numpy()
    flat_index = np.nanargmax(array) if largest else np.nanargmin(array)
    row_index, column_index = np.unravel_index(flat_index, array.shape)
    return (
        str(result.adjusted_residuals.index[row_index]),
        str(result.adjusted_residuals.columns[column_index]),
        float(array[row_index, column_index]),
    )


def all_pair_summary(frame: pd.DataFrame) -> tuple[pd.DataFrame, dict[tuple[str, str], AssociationResult]]:
    rows: list[dict[str, Any]] = []
    results: dict[tuple[str, str], AssociationResult] = {}
    for variable_x, variable_y in VARIABLE_PAIRS:
        try:
            result = association_analysis(frame, variable_x, variable_y)
        except AnalysisUnavailable as exc:
            rows.append({"variable_x": variable_x, "variable_y": variable_y, "error": str(exc)})
            continue
        positive = _extreme_pair(result, True)
        negative = _extreme_pair(result, False)
        results[(variable_x, variable_y)] = result
        rows.append(
            {
                "variable_x": variable_x,
                "variable_y": variable_y,
                "n": result.n,
                "chi2": result.chi2,
                "dof": result.dof,
                "p_raw": result.p_value,
                "cramers_v": result.cramers_v,
                "top_positive": positive,
                "top_negative": negative,
                "expected_ok": result.expected_condition_ok,
                "error": "",
            }
        )
    summary = pd.DataFrame(rows)
    summary["p_holm"] = np.nan
    valid = summary["p_raw"].notna() if "p_raw" in summary else pd.Series(False, index=summary.index)
    if valid.any():
        summary.loc[valid, "p_holm"] = multipletests(summary.loc[valid, "p_raw"], method="holm")[1]
    summary["holm_significant"] = summary["p_holm"].lt(0.05)
    return summary, results


def context_comparison(frame: pd.DataFrame, variable_x: str, variable_y: str) -> tuple[pd.DataFrame, dict[str, AssociationResult]]:
    rows: list[dict[str, Any]] = []
    results: dict[str, AssociationResult] = {}
    for raw_context, display_context in CONTEXT_LABELS.items():
        subset = frame.loc[frame["cde_context"].eq(raw_context)]
        try:
            result = association_analysis(subset, variable_x, variable_y)
        except AnalysisUnavailable as exc:
            rows.append(
                {
                    "CDE 맥락": display_context,
                    "콘텐츠 수": int(subset["video_id"].nunique()),
                    "댓글 수 N": int(len(subset)),
                    "계산 상태": str(exc),
                }
            )
            continue
        results[raw_context] = result
        rows.append(
            {
                "CDE 맥락": display_context,
                "콘텐츠 수": int(subset["video_id"].nunique()),
                "댓글 수 N": result.n,
                "카이제곱": result.chi2,
                "자유도": result.dof,
                "p값": result.p_value,
                "Cramér’s V": result.cramers_v,
                "유의한 + 조합": result.positive_significant_count,
                "유의한 - 조합": result.negative_significant_count,
                "기대빈도 조건": "충족" if result.expected_condition_ok else "주의 필요",
                "계산 상태": "완료",
            }
        )
    return pd.DataFrame(rows), results


def _interaction_columns(left: np.ndarray, right: np.ndarray) -> np.ndarray:
    if left.shape[1] == 0 or right.shape[1] == 0:
        return np.empty((left.shape[0], 0))
    return np.column_stack([left[:, i] * right[:, j] for i in range(left.shape[1]) for j in range(right.shape[1])])


def loglinear_context_test(frame: pd.DataFrame, variable_x: str, variable_y: str) -> ContextDifferenceResult:
    """[XY][XCDE][YCDE] 대 포화모형의 우도비 검정."""
    import statsmodels.api as sm

    x_column, y_column = VARIABLE_COLUMNS[variable_x], VARIABLE_COLUMNS[variable_y]
    subset = frame[[x_column, y_column, "cde_context"]].copy()
    for column in subset.columns:
        subset[column] = subset[column].fillna("").astype(str).str.strip()
    subset = subset.loc[
        subset[x_column].ne("")
        & subset[y_column].ne("")
        & subset["cde_context"].isin(CONTEXT_LABELS)
    ]
    x_levels, y_levels = _sort_codes(subset[x_column]), _sort_codes(subset[y_column])
    context_levels = [context for context in CONTEXT_LABELS if context in set(subset["cde_context"])]
    if min(len(x_levels), len(y_levels), len(context_levels)) < 2:
        raise AnalysisUnavailable("각 차원에 관측된 범주가 두 개 이상이어야 합니다.")

    full_index = pd.MultiIndex.from_tuples(
        list(product(x_levels, y_levels, context_levels)), names=[x_column, y_column, "cde_context"]
    )
    counts = subset.groupby([x_column, y_column, "cde_context"]).size().reindex(full_index, fill_value=0)
    cells = counts.index.to_frame(index=False)
    x_dummy = pd.get_dummies(cells[x_column], drop_first=True, dtype=float).to_numpy()
    y_dummy = pd.get_dummies(cells[y_column], drop_first=True, dtype=float).to_numpy()
    c_dummy = pd.get_dummies(cells["cde_context"], drop_first=True, dtype=float).to_numpy()
    design = np.column_stack(
        [
            np.ones(len(cells)),
            x_dummy,
            y_dummy,
            c_dummy,
            _interaction_columns(x_dummy, y_dummy),
            _interaction_columns(x_dummy, c_dummy),
            _interaction_columns(y_dummy, c_dummy),
        ]
    )
    try:
        fitted = sm.GLM(counts.to_numpy(dtype=float), design, family=sm.families.Poisson()).fit(maxiter=200)
    except Exception as exc:
        raise AnalysisUnavailable(f"희소 셀 또는 모형 수렴 문제로 계산할 수 없습니다: {exc}") from exc
    statistic = float(fitted.deviance)
    dof = int((len(x_levels) - 1) * (len(y_levels) - 1) * (len(context_levels) - 1))
    if not np.isfinite(statistic) or not bool(getattr(fitted, "converged", True)):
        raise AnalysisUnavailable("희소 셀 또는 모형 수렴 문제로 계산할 수 없습니다.")
    return ContextDifferenceResult(
        statistic=statistic,
        dof=dof,
        p_value=float(stats.chi2.sf(statistic, dof)),
        n=int(counts.sum()),
        converged=True,
        note="동질적 연관성 모형 [XY][XCDE][YCDE]와 포화모형 [XYCDE] 비교",
    )
