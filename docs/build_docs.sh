#!/bin/bash
# build_docs.sh — Convert all Markdown docs to PDF
# Usage: bash docs/build_docs.sh
# Requires: pandoc + texlive (or wkhtmltopdf as fallback)

set -euo pipefail

DOCS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
OUT_DIR="$DOCS_DIR/_pdf_output"
mkdir -p "$OUT_DIR"

if ! command -v pandoc &> /dev/null; then
  echo "ERROR: pandoc not found. Install with: sudo apt install pandoc texlive-latex-base texlive-fonts-recommended"
  exit 1
fi

echo "Building docs from $DOCS_DIR → $OUT_DIR"
echo ""

count=0
errors=0

while IFS= read -r md_file; do
  rel_path="${md_file#$DOCS_DIR/}"
  out_name="${rel_path//\//__}"
  out_name="${out_name%.md}.pdf"
  out_path="$OUT_DIR/$out_name"

  echo -n "  $rel_path ... "
  if pandoc "$md_file" \
    -o "$out_path" \
    --pdf-engine=xelatex \
    -V geometry:margin=2cm \
    -V fontsize=10pt \
    -V colorlinks=true \
    --toc \
    2>/dev/null; then
    echo "OK"
    count=$((count + 1))
  else
    echo "FAIL"
    errors=$((errors + 1))
  fi
done < <(find "$DOCS_DIR" -name "*.md" ! -path "*/_*" | sort)

echo ""
echo "Done: $count PDF(s) generated, $errors error(s)"
echo "Output: $OUT_DIR"
