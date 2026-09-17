#!/bin/sh
set -e
ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)"
sh "$ROOT/scripts/build-app.sh"
open "$HOME/Applications/typad.app"
