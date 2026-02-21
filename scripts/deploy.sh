#!/bin/bash
# Quick deploy script — commits and pushes all changes
cd "$(dirname "$0")/.."
git add -A
git commit -m "Site update: $(date '+%Y-%m-%d %H:%M')" || exit 0
git push
