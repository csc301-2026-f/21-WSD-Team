#!/bin/sh
# Install this release for the current user. No network or Python is needed.
set -eu
prefix="$HOME/.local"
if [ "$#" -gt 0 ]; then
    if [ "$#" -ne 2 ] || [ "$1" != "--prefix" ]; then
        echo "Usage: sh install.sh [--prefix /absolute/path]" >&2
        exit 1
    fi
    prefix="$2"
fi
case "$prefix" in /*) ;; *) echo "Prefix must be absolute." >&2; exit 1;; esac
if [ "$prefix" = / ]; then echo "Use a dedicated installation prefix." >&2; exit 1; fi
if [ "$(uname -m)" != x86_64 ]; then echo "This release requires x86-64 Linux." >&2; exit 1; fi
glibc=$(getconf GNU_LIBC_VERSION 2>/dev/null || true)
glibc=${glibc#glibc }
major=${glibc%%.*}
minor=${glibc#*.}
minor=${minor%%.*}
case "$major:$minor" in *[!0-9:]*|:*) echo "GNU glibc 2.39+ is required." >&2; exit 1;; esac
if [ "$major" -lt 2 ] || { [ "$major" -eq 2 ] && [ "$minor" -lt 39 ]; }; then
    echo "GNU glibc 2.39+ is required (Ubuntu 24.04 x86-64 is tested)." >&2
    exit 1
fi
source_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
destination="$prefix/lib/wsd/1.0.0"
launcher="$prefix/bin/wsd"
if [ -e "$destination" ] || [ -e "$launcher" ] || [ -L "$launcher" ]; then
    echo "An installation already exists. Choose another --prefix or review it before replacing." >&2
    exit 1
fi
mkdir -p "$prefix/lib/wsd" "$prefix/bin"
cp -R "$source_dir/app" "$destination"
ln -s "$destination/wsd" "$launcher"
printf 'Installed WSD 1.0.0. Start with:\n  "%s" --demo\n  "%s"\n' "$launcher" "$launcher"
echo 'Open http://127.0.0.1:5000/ after startup. Stop with Ctrl+C.'
