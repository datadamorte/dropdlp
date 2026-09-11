#!/usr/bin/env bash
# Idempotent Cloud Agent bootstrap for dropdlp (PyQt5 desktop GUI around yt-dlp).
set -euo pipefail

cd "$(dirname "$0")/.."

# System packages: python venv support, ffmpeg (media merge/remux), and the
# X/XCB libraries the Qt "xcb" platform plugin dynamically loads so the GUI can
# render on a display.
if command -v sudo >/dev/null 2>&1; then
  APT="sudo apt-get"
else
  APT="apt-get"
fi

export DEBIAN_FRONTEND=noninteractive
$APT update -qq
$APT install -y --no-install-recommends \
  python3-venv \
  ffmpeg \
  libgl1 \
  libegl1 \
  libxkbcommon-x11-0 \
  libxcb-icccm4 \
  libxcb-image0 \
  libxcb-keysyms1 \
  libxcb-render-util0 \
  libxcb-xinerama0 \
  libxcb-xkb1 \
  libxcb-cursor0

# Python virtual environment + project dependencies.
if [ ! -x venv/bin/python ]; then
  python3 -m venv venv
fi
# shellcheck disable=SC1091
source venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt

echo "dropdlp environment ready."
