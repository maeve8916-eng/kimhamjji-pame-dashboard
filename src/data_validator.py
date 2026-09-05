"""원자료를 변경하지 않는 검증·정규화 계층."""

from __future__ import annotations

from dataclasses import dataclass
from hashlib import sha256
from typing import Any

import pandas as pd

from src.config import (
    CODEBOOK_COLUMNS,
    COMMENT_COLUMNS,
    CONTENT_COLUMNS,
    CONTEXT_LABELS,
    VARIABLE_COLUMNS,
)


class DataValidationError(ValueError):
    """필수 구조가 없어 안전하게 분석할 수 없을 때 발생."""


@dataclass
class PreparedData:
    contents: pd.DataFrame
    comments: pd.DataFrame
    analysis_comments: pd.DataFrame
    codebook: pd.DataFrame
    codebook_map: dict[str, dict[str, str]]
    quality: dict[str, Any]


def _clean_headers(frame: pd.DataFrame) -> pd.DataFrame:
    cleaned = frame.copy()
    cleaned.columns = [str(value).strip() for value in cleaned.columns]
    return cleaned


def _require_headers(frame: pd.DataFrame, required: list[str], source_name: str) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise DataValidationError(f"{source_name}에 필수 헤더가 없습니다: {', '.join(missing)}")


def _text(series: pd.Series) -> pd.Series:
    return series.fillna("").astype(str).str.strip()


def _fallback_comment_ids(comments: pd.DataFrame, blank_mask: pd.Series) -> pd.Series:
    signatures = comments[["video_id", "댓글 작성자", "댓글 내용", "댓글 작성일"]].fillna("").astype(str)
    base_hashes = signatures.apply(
        lambda row: sha256("\u241f".join(row.tolist()).encode("utf-8")).hexdigest(), axis=1
    )
    duplicate_ordinals = base_hashes.groupby(base_hashes).cumcount().add(1)
    generated = "fallback-" + base_hashes + "-" + duplicate_ordinals.astype(str)
    result = _text(comments["comment_id"])
    result.loc[blank_mask] = generated.loc[blank_mask]
    return result


