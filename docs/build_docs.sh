#!/usr/bin/env bash
# Convert all Markdown under docs/ to PDFs under workspace dist/, mirroring paths.
set -euo pipefail

DOCS_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WS_ROOT="$(cd "${DOCS_ROOT}/.." && pwd)"
DIST="${WS_ROOT}/dist"

if ! command -v pandoc >/dev/null 2>&1; then
  echo "error: pandoc is required but not found in PATH" >&2
  exit 1
fi

mkdir -p "${DIST}"

mapfile -d '' -t MD_FILES < <(find "${DOCS_ROOT}" -type f -name '*.md' -print0 | sort -z)

if [[ ${#MD_FILES[@]} -eq 0 ]]; then
  echo "no .md files under ${DOCS_ROOT}" >&2
  exit 0
fi

for f in "${MD_FILES[@]}"; do
  rel="${f#"${DOCS_ROOT}/"}"
  out_dir="${DIST}/$(dirname "${rel}")"
  base="$(basename "${rel}" .md)"
  mkdir -p "${out_dir}"
  pandoc "${f}" -o "${out_dir}/${base}.pdf"
done

echo "Wrote PDFs under ${DIST}/ (mirrors docs/ layout)."
