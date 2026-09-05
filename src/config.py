"""앱 전체에서 공유하는 고정 설정."""

SPREADSHEET_ID = "1Knws8uaAT5CAVr4CQX0D1PyO2sbCPTKoROCFcOCBY8U"

CONTENT_SHEET = "대상 콘텐츠 메타 데이터/ 콘텐츠 분석 결과"
COMMENT_SHEET = "대상 콘텐츠 댓글 데이터"
CODEBOOK_SHEET = "댓글 분석: POE 코드 정의"
ALLOWED_SHEETS = (CONTENT_SHEET, COMMENT_SHEET, CODEBOOK_SHEET)

CONTENT_COLUMNS = ["video_id", "제목", "cde_context"]
COMMENT_COLUMNS = [
    "video_id",
    "comment_id",
    "댓글 작성자",
    "댓글 내용",
    "댓글 좋아요 수",
    "댓글 작성일",
    "P_code",
    "O_code",
    "E_comment_code",
    "M_code",
    "A_code",
]
CODEBOOK_COLUMNS = ["variable", "code", "label", "definition"]

VARIABLE_COLUMNS = {
    "P": "P_code",
    "A": "A_code",
    "M": "M_code",
    "E": "E_comment_code",
}
VARIABLE_NAMES = {
    "P": "작성자의 위치",
    "A": "자전적 기억",
    "M": "마음지각",
    "E": "감정적 공명",
}
VARIABLE_PAIRS = (("P", "A"), ("P", "M"), ("P", "E"), ("A", "M"), ("A", "E"), ("M", "E"))

CONTEXT_LABELS = {
    "과업–타인 부정정서형": "업무 상황 × 타인 부정 정서",
    "관계–타인 부정정서형": "관계 상황 × 타인 부정 정서",
    "개인상황–자기 부정정서형": "개인 상황 × 자기 부정 정서",
    "개인상황–자기 긍정정서형": "개인 상황 × 자기 긍정 정서",
}

