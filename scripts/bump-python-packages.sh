#!/usr/bin/env bash

# This script updates the requirements.txt of every Python extension by running
# uv pip compile on its source requirements: requirements.in if present,
# otherwise pyproject.toml.
#
# Dependencies are resolved universally, for every Python version from the
# minimum the extension declares in manifest.json (environment.python.requires)
# up. Where the newest release of a package doesn't support an older Python,
# requirements.txt gets a separate pin per Python version range, e.g.
#   starlette==0.49.3 ; python_full_version == '3.9.*'
#   starlette==1.8.0 ; python_full_version >= '3.10'
# so newer Pythons get current releases without breaking older ones.
#
# Any extra arguments passed to this script are forwarded to `uv pip compile`,
# e.g. `scripts/bump-python-packages.sh --no-upgrade` to refresh lockfiles
# without bumping pinned versions.

set -euo pipefail

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv is not installed. Please install it with 'pip install uv'."
    exit 1
fi

cd "$(dirname "$0")/.."

for manifest in extensions/*/manifest.json; do
    dir=$(dirname "$manifest")

    # Skip extensions that aren't Python content
    if [ "$(jq -r '.files["requirements.txt"] // empty' "$manifest")" = "" ]; then
        continue
    fi

    if [ -f "$dir/requirements.in" ]; then
        source_file=requirements.in
    elif [ -f "$dir/pyproject.toml" ]; then
        source_file=pyproject.toml
    else
        echo "WARNING: $dir has no requirements.in or pyproject.toml, skipping."
        continue
    fi

    # e.g. "~=3.9" -> "3.9"
    python_version=$(jq -r '.environment.python.requires // empty' "$manifest" | grep -oE '[0-9]+\.[0-9]+' | head -n 1 || true)
    if [ -z "$python_version" ]; then
        echo "WARNING: $manifest does not set environment.python.requires, skipping."
        continue
    fi

    echo "Compiling $dir/$source_file for Python $python_version"
    if ! (cd "$dir" && uv pip compile "$source_file" \
            --output-file requirements.txt \
            --universal \
            --python-version "$python_version" \
            --resolution highest \
            --upgrade \
            --custom-compile-command "scripts/bump-python-packages.sh" \
            "$@"); then
        echo "WARNING: could not compile $dir/$source_file, skipping."
    fi
done
