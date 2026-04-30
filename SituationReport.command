#!/bin/bash
set -e
cd "$(dirname "$0")"
if [ -f ".venv/bin/python" ]; then
    .venv/bin/python -m launcher
else
    python3 -m launcher
fi
