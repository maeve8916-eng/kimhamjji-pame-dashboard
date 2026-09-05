import pandas as pd

from src.data_validator import prepare_data
from src.interpretation import (
    FORBIDDEN_CAUSAL_EXPRESSIONS,
    contains_causal_expression,
    format_p_value,
    full_interpretation,
)
from src.statistics import association_analysis


def test_p_value_format():
    assert format_p_value(0.0002) == "p < .001"
    assert format_p_value(0.01234) == "p = .012"
    assert "0.000" not in format_p_value(0.0)


def test_generated_interpretation_has_no_causal_claims(codebook_frame):
    rows = []
    for p_code, m_code, count in [("P1", "M0", 60), ("P1", "M1", 5), ("P3", "M0", 5), ("P3", "M1", 60)]:
        rows.extend({"P_code": p_code, "M_code": m_code} for _ in range(count))
    result = association_analysis(pd.DataFrame(rows), "P", "M")
    codebook_map = {
        row.code: {"variable": row.variable, "label": row.label, "definition": row.definition}
        for row in codebook_frame.itertuples(index=False)
    }
    text = full_interpretation(result, codebook_map)
    assert not contains_causal_expression(text)
    assert all(expression not in text for expression in FORBIDDEN_CAUSAL_EXPRESSIONS)
    assert "동일한 댓글" in text
    assert "Cramér’s V" in text

