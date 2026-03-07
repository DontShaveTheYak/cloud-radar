#!/bin/bash

set -e

PYPROJECT="/workspaces/cloud-radar/pyproject.toml"

# Install all Python versions listed in pyproject.toml
declare -a FULL_VERSIONS
while IFS= read -r version; do
    full=$(pyenv latest --known "$version")
    pyenv install -s "$full"
    FULL_VERSIONS+=("$full")
done < <(python3 -c "
import tomllib
with open('$PYPROJECT', 'rb') as f:
    data = tomllib.load(f)
for v in data['tool']['cloud-radar']['python-versions']:
    print(v)
")

# Set pyenv global: default-python first, then the rest
DEFAULT_MINOR=$(python3 -c "
import tomllib
with open('$PYPROJECT', 'rb') as f:
    data = tomllib.load(f)
print(data['tool']['cloud-radar']['default-python'])
")
DEFAULT_FULL=$(pyenv latest --known "$DEFAULT_MINOR")
GLOBAL="$DEFAULT_FULL"
for full in "${FULL_VERSIONS[@]}"; do
    [[ "$full" != "$DEFAULT_FULL" ]] && GLOBAL+=" $full"
done

# shellcheck disable=SC2086
pyenv global $GLOBAL
pyenv rehash
