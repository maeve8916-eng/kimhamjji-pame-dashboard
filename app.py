"""김햄찌 PAME 연관성 탐색기 Streamlit 애플리케이션."""

from __future__ import annotations

import math
import os
from datetime import date

import numpy as np
import pandas as pd
import streamlit as st

from src.config import CONTEXT_LABELS, VARIABLE_COLUMNS, VARIABLE_NAMES, VARIABLE_PAIRS
from src.data_loader import DataSourceError, clear_data_cache, load_sheet_frames
from src.data_validator import DataValidationError, code_label, filter_comments, prepare_data
from src.interpretation import (
    context_difference_interpretation,
    format_p_value,
    full_interpretation,
)
from src.statistics import (
    AnalysisUnavailable,
    all_pair_summary,
    association_analysis,
    context_comparison,
    loglinear_context_test,
    significant_cells,
)
from src.visualizations import context_cramers_bar, residual_heatmap

st.set_page_config(
    page_title="김햄찌 PAME 연관성 탐색기",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    :root { --plus: #2f6f9f; --minus: #c56a2d; --ink: #2c3138; --muted: #66717e; }
    .stApp { background: #f7f8fa; color: var(--ink); }
    [data-testid="stHeader"] { background: rgba(247,248,250,.92); }
    h1, h2, h3 { letter-spacing: -0.025em; color: #20252b; }
    div[data-testid="stMetric"] { background: white; border: 1px solid #e1e5ea; padding: 14px 16px; border-radius: 8px; }
    div[data-testid="stMetricLabel"] { color: var(--muted); }
    .plus { color: var(--plus); font-weight: 700; }
    .minus { color: var(--minus); font-weight: 700; }
    .context-note { border-left: 3px solid #7a8795; padding: .2rem 0 .2rem .85rem; color: var(--muted); }
    .comment-meta { color: var(--muted); font-size: .88rem; }
    .block-container { padding-top: 2.2rem; padding-bottom: 4rem; }
    button[kind="secondary"] { border-color: #ccd3da; }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(show_spinner=False)
def cached_association(frame: pd.DataFrame, variable_x: str, variable_y: str):
    return association_analysis(frame, variable_x, variable_y)


@st.cache_data(show_spinner=False)
def cached_pair_summary(frame: pd.DataFrame):
    return all_pair_summary(frame)


@st.cache_data(show_spinner=False)
def cached_context_comparison(frame: pd.DataFrame, variable_x: str, variable_y: str):
    return context_comparison(frame, variable_x, variable_y)


@st.cache_data(show_spinner=False)
def cached_loglinear(frame: pd.DataFrame, variable_x: str, variable_y: str):
    return loglinear_context_test(frame, variable_x, variable_y)


def variable_display(variable: str) -> str:
    return f"{VARIABLE_NAMES[variable]} ({variable})"


def display_table(result, view: str, codebook_map):
    tables = {
        "관측빈도": result.observed,
        "행 백분율": result.row_percent,
        "열 백분율": result.column_percent,
        "기대빈도": result.expected,
        "조정 표준화 잔차": result.adjusted_residuals,
    }
    table = tables[view].copy()
    table.index = [code_label(code, codebook_map) for code in table.index]
    table.columns = [code_label(code, codebook_map) for code in table.columns]
    if view in ("행 백분율", "열 백분율"):
        return table.map(lambda value: f"{value:.1f}%")
    if view == "관측빈도":
        return table.astype(int)
    return table.round(2)


def display_significant_table(result, codebook_map):
    cells = significant_cells(result)
    if cells.empty:
        st.info("셀별 Holm 보정 기준에서 유의한 코드 조합이 없습니다.")
        return
    display = pd.DataFrame(
        {
            VARIABLE_NAMES[result.variable_x]: cells["x_code"].map(lambda code: code_label(code, codebook_map)),
            VARIABLE_NAMES[result.variable_y]: cells["y_code"].map(lambda code: code_label(code, codebook_map)),
            "방향": cells["direction"].map({"+": "+ 기대보다 많음", "-": "- 기대보다 적음"}),
            "관측빈도": cells["observed"],
            "기대빈도": cells["expected"].round(2),
            "조정 잔차": cells["residual"].round(2),
            "Holm 보정 p값": cells["p_holm"].map(lambda value: format_p_value(value, include_symbol=False)),
        }
    )
    st.dataframe(display, hide_index=True, width="stretch")


def choose_pair(variable_x: str, variable_y: str) -> None:
    st.session_state["pame_x"] = variable_x
    st.session_state["pame_y"] = variable_y
    st.session_state["pair_changed_from_map"] = True


demo_mode = os.getenv("KIMHAMJJI_DEMO_MODE", "").strip() == "1"
st.sidebar.subheader("데이터 연결")
if st.sidebar.button("데이터 새로고침", width="stretch"):
    clear_data_cache()
    cached_association.clear()
    cached_pair_summary.clear()
    cached_context_comparison.clear()
    cached_loglinear.clear()
    st.rerun()

try:
    with st.spinner("읽기 전용 데이터 연결과 검증을 진행하고 있습니다…"):
        raw = load_sheet_frames(demo_mode=demo_mode)
        bundle = prepare_data(raw.contents, raw.comments, raw.codebook)
except (DataSourceError, DataValidationError) as exc:
    st.title("김햄찌 PAME 연관성 탐색기")
    st.error(str(exc))
    st.info(
        "`.streamlit/secrets.toml.example`을 복사해 `.streamlit/secrets.toml`로 만들고 "
        "서비스 계정 값을 입력한 뒤, 시트를 해당 서비스 계정 이메일과 뷰어 권한으로 공유해 주세요."
    )
    st.code("streamlit run app.py", language="bash")
    st.stop()

st.sidebar.success(f"연결됨 · {raw.source}")
st.sidebar.caption(f"마지막 갱신: {raw.refreshed_at:%Y-%m-%d %H:%M:%S} KST · 캐시 5분")
st.sidebar.markdown(
    "본 앱은 Google Sheets API의 읽기 전용 범위만 사용하며 원본 시트에 값을 쓰지 않습니다."
)

st.title("김햄찌 PAME 연관성 탐색기")
st.caption("유튜브 댓글에서 P·A·M·E 반응이 같은 댓글에 함께 나타나는 양상을 방향성 없이 탐색합니다.")
if demo_mode:
    st.warning("현재 화면은 기능 검증용 합성 데이터입니다. 연구 결과로 사용하지 마세요.")
if st.session_state.pop("pair_changed_from_map", False):
    st.success("전체 관계 지도에서 선택한 변수 쌍으로 상세 분석을 갱신했습니다.")

if "pame_x" not in st.session_state:
    st.session_state["pame_x"] = "P"
if "pame_y" not in st.session_state:
    st.session_state["pame_y"] = "M"

control_1, control_2, control_3 = st.columns([1, 1, 1.45])
with control_1:
    variable_x = st.selectbox("첫 번째 변수", list(VARIABLE_COLUMNS), format_func=variable_display, key="pame_x")
y_options = [variable for variable in VARIABLE_COLUMNS if variable != variable_x]
if st.session_state.get("pame_y") not in y_options:
    st.session_state["pame_y"] = y_options[0]
with control_2:
    variable_y = st.selectbox("두 번째 변수", y_options, format_func=variable_display, key="pame_y")
context_options = {"전체": None, **{display: raw_name for raw_name, display in CONTEXT_LABELS.items()}}
with control_3:
    selected_context_label = st.selectbox("분석 맥락", list(context_options), index=0)
selected_context = context_options[selected_context_label]
analysis_frame = (
    bundle.analysis_comments
    if selected_context is None
    else bundle.analysis_comments.loc[bundle.analysis_comments["cde_context"].eq(selected_context)]
)

try:
    result = cached_association(analysis_frame, variable_x, variable_y)
except AnalysisUnavailable as exc:
    st.error(str(exc))
    st.stop()

metric_1, metric_2, metric_3, metric_4, metric_5 = st.columns(5)
metric_1.metric("분석 표본 N", f"{result.n:,}")
metric_2.metric("카이제곱", f"{result.chi2:,.2f}")
metric_3.metric("자유도", f"{result.dof}")
metric_4.metric("p값", format_p_value(result.p_value, include_symbol=False))
metric_5.metric("Cramér’s V", f"{result.cramers_v:.3f}")
st.markdown(f"<div class='context-note'>{full_interpretation(result, bundle.codebook_map).splitlines()[0]}</div>", unsafe_allow_html=True)

tabs = st.tabs(["상세 분석", "CDE 맥락별 비교", "실제 댓글", "전체 관계 지도", "데이터 현황"])

with tabs[0]:
    st.subheader("전체 검정과 코드 조합")
    if not result.expected_condition_ok:
        st.warning(
            f"기대빈도 조건에 주의가 필요합니다. 기대빈도 1 미만 {result.expected_below_one}셀, "
            f"5 미만 {result.expected_below_five}셀({result.expected_below_five_ratio:.1%})입니다. "
            "희소한 표에서는 결과를 확정적으로 해석하지 마세요."
        )
    else:
        st.success("기대빈도 점검 조건을 충족했습니다.")
    if result.fisher_p_value is not None:
        st.caption(f"2×2 표 보조 결과 · Fisher의 정확검정 {format_p_value(result.fisher_p_value)}")

    view = st.radio(
        "교차표 보기",
        ["관측빈도", "행 백분율", "열 백분율", "기대빈도", "조정 표준화 잔차"],
        horizontal=True,
    )
    st.dataframe(display_table(result, view, bundle.codebook_map), width="stretch")
    st.caption(f"선택한 두 변수의 실제 빈칸 때문에 제외된 댓글: {result.excluded_n:,}건. 0코드는 유효 범주로 포함됩니다.")

    st.subheader("조정 표준화 잔차 히트맵")
    st.caption("파랑 +는 기대보다 많은 동시 출현, 주황 -는 기대보다 적은 동시 출현입니다. 유의하지 않은 셀은 채도를 낮췄습니다.")
    st.plotly_chart(residual_heatmap(result, bundle.codebook_map), width="stretch", config={"displayModeBar": False})

    st.subheader("유의한 코드 조합")
    display_significant_table(result, bundle.codebook_map)

    st.subheader("회의용 자연어 해석")
    interpretation = full_interpretation(result, bundle.codebook_map)
    st.code(interpretation, language=None, wrap_lines=True)
    st.caption("해석문 오른쪽 위의 복사 아이콘을 누르면 전체 문장이 복사됩니다.")

with tabs[1]:
    st.subheader("네 가지 CDE 맥락 비교")
    comparison, context_results = cached_context_comparison(bundle.analysis_comments, variable_x, variable_y)
    comparison_display = comparison.copy()
    for column in ["카이제곱", "Cramér’s V"]:
        if column in comparison_display:
            comparison_display[column] = comparison_display[column].map(
                lambda value: f"{value:.3f}" if pd.notna(value) else "—"
            )
    if "p값" in comparison_display:
        comparison_display["p값"] = comparison_display["p값"].map(
            lambda value: format_p_value(value, include_symbol=False) if pd.notna(value) else "—"
        )
    st.dataframe(comparison_display, hide_index=True, width="stretch")
    if "Cramér’s V" in comparison:
        st.plotly_chart(context_cramers_bar(comparison), width="stretch", config={"displayModeBar": False})
    st.info("맥락별 Cramér’s V의 차이만으로 조절효과가 입증되었다고 해석하지 않습니다.")

    st.subheader("CDE 맥락에 따른 연관성 차이 검정")
    try:
        difference = cached_loglinear(bundle.analysis_comments, variable_x, variable_y)
        d1, d2, d3, d4 = st.columns(4)
        d1.metric("우도비 통계량", f"{difference.statistic:,.2f}")
        d2.metric("자유도", str(difference.dof))
        d3.metric("p값", format_p_value(difference.p_value, include_symbol=False))
        d4.metric("표본 N", f"{difference.n:,}")
        st.write(context_difference_interpretation(difference))
        st.caption(difference.note)
    except AnalysisUnavailable as exc:
        st.warning(str(exc))

    st.subheader("맥락별 유의 조합")
    for raw_context, context_result in context_results.items():
        with st.expander(CONTEXT_LABELS[raw_context]):
            display_significant_table(context_result, bundle.codebook_map)

with tabs[2]:
    st.subheader("통계 결과에 해당하는 실제 댓글")
    st.caption("조합 선택기는 위의 교차표·히트맵과 같은 변수 쌍을 사용합니다. 작성자는 기본적으로 숨깁니다.")
    cells = significant_cells(result)
    combo_mode = st.radio(
        "조합 필터",
        ["코드 조합 직접 선택", "양의 유의 조합 (+)", "음의 유의 조합 (-)"],
        horizontal=True,
    )
    selected_x_code = selected_y_code = None
    if combo_mode == "코드 조합 직접 선택":
        combo_col_1, combo_col_2 = st.columns(2)
        with combo_col_1:
            selected_x_code = st.selectbox(
                variable_display(variable_x),
                result.observed.index.tolist(),
                format_func=lambda code: code_label(code, bundle.codebook_map),
            )
        with combo_col_2:
            selected_y_code = st.selectbox(
                variable_display(variable_y),
                result.observed.columns.tolist(),
                format_func=lambda code: code_label(code, bundle.codebook_map),
            )
    else:
        direction = "+" if combo_mode.startswith("양의") else "-"
        if cells.loc[cells["direction"].eq(direction)].empty:
            st.info(f"현재 분석에서 {combo_mode}이 없습니다.")

    filter_col_1, filter_col_2, filter_col_3 = st.columns([1.15, 1.5, 1])
    with filter_col_1:
        comment_context_label = st.selectbox("댓글 맥락", list(context_options), key="comment_context")
        comment_context = context_options[comment_context_label]
    context_base = bundle.analysis_comments if comment_context is None else bundle.analysis_comments.loc[
        bundle.analysis_comments["cde_context"].eq(comment_context)
    ]
    with filter_col_2:
        title_choices = sorted(context_base["제목"].dropna().astype(str).unique().tolist())
        selected_titles = st.multiselect("콘텐츠 제목", title_choices, placeholder="전체 콘텐츠")
    with filter_col_3:
        minimum_likes = st.number_input("최소 좋아요 수", min_value=0, value=0, step=1)

    filter_col_4, filter_col_5 = st.columns([1.4, 1])
    with filter_col_4:
        keyword = st.text_input("댓글 키워드", placeholder="댓글 내용에서 검색")
    with filter_col_5:
        sort_by = st.selectbox("정렬", ["좋아요 많은 순", "최신순", "원본 데이터 순", "무작위"])

    valid_dates = context_base["댓글 작성일"].dropna()
    start_date = end_date = None
    if not valid_dates.empty:
        min_date, max_date = valid_dates.min().date(), valid_dates.max().date()
        chosen_dates = st.date_input("작성일", value=(min_date, max_date), min_value=min_date, max_value=max_date)
        if isinstance(chosen_dates, (tuple, list)) and len(chosen_dates) == 2:
            start_date, end_date = chosen_dates

    filtered = filter_comments(
        bundle.analysis_comments,
        x_column=VARIABLE_COLUMNS[variable_x] if combo_mode == "코드 조합 직접 선택" else None,
        x_code=selected_x_code,
        y_column=VARIABLE_COLUMNS[variable_y] if combo_mode == "코드 조합 직접 선택" else None,
        y_code=selected_y_code,
        context=comment_context,
        titles=selected_titles,
        keyword=keyword,
        minimum_likes=minimum_likes,
        start_date=start_date,
        end_date=end_date,
        sort_by=sort_by,
    )
    if combo_mode != "코드 조합 직접 선택":
        wanted_direction = "+" if combo_mode.startswith("양의") else "-"
        allowed = set(
            cells.loc[cells["direction"].eq(wanted_direction), ["x_code", "y_code"]]
            .itertuples(index=False, name=None)
        )
        pair_values = list(zip(filtered[VARIABLE_COLUMNS[variable_x]], filtered[VARIABLE_COLUMNS[variable_y]]))
        filtered = filtered.loc[[pair in allowed for pair in pair_values]].reset_index(drop=True)

    privacy_col_1, privacy_col_2, privacy_col_3 = st.columns([1, 1, 2])
    with privacy_col_1:
        show_author = st.checkbox("작성자 표시", value=False)
    with privacy_col_2:
        include_author_csv = st.checkbox("CSV에 작성자 포함", value=False)
    with privacy_col_3:
        st.write(f"현재 필터 결과 **{len(filtered):,}건** · 페이지당 20건")

    export_columns = [
        "comment_id", "댓글 내용", "제목", "cde_label", "댓글 좋아요 수", "댓글 작성일",
        "P_code", "A_code", "M_code", "E_comment_code", "O_code",
    ]
    if include_author_csv:
        export_columns.insert(1, "댓글 작성자")
    export = filtered[export_columns].copy()
    export["댓글 작성일"] = export["댓글 작성일"].dt.strftime("%Y-%m-%d")
    st.download_button(
        "현재 필터 댓글 CSV 다운로드",
        export.to_csv(index=False).encode("utf-8-sig"),
        file_name=f"kimhamjji_comments_{variable_x}_{variable_y}.csv",
        mime="text/csv",
        disabled=filtered.empty,
    )

    page_count = max(1, math.ceil(len(filtered) / 20))
    page = st.number_input("페이지", min_value=1, max_value=page_count, value=1, step=1)
    page_frame = filtered.iloc[(page - 1) * 20 : page * 20]
    if page_frame.empty:
        st.info("현재 조건에 해당하는 댓글이 없습니다.")
    for _, row in page_frame.iterrows():
        with st.container(border=True):
            st.write(row["댓글 내용"])
            date_text = row["댓글 작성일"].strftime("%Y-%m-%d") if pd.notna(row["댓글 작성일"]) else "날짜 없음"
            st.caption(
                f"{row['제목']} · {row['cde_label']} · 좋아요 {int(row['댓글 좋아요 수']) if pd.notna(row['댓글 좋아요 수']) else 0:,} · {date_text}"
            )
            labels = [code_label(row[VARIABLE_COLUMNS[v]], bundle.codebook_map) for v in ["P", "A", "M", "E"]]
            if str(row.get("O_code", "")).strip():
                labels.append(code_label(row["O_code"], bundle.codebook_map))
            st.caption(" · ".join(labels))
            identity = f"comment_id: {row['comment_id']}"
            if show_author:
                identity += f" · 작성자: {row['댓글 작성자']}"
            st.caption(identity)

with tabs[3]:
    st.subheader("전체 PAME 관계 지도")
    st.caption("화살표 없이 여섯 쌍의 방향성 없는 연관성을 요약합니다. 칸을 누르면 상단 상세 분석이 해당 쌍으로 바뀝니다.")
    pair_summary, pair_results = cached_pair_summary(bundle.analysis_comments)
    summary_display = pair_summary.copy()
    summary_display["변수 쌍"] = summary_display["variable_x"] + " × " + summary_display["variable_y"]
    summary_display["p값"] = summary_display.get("p_raw", np.nan).map(
        lambda value: format_p_value(value, include_symbol=False) if pd.notna(value) else "—"
    )
    summary_display["전체 Holm 보정 p값"] = summary_display["p_holm"].map(
        lambda value: format_p_value(value, include_symbol=False) if pd.notna(value) else "—"
    )
    summary_display["Cramér’s V"] = summary_display.get("cramers_v", np.nan).map(
        lambda value: f"{value:.3f}" if pd.notna(value) else "—"
    )
    st.dataframe(
        summary_display[["변수 쌍", "n", "p값", "전체 Holm 보정 p값", "Cramér’s V", "holm_significant", "expected_ok"]].rename(
            columns={"n": "N", "holm_significant": "Holm 유의", "expected_ok": "기대빈도 충족"}
        ),
        hide_index=True,
        width="stretch",
    )

    order = ["P", "A", "M", "E"]
    header_columns = st.columns([0.65, 1, 1, 1, 1])
    header_columns[0].markdown("**변수**")
    for index, variable in enumerate(order):
        header_columns[index + 1].markdown(f"**{variable_display(variable)}**")
    for row_index, row_variable in enumerate(order):
        columns = st.columns([0.65, 1, 1, 1, 1])
        columns[0].markdown(f"**{variable_display(row_variable)}**")
        for column_index, column_variable in enumerate(order):
            if row_variable == column_variable:
                columns[column_index + 1].markdown("—")
                continue
            first, second = sorted((row_variable, column_variable), key=order.index)
            pair_result = pair_results.get((first, second))
            if pair_result is None:
                columns[column_index + 1].caption("계산 불가")
                continue
            summary_row = pair_summary.loc[
                pair_summary["variable_x"].eq(first) & pair_summary["variable_y"].eq(second)
            ].iloc[0]
            marker = "●" if bool(summary_row["holm_significant"]) else "○"
            columns[column_index + 1].button(
                f"{marker} V={pair_result.cramers_v:.3f}",
                key=f"map-{row_index}-{column_index}",
                on_click=choose_pair,
                args=(first, second),
                width="stretch",
                help="● 전체 6검정 Holm 보정 후 유의 · ○ 유의하지 않음",
            )

    st.subheader("가장 큰 양·음의 잔차 조합")
    extreme_rows = []
    for row in pair_summary.itertuples(index=False):
        if not getattr(row, "error", ""):
            px, py, pr = row.top_positive
            nx, ny, nr = row.top_negative
            extreme_rows.append(
                {
                    "변수 쌍": f"{row.variable_x} × {row.variable_y}",
                    "가장 큰 + 조합": f"{code_label(px, bundle.codebook_map)} × {code_label(py, bundle.codebook_map)} ({pr:.2f})",
                    "가장 작은 - 조합": f"{code_label(nx, bundle.codebook_map)} × {code_label(ny, bundle.codebook_map)} ({nr:.2f})",
                }
            )
    st.dataframe(pd.DataFrame(extreme_rows), hide_index=True, width="stretch")

with tabs[4]:
    st.subheader("데이터 현황과 품질")
    quality = bundle.quality
    status_columns = st.columns(6)
    status_columns[0].metric("전체 콘텐츠", f"{quality['total_contents']:,}")
    status_columns[1].metric("전체 댓글", f"{quality['total_comments']:,}")
    status_columns[2].metric("분석 콘텐츠", f"{quality['analysis_contents']:,}")
    status_columns[3].metric("분석 댓글", f"{quality['analysis_comments']:,}")
    status_columns[4].metric("제외 콘텐츠", f"{quality['excluded_contents']:,}")
    status_columns[5].metric("제외 댓글", f"{quality['excluded_comments']:,}")

    context_status = pd.DataFrame(
        [
            {
                "CDE 맥락": display,
                "콘텐츠 수": quality["context_content_counts"].get(display, 0),
                "댓글 수": quality["context_comment_counts"].get(display, 0),
            }
            for display in CONTEXT_LABELS.values()
        ]
    )
    st.dataframe(context_status, hide_index=True, width="stretch")

    checks = pd.DataFrame(
        [
            ("콘텐츠 video_id 중복 행", quality["content_video_id_duplicates"]),
            ("콘텐츠와 연결되지 않는 댓글", quality["unmatched_comments"]),
            ("빈 comment_id", quality["blank_comment_ids"]),
            ("읽을 수 없는 comment_id", quality["invalid_comment_ids"]),
            ("대체 comment_id 사용", quality["fallback_comment_ids"]),
            ("중복 comment_id 행", quality["duplicate_comment_id_rows"]),
            ("좋아요 숫자 변환 실패", quality["like_conversion_failures"]),
            ("작성일 날짜 변환 실패", quality["date_conversion_failures"]),
            ("완전 동일 중복 댓글 행", quality["exact_duplicate_rows"]),
            ("완전 동일 중복 추가 행", quality["exact_duplicate_extra_rows"]),
        ],
        columns=["검사 항목", "건수"],
    )
    st.dataframe(checks, hide_index=True, width="stretch")

    blank_frame = pd.DataFrame(
        [{"변수": variable, "실제 빈칸 수": count} for variable, count in quality["blank_codes"].items()]
    )
    st.dataframe(blank_frame, hide_index=True, width="stretch")
    unknown_messages = [
        f"{variable}: {', '.join(codes)}" for variable, codes in quality["unknown_codes"].items() if codes
    ]
    if unknown_messages:
        st.warning("코드북에 없는 코드가 있습니다. " + " / ".join(unknown_messages))
    else:
        st.success("P·A·M·E 데이터에서 코드북에 없는 코드는 발견되지 않았습니다.")
    if quality["fallback_comment_ids"]:
        st.warning("일부 댓글에 SHA-256 기반 대체 comment_id를 사용했습니다. 원본 시트는 수정하지 않았습니다.")
    if quality["exact_duplicate_rows"]:
        st.warning("완전히 동일한 중복 댓글이 있습니다. 분석에서는 원자료 행을 유지하며 품질 정보로만 알립니다.")

st.divider()
st.caption(
    "본 분석은 동일한 댓글에서 나타나는 범주형 반응 간 연관성을 탐색하기 위한 것입니다. "
    "카이제곱 검정은 인과관계를 입증하지 않습니다. 또한 동일한 영상에 속한 댓글 간 유사성을 별도로 "
    "통제하지 않은 탐색적 결과이므로 해석에 주의가 필요합니다. 표본이 크므로 p값뿐 아니라 "
    "Cramér’s V와 구체적인 코드 조합을 함께 확인하세요."
)
