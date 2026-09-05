"""10만 건 합성 데이터에서 핵심 여섯 쌍 분석 시간을 점검한다."""

import sys
from pathlib import Path
from time import perf_counter

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from src.data_validator import prepare_data
from src.demo_data import make_demo_frames
from src.statistics import all_pair_summary


def main():
    started = perf_counter()
    frames = make_demo_frames(rows_per_context=25_000)
    prepared = prepare_data(frames.contents, frames.comments, frames.codebook)
    prepared_seconds = perf_counter() - started
    analysis_started = perf_counter()
    summary, _ = all_pair_summary(prepared.analysis_comments)
    analysis_seconds = perf_counter() - analysis_started
    print(f"rows={len(prepared.analysis_comments):,}")
    print(f"prepare_seconds={prepared_seconds:.3f}")
    print(f"six_pair_analysis_seconds={analysis_seconds:.3f}")
    print(summary[["variable_x", "variable_y", "n", "cramers_v"]].to_string(index=False))


if __name__ == "__main__":
    main()
