"""인증정보 없이 UI를 검증할 때만 쓰는 합성 데이터."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

import numpy as np
import pandas as pd

from src.config import CONTEXT_LABELS
from src.data_loader import SheetFrames


def make_demo_frames(rows_per_context: int = 180, seed: int = 20260905) -> SheetFrames:
    rng = np.random.default_rng(seed)
    contexts = list(CONTEXT_LABELS)
    content_rows = []
    comment_rows = []
    base_date = datetime(2026, 1, 1)

    for context_index, context in enumerate(contexts):
        video_ids = [f"demo-{context_index + 1}-{i + 1}" for i in range(3)]
        for i, video_id in enumerate(video_ids):
            content_rows.append(
                {"video_id": video_id, "제목": f"데모 콘텐츠 {context_index + 1}-{i + 1}", "cde_context": context}
            )
        for i in range(rows_per_context):
            p_code = rng.choice(["P1", "P2", "P3"], p=[0.45, 0.2, 0.35])
            # 맥락별로 다른 P×M 연관 패턴을 만들어 UI·고급 검정을 점검한다.
            p_m1 = {
                0: {"P1": 0.12, "P2": 0.38, "P3": 0.72},
                1: {"P1": 0.24, "P2": 0.35, "P3": 0.58},
                2: {"P1": 0.52, "P2": 0.34, "P3": 0.18},
                3: {"P1": 0.30, "P2": 0.36, "P3": 0.48},
            }[context_index][p_code]
            m_code = "M1" if rng.random() < p_m1 else "M0"
            a_code = "A1" if rng.random() < (0.42 if m_code == "M1" else 0.18) else "A0"
            e_probs = [0.25, 0.5, 0.25] if m_code == "M1" else [0.55, 0.35, 0.10]
            e_code = rng.choice(["E0", "E1", "E2"], p=e_probs)
            video_id = video_ids[i % len(video_ids)]
            comment_rows.append(
                {
                    "video_id": video_id,
                    "comment_id": f"demo-comment-{context_index + 1}-{i + 1}",
                    "댓글 작성자": f"데모 작성자 {i % 17 + 1}",
                    "댓글 내용": f"연구 화면 검증을 위한 합성 댓글 {context_index + 1}-{i + 1}",
                    "댓글 좋아요 수": int(rng.integers(0, 250)),
                    "댓글 작성일": (base_date + timedelta(days=int(rng.integers(0, 220)))).date().isoformat(),
                    "P_code": p_code,
                    "O_code": rng.choice(["O0", "O1", "O2", "O3", "O4"]),
                    "E_comment_code": e_code,
                    "M_code": m_code,
                    "A_code": a_code,
                }
            )

    codebook = pd.DataFrame(
        [
            ("P", "P1", "제3의 관찰자", "서사 밖에서 비평·분석"),
            ("P", "P2", "경계선 대입자", "가상 상황에 현실의 나를 조건부 대입"),
            ("P", "P3", "세계관 참여자", "캐릭터와 같은 세계에 있는 것처럼 직접 발화"),
            ("O", "O0", "대상 없음", "웃음·울음 등의 단순 반응"),
            ("O", "O1", "콘텐츠 메타", "제작자·연출·편집·성우 등에 대한 반응"),
            ("O", "O2", "서사 내 캐릭터·스토리", "캐릭터 또는 이야기 내용에 대한 반응"),
            ("O", "O3", "나", "수용자 개인의 경험 소환"),
            ("O", "O4", "사회·보편 스키마", "직장 문화·다이어트 등의 사회적 맥락"),
            ("E", "E0", "감정적 공명 없음", "감정적 공명이나 도덕적 지지가 나타나지 않음"),
            ("E", "E1", "감정적 공명", "감정적 동화가 나타나지만 도덕적 지지는 없음"),
            ("E", "E2", "감정적 공명 및 도덕적 지지", "위로·보호·응원 등의 반응 포함"),
            ("M", "M0", "마음지각 없음", "캐릭터의 마음에 대한 지각이 나타나지 않음"),
            ("M", "M1", "마음지각 발생", "캐릭터의 마음에 대해 언급"),
            ("A", "A0", "자전적 기억 없음", "개인적 기억이나 경험이 나타나지 않음"),
            ("A", "A1", "자전적 기억 활성화", "개인적 에피소드나 과거사 언급"),
        ],
        columns=["variable", "code", "label", "definition"],
    )
    return SheetFrames(
        contents=pd.DataFrame(content_rows),
        comments=pd.DataFrame(comment_rows),
        codebook=codebook,
        refreshed_at=datetime.now(ZoneInfo("Asia/Seoul")),
        source="합성 데모 데이터",
    )

