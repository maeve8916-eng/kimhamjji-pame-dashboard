"""코드북 기반 규칙형 한국어 해석."""

from __future__ import annotations

import math

from src.config import VARIABLE_NAMES
from src.data_validator import code_label
from src.statistics import AssociationResult, ContextDifferenceResult, significant_cells

FORBIDDEN_CAUSAL_EXPRESSIONS = (
    "영향을 미쳤다",
    "증가시켰다",
    "발생시켰다",
    "원인이 되었다",
    "효과가 입증되었다",
)


def _with_and_particle(word: str) -> str:
    """받침이 있으면 '과', 없으면 '와'를 붙인다."""
    if not word:
        return word
    last = ord(word[-1])
    has_final = 0xAC00 <= last <= 0xD7A3 and (last - 0xAC00) % 28 != 0
    return word + ("과" if has_final else "와")


def format_p_value(value: float, include_symbol: bool = True) -> str:
    if value is None or not math.isfinite(float(value)):
        return "계산 불가"
    prefix = "p " if include_symbol else ""
    if value < 0.001:
        return f"{prefix}< .001"
    formatted = f"{float(value):.3f}"
    if formatted.startswith("0"):
        formatted = formatted[1:]
    return f"{prefix}= {formatted}"


def overall_interpretation(result: AssociationResult) -> str:
    x_name = VARIABLE_NAMES[result.variable_x]
    y_name = VARIABLE_NAMES[result.variable_y]
    if result.p_value < 0.05:
        return (
            f"{_with_and_particle(x_name)} {y_name} 간에는 통계적으로 유의한 연관성이 확인되었다"
            f"({format_p_value(result.p_value)}). 관계의 크기를 나타내는 Cramér’s V는 "
            f"{result.cramers_v:.3f}였다. 분석 표본은 {result.n:,}개 댓글이며, "
            f"결측으로 제외된 댓글은 {result.excluded_n:,}개였다."
        )
    return (
        f"{_with_and_particle(x_name)} {y_name} 간에 통계적으로 유의한 연관성이 있다는 근거는 확인되지 않았다"
        f"({format_p_value(result.p_value)}). Cramér’s V는 {result.cramers_v:.3f}였고, "
        f"분석 표본은 {result.n:,}개 댓글이었다."
    )


def cell_interpretations(
    result: AssociationResult,
    codebook_map: dict[str, dict[str, str]],
    limit: int | None = None,
) -> list[str]:
    cells = significant_cells(result)
    if limit is not None:
        cells = cells.iloc[:limit]
    sentences: list[str] = []
    for row in cells.itertuples(index=False):
        x_label = code_label(row.x_code, codebook_map).rsplit("(", 1)[0]
        y_label = code_label(row.y_code, codebook_map).rsplit("(", 1)[0]
        relation = "빈번하게" if row.direction == "+" else "적게"
        sentences.append(
            f"{x_label} 반응과 {y_label}은 동일한 댓글에서 통계적 기대보다 {relation} 함께 나타났다"
            f"({row.direction}, 조정 잔차 {row.residual:.2f}, Holm 보정 {format_p_value(row.p_holm)})."
        )
    return sentences


def full_interpretation(result: AssociationResult, codebook_map: dict[str, dict[str, str]]) -> str:
    sentences = [overall_interpretation(result)]
    cells = cell_interpretations(result, codebook_map)
    if cells:
        sentences.append("\n".join(cells))
    else:
        sentences.append("셀별 Holm 보정 기준에서 유의한 코드 조합은 확인되지 않았다.")
    sentences.append(
        "이 결과는 관찰자료의 방향성 없는 연관성을 나타내며 인과관계를 뜻하지 않는다. "
        "표본이 크므로 p값과 함께 Cramér’s V 및 구체적인 코드 조합을 살펴봐야 한다."
    )
    return "\n\n".join(sentences)


def context_difference_interpretation(result: ContextDifferenceResult) -> str:
    if result.p_value < 0.05:
        return (
            "선택된 두 변수의 연관성 양상은 네 가지 콘텐츠 맥락에 따라 통계적으로 다르게 나타났다"
            f"(우도비 통계량 {result.statistic:.2f}, 자유도 {result.dof}, {format_p_value(result.p_value)})."
        )
    return (
        "선택된 두 변수의 연관성 양상이 콘텐츠 맥락에 따라 다르다는 통계적 근거는 확인되지 않았다"
        f"(우도비 통계량 {result.statistic:.2f}, 자유도 {result.dof}, {format_p_value(result.p_value)})."
    )


def contains_causal_expression(text: str) -> bool:
    return any(expression in text for expression in FORBIDDEN_CAUSAL_EXPRESSIONS)
