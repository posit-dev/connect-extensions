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
# Each extension whose requirements.txt changes also gets a patch version bump
# in manifest.json (e.g. 1.0.3 -> 1.0.4), so the update is released on merge.
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
        continue
    fi

    # If requirements.txt changed, bump the extension's patch version so the
    # update is released on merge. Skip if manifest.json already has
    # uncommitted changes, so rerunning the script doesn't bump twice.
    if ! git diff --quiet HEAD -- "$dir/requirements.txt" && git diff --quiet HEAD -- "$manifest"; then
        old_version=$(jq -r '.extension.version' "$manifest")
        new_version=$(echo "$old_version" | awk -F. '{ print $1 "." $2 "." $3 + 1 }')
        echo "Bumping $dir extension version $old_version -> $new_version"
        # Edit in place with sed rather than jq to preserve the file's formatting
        sed -E -i.bak "/\"extension\": *\{/,/\"version\":/ s/(\"version\": *)\"$old_version\"/\1\"$new_version\"/" "$manifest"
        rm "$manifest.bak"
    fi
done
