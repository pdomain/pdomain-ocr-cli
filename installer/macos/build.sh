#!/bin/sh
set -eu

source_dir=$(CDPATH='' cd -- "$(dirname -- "$0")" && pwd)
root=$(CDPATH='' cd -- "$source_dir/../.." && pwd)
case "${1:-}" in
    *[!v0-9.]*) set -- ;;
esac
if [ "$#" -lt 1 ] || [ "$#" -gt 2 ] ||
    ! printf '%s\n' "$1" | grep -Eq '^v[0-9]+\.[0-9]+\.[0-9]+$'; then
    printf '%s\n' 'Usage: build.sh vMAJOR.MINOR.PATCH [output-directory]' >&2
    exit 2
fi
if [ "$(uname -s)" != Darwin ]; then
    printf '%s\n' 'Building the AppKit setup app requires macOS and Xcode Command Line Tools.' >&2
    exit 1
fi

release=$1
out=${2:-"$root/dist/macos-setup"}
mkdir -p "$out"
out=$(CDPATH='' cd -- "$out" && pwd)
name='Install OCR CLI.app'
archive="OCR-CLI-Setup-$release.zip"
if [ -e "$out/$name" ] || [ -L "$out/$name" ] || [ -e "$out/$archive" ] || [ -L "$out/$archive" ]; then
    printf '%s\n' 'Choose a fresh output directory for this build.' >&2
    exit 1
fi

stage=$(mktemp -d "$out/.build.XXXXXX")
trap 'rm -rf "$stage"' EXIT
trap 'exit 1' HUP INT TERM
bundle="$stage/$name"
contents="$bundle/Contents"
payload="$contents/Resources/payload"
mkdir -p "$contents/MacOS" "$payload"
cp "$root/install.sh" "$source_dir/setup-worker.sh" "$payload/"
printf '%s\n' "$release" >"$payload/release-tag"
cat >"$contents/Info.plist" <<PLIST
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
<key>CFBundleName</key><string>Install OCR CLI</string>
<key>CFBundleIdentifier</key><string>org.pdomain.ocr-cli.installer</string>
<key>CFBundleExecutable</key><string>Setup</string>
<key>CFBundlePackageType</key><string>APPL</string>
<key>CFBundleVersion</key><string>${release#v}</string>
<key>CFBundleShortVersionString</key><string>${release#v}</string>
<key>LSMinimumSystemVersion</key><string>14.0</string>
</dict>
</plist>
PLIST
/usr/bin/plutil -lint "$contents/Info.plist"
/usr/bin/xcrun --sdk macosx swiftc -swift-version 5 -target arm64-apple-macos14.0 \
    "$source_dir/Setup.swift" -o "$contents/MacOS/Setup"
/usr/bin/codesign --force --sign - "$bundle"
/usr/bin/codesign --verify --strict "$bundle"
/usr/bin/ditto -c -k --keepParent "$bundle" "$stage/$archive"
mv "$bundle" "$out/$name"
mv "$stage/$archive" "$out/$archive"
printf '%s\n' "$out/$name" "$out/$archive"
