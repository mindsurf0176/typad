# Mac App Store prep

Local source and GitHub Releases are the current distribution. This file is the App Store listing draft and the remaining Apple gates. Nothing here means the app is on the store.

## Listing draft

- Name: typad
- Subtitle: 가벼운 텍스트 에디터
- Category: Productivity (`public.app-category.productivity`)
- Bundle ID: `ai.minseo.typad`
- SKU: typad
- Age: 4+
- Price: Free
- Copyright: 2026 Minseo Lee
- Encryption: ITSAppUsesNonExemptEncryption = false

### Description (KO)

Notepad++처럼 가볍고, 탭과 문법 강조가 있는 로컬 텍스트 에디터입니다. 인터넷 없이 파일을 열고 저장합니다.

- 탭, UTF-8/CP949, LF/CRLF
- 확장자 기준 문법 강조
- 찾기/바꾸기, 폴더에서 찾기
- 줄 번호, 북마크, 주석 토글
- 어두운/밝은 테마, 화면 글자 크기

설정은 이 Mac의 Application Support에만 남습니다.

### Description (EN)

A lightweight local text editor with tabs and syntax highlighting. Open and save files without an account or network.

### Keywords

text,editor,code,notepad,markdown,syntax,korean

### Privacy nutrition label

Data Not Collected.

## Signed identities on this Mac

Developer ID Application and Apple Distribution certificates for MINSEO LEE (74Q37UBA68) are installed. `scripts/notarize.sh` uses the Developer ID Application identity plus a notarytool keychain profile (`typad-notary`, backed by an existing App Store Connect API key) to sign with hardened runtime, submit to Apple's notary service, and staple the ticket. GitHub Releases v0.2.1 now ships a notarized, stapled `typad.app`/`typad.dmg` — `spctl --assess` reports `source=Notarized Developer ID`. App Store Connect submission (a separate track from notarized direct distribution) still needs an app record, screenshots, and a sandboxed standalone build.

## Remaining gates (not done)

1. ~~Standalone runtime~~ — done. Two dead ends on this Mac's local shell first: a hand-rolled relocatable bundle hung inside dyld at launch, and `py2app` could not even install here (this shell's `platform.mac_ver()` returns `""`, which crashes pip's `truststore`; separately, Homebrew's `python@3.13`/`python@3.14` both have a `pyexpat` missing `_XML_SetAllocTrackerActivationThreshold`). Root cause turned out to be the shell itself: `codesign --verify --strict` here rejects even an untouched copy of Apple's own `/System/Library/Frameworks/CoreFoundation.framework` ("bundle format is ambiguous"), which is not something fixable from this repo.
   `.github/workflows/build-standalone.yml` builds with `py2app` on a real GitHub Actions macOS runner instead. First real run (`gh run 35358327816`) succeeded end to end: `typad.app` vendors its own `Python.framework`, `_tkinter.so`, `libtcl8.6.dylib`/`libtk8.6.dylib`, `libssl`/`libcrypto` — zero `/opt/homebrew` or `/usr/local` references (checked with `otool -L` over every Mach-O in the bundle). Downloaded the artifact and confirmed on this Mac: `codesign --verify --deep --strict` passes cleanly, `open`ing it launches a real window, and both `name` and `displayed name` read `typad` (no "Python" menu-bar bug at all, since py2app's main executable is literally named `typad`). The workflow signs with Developer ID and notarizes automatically once `MACOS_CERTIFICATE`/`MACOS_CERTIFICATE_PWD`/`MACOS_SIGNING_IDENTITY` and `NOTARY_KEY_ID`/`NOTARY_ISSUER_ID`/`NOTARY_KEY_P8` repo secrets are set (add those in GitHub repo Settings → Secrets, never here); without them it ships ad-hoc signed, as the first run did. Trigger with `gh workflow run build-standalone.yml` or a `v*` tag push.
2. ~~Sandbox file access~~ — done for the part that actually breaks under sandbox. tkinter's native open/save panels already grant in-process access to whatever the user picks (that part just works), but *persisted* access across relaunches did not: session restore, the recent-files list, and the last browsed folder all re-touch paths the sandbox has since forgotten. `core.py` now creates a security-scoped bookmark (`make_bookmark`) right after every successful open/save/open-folder and resolves+holds it (`ScopedAccess`) for as long as that tab or folder stays open; both are no-ops outside the sandbox, so every other build is unaffected.
   - Verified twice. On this Mac (PyObjC's Cocoa bridge happens to be installed here): `test_security_scoped_bookmark_roundtrip` creates/resolves/starts/stops a genuine `NSURL` bookmark, and `test_session_restore_reopens_via_bookmark` opens a file, persists, destroys the app, creates a *second* `App` instance against that same config, and confirms it reopens the file and the content matches.
   - On a clean GitHub Actions macOS runner (`gh run 35360069086`, `build-sandboxed` job): fresh `pip install py2app pyobjc-framework-Cocoa`, re-ran the exact same tests (pass), built the App Sandbox variant (`TYPAD_SANDBOX=1 python3 setup.py py2app`), ad-hoc signed it with `scripts/typad.entitlements`, and confirmed with `codesign -d --entitlements :-` that `com.apple.security.app-sandbox` is genuinely embedded in the signed binary.
   - Not yet verified: full interactive sandbox enforcement (Apple's Transparency/Consent prompts, an actual provisioning-profile-backed sandboxed launch on a real device/account). That needs a real TestFlight/App Store Connect build, which is gate 3 below.
3. App Store Connect — create the app with bundle id `ai.minseo.typad`, upload 1280x800 (or 2560x1600) screenshots, attach this privacy policy URL.
4. Review submit — Apple Distribution signed pkg/ipa via Transporter. Not started.
5. ~~Notarization~~ — done for direct distribution (see `scripts/notarize.sh` above). Not the same as an App Store Connect submission, which is a separate, still-not-started track (gates 2-4).
6. Interactive click QA — AppleScript/System Events UI automation from this shell hangs waiting on an Accessibility/Automation permission prompt that nothing can dismiss headlessly. `test_texter.py`'s GUI smoke test (creates a real Tk window, exercises tabs/search/comments, closes cleanly) passes, and both the notarized Homebrew-linked build and the new standalone CI build launch and show the correct `typad` name via `open`, but no one has clicked through Settings, dialogs, or shortcuts by hand yet.

Entitlements: `scripts/runtime.entitlements` (hardened runtime, library validation disabled for Homebrew's dylibs) is what actually ships, signed and notarized. `scripts/typad.entitlements` (app sandbox + user-selected files) is only a draft for a future App Store submission; the notarized direct-distribution build is intentionally not sandboxed.
