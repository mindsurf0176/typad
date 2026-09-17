# txtr

Notepad++처럼 가볍고, 탭·문법 강조·찾기/바꾸기·폴더 워크스페이스가 있는 텍스트 에디터.
의존성 없음. Python 3 표준 라이브러리(`tkinter`)만 사용합니다.

## 실행

```bash
python3 texter.py
python3 texter.py README.md
python3 texter.py /path/to/folder
```

설정과 마지막 세션은 `~/.txtr.json`에 저장됩니다. 예전 `~/.textpress.json` / `~/.texter.json`이 있으면 그대로 읽어 옵니다.

## 기능

- 탭, 저장 확인, UTF-8/CP949, LF/CRLF
- 확장자 기준 문법 강조
- 찾기/바꾸기(정규식), 폴더에서 찾기
- 줄 번호, 현재 줄, 괄호 짝, 북마크
- 주석 토글, 줄 복제/이동/삭제, 자동 들여쓰기
- 폴더 트리, 최근 파일, 세션 복원
- 어두운/밝은 테마, 확대/축소

`python3 test_texter.py` 로 핵심 로직을 검사합니다.

## macOS 앱

```bash
sh scripts/build-app.sh
open ~/Applications/txtr.app
```

Finder에서 만든 `.app`은 이 맥의 Homebrew Python(tkinter 포함)을 번들 안으로 복사합니다. 다른 맥으로 복사해서 쓰는 포터블 빌드는 아닙니다. 대상 맥에서 `sh scripts/build-app.sh`를 다시 실행하세요.

설정은 ⌘, 또는 파일 → 설정. 편집기 글꼴·크기, 화면 글자 크기, 탭 너비, 테마, 줄 번호, 문법 강조, 세션 복원을 바로 적용합니다.

앱 카테고리는 생산성입니다.

소스: https://github.com/mindsurf0176/txtr
