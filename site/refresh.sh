#!/usr/bin/env bash
# Refresh both static sites from a new live detector run, ready for Vercel.
#   bash site/refresh.sh   then commit site/data and andrew-site/public and push.
set -euo pipefail
cd "$(dirname "$0")/.."
python scripts/detect.py                       # live feeds -> data/latest_run.json
python site/build_data.py                      # site 1 -> site/data/run.json
python andrew-site/build.py                    # site 2 -> andrew-site/build/index.html
mkdir -p andrew-site/public
cp andrew-site/build/index.html andrew-site/public/index.html   # committed snapshot Vercel serves
