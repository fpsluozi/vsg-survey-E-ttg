#!/usr/bin/env bash
# VSG Human Survey E (ttg) -> http://localhost:8505
set -e
cd "$(dirname "$0")"
exec streamlit run app.py --server.port "${PORT:-8505}" --server.address localhost \
     --browser.gatherUsageStats false
