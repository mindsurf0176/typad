#!/bin/sh
set -e
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
APP="$ROOT/dist/typad.app"

: "${SIGNING_IDENTITY:=Developer ID Application: MINSEO LEE (74Q37UBA68)}"
: "${NOTARY_PROFILE:=typad-notary}"
export SIGNING_IDENTITY

echo "Building and signing with: $SIGNING_IDENTITY"
sh "$ROOT/scripts/build-app.sh" >/dev/null

echo "codesign --verify (deep, strict)"
codesign --verify --deep --strict --verbose=2 "$APP"

ZIP="$ROOT/dist/typad-notarize.zip"
rm -f "$ZIP"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$ZIP"

echo "Submitting to notarytool (profile: $NOTARY_PROFILE)"
xcrun notarytool submit "$ZIP" --keychain-profile "$NOTARY_PROFILE" --wait

echo "Stapling ticket"
xcrun stapler staple "$APP"
xcrun stapler validate "$APP"

echo "Gatekeeper assessment"
spctl --assess --type execute --verbose=2 "$APP"

DEST="$HOME/Applications/typad.app"
mkdir -p "$HOME/Applications"
if [ -d "$DEST" ]; then
  chmod -R u+rwX "$DEST" 2>/dev/null || true
fi
rm -rf "$DEST"
cp -R "$APP" "$DEST"

FINAL_ZIP="$ROOT/dist/typad-macos-arm64.zip"
rm -f "$FINAL_ZIP"
ditto -c -k --sequesterRsrc --keepParent "$APP" "$FINAL_ZIP"

STAGE="$ROOT/dist/dmg-stage"
rm -rf "$STAGE"
mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/typad.app"
ln -sf /Applications "$STAGE/Applications"
DMG="$ROOT/dist/typad.dmg"
rm -f "$DMG"
hdiutil create -volname typad -srcfolder "$STAGE" -ov -format UDZO "$DMG" >/dev/null

echo "Signing and notarizing the disk image"
codesign --force --timestamp --sign "$SIGNING_IDENTITY" "$DMG"
xcrun notarytool submit "$DMG" --keychain-profile "$NOTARY_PROFILE" --wait
xcrun stapler staple "$DMG"
xcrun stapler validate "$DMG"

echo "Done."
echo "$APP"
echo "$DEST"
echo "$FINAL_ZIP"
echo "$DMG"

