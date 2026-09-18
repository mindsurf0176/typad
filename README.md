# typad

Notepad++처럼 가볍고, 탭·문법 강조·찾기/바꾸기·폴더 워크스페이스가 있는 텍스트 에디터.
의존성 없음. Python 3 표준 라이브러리(`tkinter`)만 사용합니다.

소스: https://github.com/mindsurf0176/typad

## 실행

```bash
python3 texter.py
python3 texter.py README.md
python3 texter.py /path/to/folder
```

설정과 마지막 세션은 `~/Library/Application Support/typad/config.json`에 저장됩니다.
예전 `~/.typad.json` / `~/.txtr.json` / `~/.textpress.json` / `~/.texter.json`이 있으면 그대로 읽어 옵니다.

## 기능

- 탭, 저장 확인, UTF-8/CP949, LF/CRLF
- 확장자 기준 문법 강조
- 찾기/바꾸기(정규식), 폴더에서 찾기
- 줄 번호, 현재 줄, 괄호 짝, 북마크
- 주석 토글, 줄 복제/이동/삭제, 자동 들여쓰기
- 폴더 트리, 최근 파일, 세션 복원
- 어두운/밝은 테마, 확대/축소
- Shift+Enter 줄바꿈, ⌘⌫ 줄 앞까지 지우기, ⌘←/→ 줄 처음/끝

`python3 test_texter.py` 로 핵심 로직을 검사합니다.

## 설치

```bash
sh scripts/install.sh
```

`~/Applications/typad.app`이 생기고 바로 열립니다. 응용 프로그램 폴더로 끌어다 넣으려면 `dist/typad.dmg`를 여세요.

```bash
sh scripts/build-app.sh
open dist/typad.dmg
```

이 명령은 **이 Mac의 Homebrew Python**을 번들에 복사합니다. 다른 Mac으로 복사하거나 앱스토어에 올리는 빌드가 아닙니다.
앱 카테고리는 생산성, 번들 ID는 `ai.minseo.typad`입니다.

[GitHub Releases](https://github.com/mindsurf0176/typad/releases)에는 두 종류 빌드가 올라갑니다.

- `typad.app` / `typad.dmg`: 이 Mac에서 Developer ID 서명 + 공증(notarize) + staple까지 마친 빌드. Gatekeeper 경고 없이 바로 열립니다. 이 Mac의 Homebrew Python 3.14(tkinter 포함)가 있는 다른 Mac에서만 그대로 동작합니다. 다시 만들려면 `sh scripts/notarize.sh` (Developer ID 인증서 + `typad-notary` notarytool 키체인 프로파일 필요).
- `typad-standalone-macos.zip`: GitHub Actions에서 `py2app`으로 만든 완전 독립 실행형 빌드. 자체 Python·Tcl/Tk을 번들에 다 넣어서 **어떤 Mac에서든** Homebrew 없이 그대로 열립니다. `.github/workflows/build-standalone.yml`을 `gh workflow run build-standalone.yml`로 실행하거나 `v*` 태그를 올리면 새로 만들어집니다. 서명·공증까지 자동으로 하려면 GitHub 저장소 Settings → Secrets에 `MACOS_CERTIFICATE`/`MACOS_CERTIFICATE_PWD`/`MACOS_SIGNING_IDENTITY`, `NOTARY_KEY_ID`/`NOTARY_ISSUER_ID`/`NOTARY_KEY_P8`를 등록하세요.

Mac App Store 제출은 별도 트랙이며 [docs/app-store.md](docs/app-store.md)에 남은 게이트가 있습니다.

## 라이선스 / 개인정보

MIT. 파일은 이 Mac에만 남습니다. [PRIVACY.md](PRIVACY.md)
