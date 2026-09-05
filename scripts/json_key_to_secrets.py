"""Google 서비스 계정 JSON을 로컬 Streamlit Secrets로 변환한다."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("json_key", type=Path, help="Google Cloud에서 내려받은 서비스 계정 JSON 경로")
    parser.add_argument("--force", action="store_true", help="기존 secrets.toml 덮어쓰기")
    args = parser.parse_args()

    source = args.json_key.expanduser().resolve()
    target = Path(__file__).resolve().parents[1] / ".streamlit" / "secrets.toml"
    if target.exists() and not args.force:
        raise SystemExit(f"중단: {target} 파일이 이미 있습니다. 덮어쓰려면 --force를 사용하세요.")
    with source.open(encoding="utf-8") as handle:
        credentials = json.load(handle)
    required = {"type", "project_id", "private_key", "client_email", "token_uri"}
    missing = sorted(required - set(credentials))
    if missing:
        raise SystemExit("서비스 계정 JSON 필드가 부족합니다: " + ", ".join(missing))

    lines = ["[gcp_service_account]"]
    for key, value in credentials.items():
        if isinstance(value, str):
            lines.append(f"{key} = {json.dumps(value, ensure_ascii=False)}")
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("\n".join(lines) + "\n", encoding="utf-8")
    os.chmod(target, 0o600)
    print(f"완료: {target}")
    print("이 파일과 원본 JSON을 GitHub에 커밋하지 마세요.")


if __name__ == "__main__":
    main()
