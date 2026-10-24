#!/usr/bin/env bash
set -euo pipefail

.venv/bin/python scripts/export_openapi.py
npx --no-install openapi-typescript gapmap/shared/contracts/openapi.json -o gapmap/shared/contracts/api.d.ts
