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

GitHub Releases는 소스 태그입니다. Mac App Store 제출은 [docs/app-store.md](docs/app-store.md) 게이트가 남아 있습니다.

## 라이선스 / 개인정보

MIT. 파일은 이 Mac에만 남습니다. [PRIVACY.md](PRIVACY.md)
