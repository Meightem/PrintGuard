#!/bin/sh
set -eu

python -m piptools compile \
  pyproject.toml \
  --all-extras \
  --strip-extras \
  --resolver=backtracking \
  --output-file constraints.lock
