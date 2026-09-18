#!/bin/sh
set -e
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
APP="$ROOT/dist/typad.app"
PY="$(/usr/bin/python3 -c 'import sys; print(sys.executable)' 2>/dev/null || true)"
# Prefer the interpreter that actually has tkinter (Homebrew on this machine).
for cand in /opt/homebrew/bin/python3 /usr/local/bin/python3 "$PY"; do
  if [ -n "$cand" ] && "$cand" -c "import tkinter" 2>/dev/null; then
    PY="$cand"
    break
  fi
done
if ! "$PY" -c "import tkinter" 2>/dev/null; then
  echo "python with tkinter not found" >&2
  exit 1
fi

"$PY" "$ROOT/scripts/make_icon.py"

PYAPP_SRC="$("$PY" -c 'import sys, pathlib; print(pathlib.Path(sys.base_prefix) / "Resources" / "Python.app")')"
if [ ! -x "$PYAPP_SRC/Contents/MacOS/Python" ]; then
  echo "Python.app not found at $PYAPP_SRC" >&2
  exit 1
fi

if [ -d "$APP" ]; then
  chmod -R u+rwX "$APP" 2>/dev/null || true
fi
rm -rf "$APP"
mkdir -p "$APP/Contents/MacOS" "$APP/Contents/Resources"
cp "$ROOT/texter.py" "$ROOT/core.py" "$APP/Contents/Resources/"
cp "$ROOT/scripts/Info.plist" "$APP/Contents/Info.plist"
if [ -f "$ROOT/dist/AppIcon.icns" ]; then
  cp "$ROOT/dist/AppIcon.icns" "$APP/Contents/Resources/AppIcon.icns"
fi

cp -R "$PYAPP_SRC" "$APP/Contents/Resources/Python.app"
if [ -f "$ROOT/dist/AppIcon.icns" ]; then
  cp "$ROOT/dist/AppIcon.icns" "$APP/Contents/Resources/Python.app/Contents/Resources/AppIcon.icns"
fi

INNER_PLIST="$APP/Contents/Resources/Python.app/Contents/Info.plist"
/usr/libexec/PlistBuddy -c 'Set :CFBundleName typad' "$INNER_PLIST"
/usr/libexec/PlistBuddy -c 'Set :CFBundleIdentifier ai.minseo.typad' "$INNER_PLIST"
/usr/libexec/PlistBuddy -c 'Set :CFBundleIconFile AppIcon' "$INNER_PLIST"
/usr/libexec/PlistBuddy -c 'Add :CFBundleDisplayName string typad' "$INNER_PLIST" 2>/dev/null || /usr/libexec/PlistBuddy -c 'Set :CFBundleDisplayName typad' "$INNER_PLIST"
/usr/libexec/PlistBuddy -c 'Add :LSApplicationCategoryType string public.app-category.productivity' "$INNER_PLIST" 2>/dev/null || /usr/libexec/PlistBuddy -c 'Set :LSApplicationCategoryType public.app-category.productivity' "$INNER_PLIST"

cat > "$APP/Contents/MacOS/typad" << 'LAUNCH'
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONEXECUTABLE="$DIR/typad"
exec "$DIR/../Resources/Python.app/Contents/MacOS/Python" "$DIR/../Resources/texter.py" "$@"
LAUNCH
chmod +x "$APP/Contents/MacOS/typad" "$APP/Contents/Resources/texter.py"

ENTITLEMENTS="$ROOT/scripts/runtime.entitlements"
if [ -n "${SIGNING_IDENTITY:-}" ]; then
  # Real Developer ID signing for notarization: hardened runtime + secure
  # timestamp + library-validation disabled (the app loads Homebrew's
  # Python/Tcl/Tk dylibs, which carry a different Team ID).
  codesign --force --deep --options runtime --timestamp \
    --entitlements "$ENTITLEMENTS" --sign "$SIGNING_IDENTITY" "$APP"
else
  codesign --force --deep -s - "$APP" >/dev/null
fi

DEST="$HOME/Applications/typad.app"
mkdir -p "$HOME/Applications"
rm -rf "$DEST" "$HOME/Applications/txtr.app" "$HOME/Applications/Textpress.app" "$HOME/Applications/Texter.app"
cp -R "$APP" "$DEST"
echo "$APP"
echo "$DEST"

ZIP="$ROOT/dist/typad-macos-arm64.zip"
rm -f "$ZIP"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"
STAGE="$ROOT/dist/dmg-stage"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/typad.app"
ln -sf /Applications "$STAGE/Applications"
DMG="$ROOT/dist/typad.dmg"
rm -f "$DMG"
hdiutil create -volname typad -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null
echo "$ZIP"
echo "$DMG"
