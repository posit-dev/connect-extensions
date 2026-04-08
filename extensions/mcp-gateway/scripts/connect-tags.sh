#!/usr/bin/env bash
# Debug script: search Connect tags, get a tag ID, list content with that tag.
#
# Usage:
#   export CONNECT_SERVER="https://your-connect-server.example.com"
#   export CONNECT_API_KEY="your-api-key"
#
#   ./scripts/connect-tags.sh                    # list all tags
#   ./scripts/connect-tags.sh mcp                # search tags matching "mcp"
#   ./scripts/connect-tags.sh --content TAG_ID   # list content for a tag ID

set -euo pipefail

SERVER="${CONNECT_SERVER:?Set CONNECT_SERVER}"
API_KEY="${CONNECT_API_KEY:?Set CONNECT_API_KEY}"
API="${SERVER%/}/__api__"

header="Authorization: Key ${API_KEY}"

# --- Functions ---

list_tags() {
    echo "=== All tags on ${SERVER} ==="
    curl -s -H "$header" "${API}/v1/tags" | python3 -m json.tool
}

search_tags() {
    local query="$1"
    echo "=== Tags matching \"${query}\" ==="
    curl -s -H "$header" "${API}/v1/tags" \
        | python3 -c "
import json, sys
tags = json.load(sys.stdin)
for t in tags:
    if '${query}'.lower() in t['name'].lower():
        parent = t.get('parent_id', '')
        print(f\"  id={t['id']}  name={t['name']}  parent_id={parent}\")
"
}

list_content_for_tag() {
    local tag_id="$1"
    echo "=== Content with tag ID ${tag_id} ==="
    curl -s -G -H "$header" "${API}/v1/tags/${tag_id}/content" \
        | python3 -c "
import json, sys
items = json.load(sys.stdin)
if not items:
    print('  (no content found)')
else:
    for item in items:
        guid = item.get('guid', '?')
        name = item.get('name', '') or item.get('title', '?')
        app_mode = item.get('app_mode', '?')
        url = item.get('content_url', '') or f'${SERVER}/content/{guid}/'
        print(f\"  guid={guid}\")
        print(f\"    name={name}\")
        print(f\"    app_mode={app_mode}\")
        print(f\"    url={url}\")
        print()
print(f'Total: {len(items)} item(s)')
"
}

# --- Main ---

if [[ $# -eq 0 ]]; then
    list_tags
elif [[ "$1" == "--content" && $# -ge 2 ]]; then
    list_content_for_tag "$2"
else
    search_tags "$1"
    echo ""
    echo "To list content for a tag, run:"
    echo "  $0 --content <TAG_ID>"
fi
