#!/bin/sh
set -e
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
APP="$ROOT/dist/Textpress.app"
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
/usr/libexec/PlistBuddy -c 'Set :CFBundleName Textpress' "$INNER_PLIST"
/usr/libexec/PlistBuddy -c 'Set :CFBundleIdentifier local.textpress' "$INNER_PLIST"
/usr/libexec/PlistBuddy -c 'Set :CFBundleIconFile AppIcon' "$INNER_PLIST"
/usr/libexec/PlistBuddy -c 'Add :CFBundleDisplayName string Textpress' "$INNER_PLIST" 2>/dev/null || /usr/libexec/PlistBuddy -c 'Set :CFBundleDisplayName Textpress' "$INNER_PLIST"
/usr/libexec/PlistBuddy -c 'Add :LSApplicationCategoryType string public.app-category.productivity' "$INNER_PLIST" 2>/dev/null || /usr/libexec/PlistBuddy -c 'Set :LSApplicationCategoryType public.app-category.productivity' "$INNER_PLIST"

cat > "$APP/Contents/MacOS/Textpress" << 'LAUNCH'
#!/bin/bash
DIR="$(cd "$(dirname "$0")" && pwd)"
export PYTHONEXECUTABLE="$DIR/Textpress"
exec "$DIR/../Resources/Python.app/Contents/MacOS/Python" "$DIR/../Resources/texter.py" "$@"
LAUNCH
chmod +x "$APP/Contents/MacOS/Textpress" "$APP/Contents/Resources/texter.py"

if command -v codesign >/dev/null; then
  codesign --force --deep -s - "$APP" >/dev/null
fi

DEST="$HOME/Applications/Textpress.app"
mkdir -p "$HOME/Applications"
rm -rf "$DEST" "$HOME/Applications/Texter.app"
cp -R "$APP" "$DEST"
echo "$APP"
echo "$DEST"
