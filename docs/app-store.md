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

1. Standalone runtime — current `typad.app` copies this Mac's Homebrew Python.app rather than vendoring a relocatable copy. A relocatable-bundle attempt (rewriting Mach-O linkage with install_name_tool and re-signing) got through build and static verification, but the resulting binary hung inside dyld at launch (confirmed via `sample`: stuck in `isMachO`/shared-cache resolution before `main()` ever ran). That approach was abandoned rather than shipped broken. `py2app` — the standard tool for this — could not be installed either: this machine's `platform.mac_ver()` returns an empty string in some shells, which crashes pip's bundled `truststore` SSL backend during `pip install`, and get-pip.py's own bootstrap pip additionally hits an unrelated `_prevent_import_hook` ImportError on Python 3.14. Other Macs and App Store review will not accept a Homebrew-linked binary.
   - Update: retried with a corrected sign-inside-out order (see the notarization fix below) and hit a *different*, more fundamental wall: `codesign --verify --strict` fails with bogus errors ("No such file or directory", "bundle format is ambiguous") even on a completely untouched copy of the framework, and even on Apple's own `/System/Library/Frameworks/CoreFoundation.framework` — proving this exec shell's `codesign`/bundle-verification tooling itself misbehaves for Versions/Current-style framework bundles, independent of anything in this repo. `py2app` also failed a second way on this Mac: Homebrew's `python@3.13`/`python@3.14` both have a broken `pyexpat` (missing `_XML_SetAllocTrackerActivationThreshold` symbol against `/usr/lib/libexpat.1.dylib`), which pip's vendored `distlib` needs at import time. Building this from a normal Terminal.app session (outside this automation shell) may not hit either issue.
   - Working around both: `.github/workflows/build-standalone.yml` builds with `py2app` on a real GitHub Actions macOS runner (no Homebrew, no sandboxed shell), which sidesteps every issue above. It signs with Developer ID and notarizes automatically once `MACOS_CERTIFICATE`/`MACOS_CERTIFICATE_PWD`/`MACOS_SIGNING_IDENTITY` and `NOTARY_KEY_ID`/`NOTARY_ISSUER_ID`/`NOTARY_KEY_P8` repo secrets are set; without them it ships an ad-hoc-signed build. Trigger with `gh workflow run build-standalone.yml` or by pushing a `v*` tag.
2. Sandbox file access — tkinter file dialogs do not create security-scoped bookmarks. Sandboxed open/save needs NSOpenPanel/NSSavePanel (PyObjC or a native wrapper) before review.
3. App Store Connect — create the app with bundle id `ai.minseo.typad`, upload 1280x800 (or 2560x1600) screenshots, attach this privacy policy URL.
4. Review submit — Apple Distribution signed pkg/ipa via Transporter. Not started.
5. ~~Notarization~~ — done for direct distribution (see above). Not the same as an App Store Connect submission, which is a separate, still-not-started track (gates 2-4).
6. Interactive click QA — AppleScript/System Events UI automation from this shell hangs waiting on an Accessibility/Automation permission prompt that nothing can dismiss headlessly. `test_texter.py`'s GUI smoke test (creates a real Tk window, exercises tabs/search/comments, closes cleanly) passes, and the packaged app launches and shows the correct `typad` menu-bar name via `open`, but no one has clicked through Settings, dialogs, or shortcuts by hand yet.

Entitlements: `scripts/runtime.entitlements` (hardened runtime, library validation disabled for Homebrew's dylibs) is what actually ships, signed and notarized. `scripts/typad.entitlements` (app sandbox + user-selected files) is only a draft for a future App Store submission; the notarized direct-distribution build is intentionally not sandboxed.
