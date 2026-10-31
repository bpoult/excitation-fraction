#!/bin/bash
# Build the standalone macOS app (macOS 26+, Apple silicon) and zip it for distribution.
# Run from a shell where the project's Python env is active, then: ./build_macos.sh
# Output: dist/ExcitationFraction-macos-arm64.zip
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/4] Cleaning previous build..."
rm -rf build dist

echo "[2/4] Checking build dependencies..."
python -c "import PyInstaller, webview, WebKit" 2>/dev/null || {
  echo "PyInstaller/pywebview not found. Run: pip install -r requirements-build.txt"
  exit 1
}

echo "[3/4] Running PyInstaller..."
pyinstaller ExcitationFraction.spec --noconfirm --clean --log-level WARN

# PyInstaller ad-hoc signs the bundle; re-sign the whole .app so the seal is
# consistent (not notarized — first launch needs "Open Anyway", see README).
codesign --force --deep --sign - dist/ExcitationFraction.app

echo "[4/4] Zipping dist/ExcitationFraction.app ..."
# ditto keeps the bundle's symlinks and code signature intact (zip -r does not).
ditto -c -k --keepParent dist/ExcitationFraction.app dist/ExcitationFraction-macos-arm64.zip

echo "Done: dist/ExcitationFraction-macos-arm64.zip ($(du -h dist/ExcitationFraction-macos-arm64.zip | cut -f1))"
