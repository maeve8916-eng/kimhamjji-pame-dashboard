"""읽기 전용 Google Sheets 연결과 Streamlit 캐시."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from src.config import (
    CODEBOOK_SHEET,
    COMMENT_SHEET,
    CONTENT_SHEET,
    SPREADSHEET_ID,
)

READONLY_SCOPE = "https://www.googleapis.com/auth/spreadsheets.readonly"


class DataSourceError(RuntimeError):
    """사용자에게 안전하게 표시할 데이터 연결 오류."""


@dataclass
class SheetFrames:
    contents: pd.DataFrame
    comments: pd.DataFrame
    codebook: pd.DataFrame
    refreshed_at: datetime
    source: str = "Google Sheets"


def _rows_to_frame(rows: list[list[object]]) -> pd.DataFrame:
    if not rows:
        return pd.DataFrame()
    headers = [str(value).strip() for value in rows[0]]
    width = len(headers)
    normalized = [(list(row) + [""] * width)[:width] for row in rows[1:]]
    frame = pd.DataFrame(normalized, columns=headers)
    if frame.empty:
        return frame
    nonempty = frame.apply(lambda col: col.astype(str).str.strip().ne(""))
    return frame.loc[nonempty.any(axis=1)].reset_index(drop=True)


def _credentials_from_streamlit_secrets():
    try:
        from google.oauth2.service_account import Credentials

        info = dict(st.secrets["gcp_service_account"])
        if "private_key" in info:
            info["private_key"] = str(info["private_key"]).replace("\\n", "\n")
        return Credentials.from_service_account_info(info, scopes=[READONLY_SCOPE])
    except (KeyError, FileNotFoundError) as exc:
        raise DataSourceError(
            "Google 서비스 계정 설정을 찾지 못했습니다. README의 Secrets 설정을 확인해 주세요."
        ) from exc
    except Exception as exc:
        if "secret" in exc.__class__.__name__.lower() or "secrets file" in str(exc).lower():
            raise DataSourceError(
                "Google 서비스 계정 설정을 찾지 못했습니다. README의 Secrets 설정을 확인해 주세요."
            ) from exc
        raise DataSourceError(
            "Google 읽기 전용 인증정보를 사용할 수 없습니다. 서비스 계정 키 형식을 확인해 주세요."
        ) from exc


def _read_google_sheet() -> SheetFrames:
    try:
        import gspread

        client = gspread.authorize(_credentials_from_streamlit_secrets())
        book = client.open_by_key(SPREADSHEET_ID)

        # 요구사항에 지정된 세 탭 외에는 접근하지 않는다. get_all_values는
        # 그리드 전체가 아니라 마지막 값이 있는 행·열까지만 반환한다.
        contents = _rows_to_frame(book.worksheet(CONTENT_SHEET).get_all_values())
        comments = _rows_to_frame(book.worksheet(COMMENT_SHEET).get_all_values())
        codebook = _rows_to_frame(book.worksheet(CODEBOOK_SHEET).get("F1:I16"))
        return SheetFrames(
            contents=contents,
            comments=comments,
            codebook=codebook,
            refreshed_at=datetime.now(ZoneInfo("Asia/Seoul")),
        )
    except DataSourceError:
        raise
    except gspread.WorksheetNotFound as exc:
        raise DataSourceError(f"필수 탭을 찾지 못했습니다: {exc}") from exc
    except gspread.SpreadsheetNotFound as exc:
        raise DataSourceError(
            "스프레드시트를 열 수 없습니다. 서비스 계정 이메일을 뷰어로 공유했는지 확인해 주세요."
        ) from exc
    except Exception as exc:
        raise DataSourceError(
            "Google Sheets 데이터를 읽는 중 오류가 발생했습니다. 잠시 후 새로고침해 주세요."
        ) from exc


@st.cache_data(ttl=300, show_spinner=False)
def load_sheet_frames(demo_mode: bool = False) -> SheetFrames:
    """5분 동안 공유 캐시되는 데이터 로더."""
    if demo_mode:
        from src.demo_data import make_demo_frames

        return make_demo_frames()
    return _read_google_sheet()


def clear_data_cache() -> None:
    load_sheet_frames.clear()