def prepare_data(contents: pd.DataFrame, comments: pd.DataFrame, codebook: pd.DataFrame) -> PreparedData:
    contents = _clean_headers(contents)
    comments = _clean_headers(comments)
    codebook = _clean_headers(codebook)
    _require_headers(contents, CONTENT_COLUMNS, "콘텐츠 탭")
    _require_headers(comments, COMMENT_COLUMNS, "댓글 탭")
    _require_headers(codebook, CODEBOOK_COLUMNS, "코드 정의 범위")

    contents = contents[CONTENT_COLUMNS].copy()
    comments = comments[COMMENT_COLUMNS].copy()
    codebook = codebook[CODEBOOK_COLUMNS].copy()
    for column in CONTENT_COLUMNS:
        contents[column] = _text(contents[column])
    for column in ["variable", "code", "label", "definition"]:
        codebook[column] = _text(codebook[column])
    codebook = codebook.loc[codebook["code"].ne("")].reset_index(drop=True)

    comments["_source_order"] = range(len(comments))
    for column in COMMENT_COLUMNS:
        if column not in ("댓글 좋아요 수",):
            comments[column] = _text(comments[column])

    original_ids = _text(comments["comment_id"])
    blank_id_mask = original_ids.eq("")
    duplicate_original_mask = original_ids.ne("") & original_ids.duplicated(keep=False)
    comments["comment_id_was_fallback"] = blank_id_mask
    comments["comment_id"] = _fallback_comment_ids(comments, blank_id_mask)
    duplicate_ordinal = comments.groupby("comment_id").cumcount().add(1)
    comments["comment_key"] = comments["comment_id"]
    duplicate_after_fill = comments["comment_id"].duplicated(keep=False)
    comments.loc[duplicate_after_fill, "comment_key"] = (
        comments.loc[duplicate_after_fill, "comment_id"]
        + "#dup-"
        + duplicate_ordinal.loc[duplicate_after_fill].astype(str)
    )

    like_raw = _text(comments["댓글 좋아요 수"])
    comments["댓글 좋아요 수"] = pd.to_numeric(like_raw.str.replace(",", "", regex=False), errors="coerce")
    like_failures = int((like_raw.ne("") & comments["댓글 좋아요 수"].isna()).sum())
    date_raw = _text(comments["댓글 작성일"])
    comments["댓글 작성일"] = pd.to_datetime(date_raw, errors="coerce")
    date_failures = int((date_raw.ne("") & comments["댓글 작성일"].isna()).sum())

    content_duplicate_mask = contents["video_id"].ne("") & contents["video_id"].duplicated(keep=False)
    content_unique = contents.drop_duplicates("video_id", keep="first")
    merged = comments.merge(
        content_unique[["video_id", "제목", "cde_context"]],
        on="video_id",
        how="left",
        validate="many_to_one",
        indicator=True,
    )
    merged["cde_label"] = merged["cde_context"].map(CONTEXT_LABELS)
    analysis_comments = merged.loc[merged["cde_context"].isin(CONTEXT_LABELS)].copy()

    codebook_map = {
        row.code: {"variable": row.variable, "label": row.label, "definition": row.definition}
        for row in codebook.itertuples(index=False)
    }
    blank_codes: dict[str, int] = {}
    unknown_codes: dict[str, list[str]] = {}
    code_columns = {**VARIABLE_COLUMNS, "O": "O_code"}
    for variable, column in code_columns.items():
        values = _text(merged[column])
        if variable in VARIABLE_COLUMNS:
            blank_codes[variable] = int(values.eq("").sum())
        known = set(codebook.loc[codebook["variable"].eq(variable), "code"])
        unknown_codes[variable] = sorted(set(values.loc[values.ne("")]) - known)

    exact_subset = ["video_id", "댓글 작성자", "댓글 내용", "댓글 작성일"]
    exact_duplicate_rows = int(merged.duplicated(exact_subset, keep=False).sum())
    exact_duplicate_extra = int(merged.duplicated(exact_subset, keep="first").sum())
    context_content_counts = {
        label: int(contents["cde_context"].eq(raw).sum()) for raw, label in CONTEXT_LABELS.items()
    }
    context_comment_counts = {
        label: int(merged["cde_context"].eq(raw).sum()) for raw, label in CONTEXT_LABELS.items()
    }
    quality: dict[str, Any] = {
        "total_contents": int(len(contents)),
        "total_comments": int(len(comments)),
        "analysis_contents": int(contents["cde_context"].isin(CONTEXT_LABELS).sum()),
        "analysis_comments": int(len(analysis_comments)),
        "excluded_contents": int((~contents["cde_context"].isin(CONTEXT_LABELS)).sum()),
        "excluded_comments": int(len(comments) - len(analysis_comments)),
        "content_video_id_duplicates": int(content_duplicate_mask.sum()),
        "unmatched_comments": int(merged["_merge"].eq("left_only").sum()),
        "blank_comment_ids": int(blank_id_mask.sum()),
        "invalid_comment_ids": 0,
        "fallback_comment_ids": int(blank_id_mask.sum()),
        "duplicate_comment_id_rows": int(duplicate_original_mask.sum()),
        "blank_codes": blank_codes,
        "unknown_codes": unknown_codes,
        "like_conversion_failures": like_failures,
        "date_conversion_failures": date_failures,
        "exact_duplicate_rows": exact_duplicate_rows,
        "exact_duplicate_extra_rows": exact_duplicate_extra,
        "context_content_counts": context_content_counts,
        "context_comment_counts": context_comment_counts,
    }
    return PreparedData(contents, merged, analysis_comments, codebook, codebook_map, quality)


def code_label(code: str, codebook_map: dict[str, dict[str, str]]) -> str:
    entry = codebook_map.get(str(code), {})
    label = entry.get("label")
    return f"{label}({code})" if label else str(code)


def filter_comments(
    frame: pd.DataFrame,
    *,
    x_column: str | None = None,
    x_code: str | None = None,
    y_column: str | None = None,
    y_code: str | None = None,
    context: str | None = None,
    titles: list[str] | None = None,
    keyword: str = "",
    minimum_likes: float = 0,
    start_date=None,
    end_date=None,
    sort_by: str = "원본 데이터 순",
) -> pd.DataFrame:
    filtered = frame.copy()
    if x_column and x_code is not None:
        filtered = filtered.loc[filtered[x_column].eq(x_code)]
    if y_column and y_code is not None:
        filtered = filtered.loc[filtered[y_column].eq(y_code)]
    if context:
        filtered = filtered.loc[filtered["cde_context"].eq(context)]
    if titles:
        filtered = filtered.loc[filtered["제목"].isin(titles)]
    if keyword.strip():
        filtered = filtered.loc[
            filtered["댓글 내용"].fillna("").str.contains(keyword.strip(), case=False, regex=False)
        ]
    filtered = filtered.loc[filtered["댓글 좋아요 수"].fillna(0).ge(minimum_likes)]
    if start_date is not None:
        filtered = filtered.loc[filtered["댓글 작성일"].dt.date.ge(start_date)]
    if end_date is not None:
        filtered = filtered.loc[filtered["댓글 작성일"].dt.date.le(end_date)]
    if sort_by == "좋아요 많은 순":
        filtered = filtered.sort_values(["댓글 좋아요 수", "_source_order"], ascending=[False, True])
    elif sort_by == "최신순":
        filtered = filtered.sort_values(["댓글 작성일", "_source_order"], ascending=[False, True])
    elif sort_by == "무작위":
        filtered = filtered.sample(frac=1, random_state=20260905)
    else:
        filtered = filtered.sort_values("_source_order")
    return filtered.reset_index(drop=True)
