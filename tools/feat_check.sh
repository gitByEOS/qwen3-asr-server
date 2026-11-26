#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
exec bash /Users/bole/.cursor/skills/feat-verify/scripts/feat_check.sh "$ROOT"
