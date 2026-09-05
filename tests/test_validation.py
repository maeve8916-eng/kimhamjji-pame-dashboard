import pandas as pd
import pytest

from src.data_validator import DataValidationError, filter_comments, prepare_data


def test_required_header_validation(content_frame, comment_frame, codebook_frame):
    with pytest.raises(DataValidationError, match="댓글 내용"):
        prepare_data(content_frame, comment_frame.drop(columns=["댓글 내용"]), codebook_frame)


def test_fallback_ids_are_hash_based_unique_and_stable(content_frame, comment_frame, codebook_frame):
    first = prepare_data(content_frame, comment_frame, codebook_frame)
    second = prepare_data(content_frame, comment_frame, codebook_frame)
    generated_first = first.comments.loc[first.comments["comment_id_was_fallback"], "comment_id"].tolist()
    generated_second = second.comments.loc[second.comments["comment_id_was_fallback"], "comment_id"].tolist()
    assert generated_first == generated_second
    assert len(generated_first) == len(set(generated_first))
    assert all(value.startswith("fallback-") for value in generated_first)
    assert first.quality["fallback_comment_ids"] == 2


def test_context_merge_and_filter(content_frame, comment_frame, codebook_frame):
    prepared = prepare_data(content_frame, comment_frame, codebook_frame)
    assert len(prepared.analysis_comments) == 4
    assert prepared.quality["excluded_comments"] == 1
    assert prepared.quality["unmatched_comments"] == 0
    assert prepared.quality["blank_codes"]["A"] == 0


def test_exact_duplicate_detection(content_frame, comment_frame, codebook_frame):
    prepared = prepare_data(content_frame, comment_frame, codebook_frame)
    assert prepared.quality["exact_duplicate_rows"] == 2
    assert prepared.quality["exact_duplicate_extra_rows"] == 1


def test_comment_filters(content_frame, comment_frame, codebook_frame):
    prepared = prepare_data(content_frame, comment_frame, codebook_frame)
    filtered = filter_comments(
        prepared.analysis_comments,
        x_column="P_code",
        x_code="P1",
        y_column="M_code",
        y_code="M0",
        keyword="댓글",
        minimum_likes=5,
        sort_by="좋아요 많은 순",
    )
    assert filtered["comment_id"].tolist() == ["1"]

