# 김햄찌 PAME 연관성 탐색기

AI 애니메이션 캐릭터 ‘김햄찌’의 YouTube 댓글에서 P·A·M·E 반응이 같은 댓글에 함께 나타나는 양상을 탐색하는 Streamlit 앱입니다. 관찰자료의 **방향성 없는 연관성**만 다루며 인과관계를 주장하지 않습니다.

## 제공 기능

- P·A·M·E 중 서로 다른 두 변수를 선택해 Pearson 카이제곱, Cramér’s V, 기대빈도, 행·열 백분율을 계산합니다.
- 조정 표준화 잔차와 셀별 양측 p값의 Holm 보정으로 기대보다 많은 조합 `+`와 적은 조합 `-`를 구분합니다.
- 여섯 변수쌍 전체 검정에 별도의 Holm 보정을 적용하고 대칭형 관계 지도를 제공합니다.
- 네 CDE 맥락별 결과와 `[XY][XCDE][YCDE]` 대 `[XYCDE]` 로그선형 우도비 검정을 제공합니다.
- 통계 셀과 연결되는 실제 댓글을 20개씩 검색·정렬·다운로드합니다. 작성자는 기본적으로 숨깁니다.
- Google Sheets를 5분간 캐시하며, 새로고침 버튼을 누를 때만 최신 데이터를 다시 읽습니다.
- 원본 시트에는 쓰지 않습니다. 인증 범위도 `spreadsheets.readonly` 하나뿐입니다.

## 프로젝트 구조

```text
.
├── app.py
├── requirements.txt
├── runtime.txt
├── README.md
├── VALIDATION.md
├── .gitignore
├── .streamlit/
│   ├── config.toml
│   └── secrets.toml.example
├── src/
│   ├── config.py
│   ├── data_loader.py
│   ├── data_validator.py
│   ├── demo_data.py
│   ├── statistics.py
│   ├── interpretation.py
│   └── visualizations.py
├── scripts/
│   ├── benchmark_100k.py
│   └── json_key_to_secrets.py
└── tests/
    ├── test_statistics.py
    ├── test_validation.py
    └── test_interpretation.py
```

## 처음부터 배포까지

### 1. Google Cloud 프로젝트 준비

