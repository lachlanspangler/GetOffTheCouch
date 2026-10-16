#!/usr/bin/env bash
# Build the self-hosted web fonts (DESIGN.md §2.2). One-off; outputs are committed.
#
#   scripts/build_fonts.sh
#
# Downloads Inter[opsz,wght] and Newsreader[opsz,wght] from google/fonts, pins opsz, trims wght,
# subsets to Latin + typographic punctuation and writes woff2 + OFL licenses to web/public/fonts/.
# Budget: <= 80 KB total for both files (both are preloaded).
#
# fontTools gotcha: instancing and subsetting must not share one in-memory TTFont (gvar KeyError).
# We run them as separate processes, so the instanced font is always saved and reloaded from disk.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
OUT="$ROOT/web/public/fonts"
RAW="https://raw.githubusercontent.com/google/fonts/main/ofl"

WORK="$(mktemp -d)"
trap 'rm -rf "$WORK"' EXIT
DL="$WORK/download"   # untrusted downloads live alone in their own dir
BUILD="$WORK/build"
mkdir -p "$DL" "$BUILD" "$OUT"

# fontTools + brotli (woff2): use the current python if it already has both, else a throwaway venv.
PY="${PYTHON:-python3}"
if ! "$PY" -I -c "import fontTools, brotli" 2>/dev/null; then
  echo "==> creating temp venv with fonttools + brotli"
  "$PY" -m venv "$WORK/venv"
  "$WORK/venv/bin/python" -I -m pip install --quiet --disable-pip-version-check fonttools brotli
  PY="$WORK/venv/bin/python"
fi

fetch() { # url dest
  curl --fail --silent --show-error --location --retry 3 -o "$2" "$1"
}

echo "==> downloading from google/fonts"
fetch "$RAW/inter/Inter%5Bopsz%2Cwght%5D.ttf" "$DL/Inter-VF.ttf"
fetch "$RAW/inter/OFL.txt" "$DL/OFL-Inter.txt"
fetch "$RAW/newsreader/Newsreader%5Bopsz%2Cwght%5D.ttf" "$DL/Newsreader-VF.ttf"
fetch "$RAW/newsreader/OFL.txt" "$DL/OFL-Newsreader.txt"

UNI="U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+2000-206F,U+2074,U+20AC,U+2122,U+2190-2199,U+2212,U+2215,U+FEFF,U+FFFD"
FEAT="kern,liga,calt,tnum,case,ccmp,locl,mark,mkmk,frac,sups"

# Run tools from the build dir (never from the download dir), isolated (-I).
cd "$BUILD"

build() { # src out axis=value...
  local src="$1" out="$2" inst="$BUILD/$(basename "$2" .woff2)-inst.ttf"; shift 2
  echo "==> instancing $(basename "$src") $*"
  "$PY" -I -m fontTools.varLib.instancer "$src" "$@" -o "$inst" -q
  echo "==> subsetting -> $(basename "$out")"
  "$PY" -I -m fontTools.subset "$inst" --unicodes="$UNI" --layout-features="$FEAT" \
    --flavor=woff2 --desubroutinize --output-file="$out"
}

build "$DL/Inter-VF.ttf"      "$OUT/inter-latin-var.woff2"      opsz=14 wght=400:700
build "$DL/Newsreader-VF.ttf" "$OUT/newsreader-latin-var.woff2" opsz=36 wght=400:600

cp "$DL/OFL-Inter.txt" "$OUT/OFL-Inter.txt"
cp "$DL/OFL-Newsreader.txt" "$OUT/OFL-Newsreader.txt"

kb() { awk -v b="$1" 'BEGIN { printf "%.1f", b / 1024 }'; }
total=0
for f in "$OUT/inter-latin-var.woff2" "$OUT/newsreader-latin-var.woff2"; do
  b=$(wc -c < "$f" | tr -d ' ')
  total=$((total + b))
  printf '%-32s %6d bytes (%s KB)\n' "$(basename "$f")" "$b" "$(kb "$b")"
done
printf '%-32s %6d bytes (%s KB)\n' "total" "$total" "$(kb "$total")"
if [ "$total" -gt $((80 * 1024)) ]; then
  echo "!! over the 80 KB font budget (DESIGN.md §2.2)" >&2
  exit 1
fi
