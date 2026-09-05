import numpy as np
import pandas as pd
import pytest
from scipy import stats
from statsmodels.stats.multitest import multipletests

from src.statistics import (
    adjusted_standardized_residuals,
    association_analysis,
    holm_adjust,
    loglinear_context_test,
)


def frame_from_table(table):
    rows = []
    for i, p_code in enumerate(["P1", "P2"]):
        for j, m_code in enumerate(["M0", "M1"]):
            rows.extend({"P_code": p_code, "M_code": m_code} for _ in range(table[i][j]))
    return pd.DataFrame(rows)


def test_chi_square_and_cramers_v_match_scipy():
    observed = np.array([[20, 10], [5, 15]])
    frame = frame_from_table(observed)
    result = association_analysis(frame, "P", "M")
    chi2, p_value, dof, _ = stats.chi2_contingency(observed, correction=False)
    assert result.chi2 == pytest.approx(chi2)
    assert result.p_value == pytest.approx(p_value)
    assert result.dof == dof
    assert result.cramers_v == pytest.approx(np.sqrt(chi2 / observed.sum()))


def test_adjusted_residual_formula():
    observed = np.array([[20, 10], [5, 15]], dtype=float)
    _, _, _, expected = stats.chi2_contingency(observed, correction=False)
    calculated = adjusted_standardized_residuals(observed, expected)
    row_p = observed.sum(axis=1, keepdims=True) / observed.sum()
    col_p = observed.sum(axis=0, keepdims=True) / observed.sum()
    manual = (observed - expected) / np.sqrt(expected * (1 - row_p) * (1 - col_p))
    np.testing.assert_allclose(calculated, manual)


def test_holm_adjustment_matches_statsmodels():
    values = np.array([[0.001, 0.02], [0.04, 0.5]])
    expected = multipletests(values.ravel(), method="holm")[1].reshape(values.shape)
    np.testing.assert_allclose(holm_adjust(values), expected)


def test_zero_codes_are_valid_categories():
    frame = pd.DataFrame(
        {
            "A_code": ["A0", "A0", "A1", "A1", ""],
            "M_code": ["M0", "M1", "M0", "M1", "M0"],
        }
    )
    result = association_analysis(frame, "A", "M")
    assert result.n == 4
    assert "A0" in result.observed.index
    assert "M0" in result.observed.columns
    assert result.excluded_n == 1


def test_loglinear_context_interaction_detects_large_difference():
    rows = []
    tables = {
        "과업–타인 부정정서형": [[90, 10], [10, 90]],
        "관계–타인 부정정서형": [[10, 90], [90, 10]],
        "개인상황–자기 부정정서형": [[85, 15], [15, 85]],
        "개인상황–자기 긍정정서형": [[15, 85], [85, 15]],
    }
    for context, table in tables.items():
        for i, p_code in enumerate(["P1", "P2"]):
            for j, m_code in enumerate(["M0", "M1"]):
                rows.extend(
                    {"P_code": p_code, "M_code": m_code, "cde_context": context}
                    for _ in range(table[i][j])
                )
    result = loglinear_context_test(pd.DataFrame(rows), "P", "M")
    assert result.converged
    assert result.dof == 3
    assert result.p_value < 0.001