1. [Google Cloud Console](https://console.cloud.google.com/)에 로그인합니다.
2. 위쪽 프로젝트 선택 메뉴 → **새 프로젝트**를 누릅니다.
3. 프로젝트 이름을 입력하고 **만들기**를 누릅니다.
4. 방금 만든 프로젝트를 선택합니다.

### 2. Google Sheets API 활성화

1. 왼쪽 메뉴 → **API 및 서비스** → **라이브러리**로 이동합니다.
2. `Google Sheets API`를 검색합니다.
3. **Google Sheets API** → **사용**을 누릅니다.

Google 공식 절차는 [Google Workspace API 활성화](https://developers.google.com/workspace/guides/enable-apis?hl=ko)를 참고하세요.

### 3. 읽기 전용 서비스 계정 생성

1. 왼쪽 메뉴 → **IAM 및 관리자** → **서비스 계정**으로 이동합니다.
2. **서비스 계정 만들기**를 누릅니다.
3. 이름을 예를 들어 `kimhamjji-sheet-reader`로 입력합니다.
4. **만들고 계속하기**를 누릅니다.
5. 프로젝트 역할은 추가하지 않아도 됩니다. **완료**를 누릅니다.
6. 생성된 서비스 계정 이메일을 누릅니다.
7. **키** 탭 → **키 추가** → **새 키 만들기** → **JSON** → **만들기**를 누릅니다.

서비스 계정 키는 비밀번호와 같습니다. 메일·메신저로 보내지 말고 GitHub에 올리지 마세요. Google의 현재 메뉴는 [서비스 계정 만들기](https://cloud.google.com/iam/docs/service-accounts-create?hl=ko)와 [키 만들기](https://cloud.google.com/iam/docs/keys-create-delete?hl=ko)에서 확인할 수 있습니다.

### 4. Google Sheet를 뷰어로 공유

대상 시트:

`https://docs.google.com/spreadsheets/d/1Knws8uaAT5CAVr4CQX0D1PyO2sbCPTKoROCFcOCBY8U/edit`

1. 내려받은 JSON에서 `client_email` 값을 확인합니다.
2. Google Sheet 오른쪽 위 **공유**를 누릅니다.
3. `client_email` 주소를 붙여 넣습니다.
4. 권한을 반드시 **뷰어**로 선택하고 **보내기**를 누릅니다.
5. ‘링크가 있는 모든 사용자’ 공개로 바꾸지 않습니다. 원본 시트는 비공개 상태를 유지합니다.

Google의 공유 방식은 [Sheets 공동작업 안내](https://support.google.com/docs/answer/9331169?hl=ko)를 참고하세요.

### 5. 로컬 Secrets 설정

프로젝트 폴더에서 다음을 실행하면 서비스 계정 JSON을 `.streamlit/secrets.toml`로 안전하게 변환합니다.

```bash
python scripts/json_key_to_secrets.py /다운로드/폴더/서비스계정키.json
```

또는 `.streamlit/secrets.toml.example`을 `.streamlit/secrets.toml`로 복사한 뒤 JSON의 각 값을 직접 옮겨도 됩니다.

확인할 점:

- 실제 `.streamlit/secrets.toml`은 `.gitignore`에 포함되어 있습니다.
- JSON 원본도 프로젝트 폴더에 두지 마세요.
- 앱은 `https://www.googleapis.com/auth/spreadsheets.readonly` 범위만 요청합니다.

### 6. 패키지 설치

Python 3.12가 필요합니다.

```bash
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
pip install -r requirements.txt
```

Windows PowerShell에서는 가상환경 활성화만 다음처럼 바꿉니다.

```powershell
.venv\Scripts\Activate.ps1
```

### 7. Streamlit 로컬 실행

```bash
streamlit run app.py
```

브라우저에서 `http://localhost:8501`을 엽니다. 왼쪽에 `연결됨 · Google Sheets`가 표시되고 데이터 현황에 실제 건수가 보이면 정상입니다.

인증 없이 화면 기능만 점검하려면 다음 데모 모드를 사용할 수 있습니다. 합성 데이터이므로 연구 결과에는 사용하지 마세요.

```bash
KIMHAMJJI_DEMO_MODE=1 streamlit run app.py
```

Windows PowerShell:

```powershell
$env:KIMHAMJJI_DEMO_MODE="1"; streamlit run app.py
```

### 8. 테스트 실행

```bash
pytest -q
python scripts/benchmark_100k.py
```

현재 검증 결과는 [VALIDATION.md](VALIDATION.md)에 기록되어 있습니다.

### 9. GitHub 저장소 연결

1. [GitHub 새 저장소](https://github.com/new)에서 저장소 이름을 정합니다.
2. 공개 앱으로 배포하려면 **Public**을 선택합니다.
3. 이 폴더에는 이미 README와 `.gitignore`가 있으므로 GitHub 화면의 README·`.gitignore` 자동 생성은 선택하지 않습니다.
4. 프로젝트 폴더에서 아래 명령을 실행합니다. `<사용자명>`은 본인 계정으로 바꿉니다.

```bash
git init
git branch -M main
git add .
git status
git check-ignore .streamlit/secrets.toml
git commit -m "Build PAME association dashboard"
git remote add origin https://github.com/<사용자명>/kimhamjji-pame-dashboard.git
git push -u origin main
```

`git status`에 `.streamlit/secrets.toml`, 서비스 계정 JSON, API 키가 보이면 커밋하지 말고 먼저 제거하세요. GitHub의 현재 절차는 [새 저장소 만들기](https://docs.github.com/ko/repositories/creating-and-managing-repositories/creating-a-new-repository)를 참고하세요.

### 10. Streamlit Community Cloud 공개 배포

1. [share.streamlit.io](https://share.streamlit.io/)에서 GitHub 계정으로 로그인합니다.
2. 작업공간 오른쪽 위 **Create app**을 누릅니다.
3. **Yup, I have an app**을 선택합니다.
4. Repository에 방금 만든 저장소, Branch에 `main`, Main file path에 `app.py`를 입력합니다.
5. **Advanced settings**를 누릅니다.
6. Python version을 `3.12`로 선택합니다.
7. Secrets 입력란에 로컬 `.streamlit/secrets.toml`의 **내용만** 붙여 넣고 **Save**를 누릅니다.
8. **Deploy**를 누릅니다.

현재 Community Cloud 배포 화면은 [공식 배포 문서](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/deploy)를, Secrets 관리 원칙은 [공식 Secrets 문서](https://docs.streamlit.io/deploy/streamlit-community-cloud/deploy-your-app/secrets-management)를 참고하세요.

### 11. 로그인 없는 공개 앱으로 설정

공개 저장소에서 배포하면 기본적으로 공개됩니다. 그래도 다음을 확인합니다.

1. 배포된 앱 → 오른쪽 위 **Share** 또는 **App settings**를 엽니다.
2. **Sharing** → **Who can view this app**에서 **This app is public and searchable**을 선택합니다.
3. 시크릿 브라우저 창에서 앱 URL을 열어 로그인 없이 보이는지 확인합니다.

공개·비공개 전환 메뉴는 [Streamlit 앱 공유 문서](https://docs.streamlit.io/deploy/streamlit-community-cloud/share-your-app)에 설명되어 있습니다.

### 12. 데이터 새로고침

앱 왼쪽의 **데이터 새로고침**을 누르면 5분 캐시를 비우고 지정된 세 탭을 다시 읽습니다. 여러 이용자의 매 조작마다 원본 10만 행을 다시 호출하지 않습니다.

## 흔한 오류 해결

| 화면 메시지/증상 | 확인할 것 |
|---|---|
| 서비스 계정 설정을 찾지 못함 | `.streamlit/secrets.toml` 경로와 `[gcp_service_account]` 제목 확인 |
| 스프레드시트를 열 수 없음 | JSON의 `client_email`을 시트에 **뷰어**로 공유했는지 확인 |
| `WorksheetNotFound` | 세 탭 이름의 공백·콜론·슬래시를 수정하지 않았는지 확인 |
| `API has not been used` 또는 403 | Google Cloud에서 Google Sheets API를 사용 설정하고 1~2분 뒤 재시도 |
| `invalid_grant` | `private_key`의 줄바꿈, 서비스 계정 키 폐기 여부, 컴퓨터 시간을 확인 |
| Streamlit Cloud에서만 인증 실패 | App settings → Secrets에 로컬 `secrets.toml` 내용을 그대로 붙였는지 확인 |
| 앱이 오래된 데이터를 표시 | 왼쪽 **데이터 새로고침**을 누름 |
| 기대빈도 경고 | 희소 셀이 많은 결과이므로 확정적으로 해석하지 않음 |
| 작성자가 CSV에 없음 | 개인정보 보호 기본값입니다. 필요한 경우 `CSV에 작성자 포함`을 명시적으로 선택 |

오류 화면에는 전체 스택 트레이스를 공개하지 않습니다. Cloud 운영자는 앱의 **Manage app** 로그에서만 자세한 내용을 확인하세요.

## 통계 해석 주의

본 분석은 동일한 댓글에서 나타나는 범주형 반응 간 연관성을 탐색합니다. 카이제곱 검정은 인과관계를 입증하지 않습니다. 동일한 영상에 속한 댓글 간 유사성을 별도로 통제하지 않은 탐색적 결과이므로 해석에 주의해야 합니다. 표본이 크므로 p값만 보지 말고 Cramér’s V와 구체적인 코드 조합을 함께 확인하세요.

