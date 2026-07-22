"""
DAG Validation and Layout

This module handles DAG validation, topological sorting, and automatic layout algorithms.
Backend-agnostic DAG processing logic.
"""

from typing import List, Dict, Any
import collections
import logging

logger = logging.getLogger(__name__)


def validate_dag(nodes: List[Dict], edges: List[Dict]) -> Dict[str, Any]:
    """Validate the DAG for cycles and connectivity."""
    if not nodes:
        return {"isValid": True, "errors": []}

    errors = []

    # Build adjacency list
    adj_list = {node["id"]: [] for node in nodes}
    for edge in edges:
        if edge["source"] in adj_list and edge["target"] in adj_list:
            adj_list[edge["source"]].append(edge["target"])

    # Check for cycles using DFS
    def has_cycle():
        visited = set()
        rec_stack = set()

        def dfs(node):
            visited.add(node)
            rec_stack.add(node)

            for neighbor in adj_list[node]:
                if neighbor not in visited:
                    if dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True

            rec_stack.remove(node)
            return False

        for node_id in adj_list:
            if node_id not in visited:
                if dfs(node_id):
                    return True
        return False

    if has_cycle():
        errors.append("DAG contains cycles")

    # Check for disconnected components (if more than one node)
    if len(nodes) > 1:
        # Find all connected components
        visited = set()
        components = 0

        def dfs_undirected(node, component):
            visited.add(node)
            component.add(node)

            # Check both incoming and outgoing edges
            for edge in edges:
                if edge["source"] == node and edge["target"] not in visited:
                    dfs_undirected(edge["target"], component)
                elif edge["target"] == node and edge["source"] not in visited:
                    dfs_undirected(edge["source"], component)

        for node in nodes:
            node_id = node["id"]
            if node_id not in visited:
                component = set()
                dfs_undirected(node_id, component)
                components += 1

        if components > 1:
            errors.append("DAG has disconnected components")

    return {
        "isValid": len(errors) == 0,
        "errors": errors
    }


def topological_sort_in_batches(nodes: List[Dict[str, Any]], edges: List[Dict[str, str]]) -> List[List[Dict[str, Any]]]:
    """
    Performs a topological sort that groups nodes into parallelizable batches.
    """
    node_map = {node['id']: node for node in nodes}
    adjacency_list = collections.defaultdict(list)
    in_degree = {node_id: 0 for node_id in node_map}

    for edge in edges:
        source_id, target_id = edge['source'], edge['target']
        if source_id in node_map and target_id in node_map:
            adjacency_list[source_id].append(target_id)
            in_degree[target_id] += 1

    queue = collections.deque([node_id for node_id, degree in in_degree.items() if degree == 0])

    sorted_batches = []
    processed_node_count = 0
    while queue:
        current_batch_size = len(queue)
        current_batch = []
        for _ in range(current_batch_size):
            current_node_id = queue.popleft()
            current_batch.append(node_map[current_node_id])
            processed_node_count += 1
            for neighbor_id in adjacency_list[current_node_id]:
                in_degree[neighbor_id] -= 1
                if in_degree[neighbor_id] == 0:
                    queue.append(neighbor_id)
        sorted_batches.append(current_batch)

    if processed_node_count != len(nodes):
        unsorted_nodes = [node_id for node_id, degree in in_degree.items() if degree > 0]
        raise ValueError(f"Cycle detected in graph. Unprocessed nodes: {unsorted_nodes}")

    return sorted_batches


def auto_layout_nodes(nodes: List[Dict[str, Any]], edges: List[Dict[str, str]]) -> List[Dict[str, Any]]:
    """Automatically layout nodes using a simple hierarchical layout."""
    if not nodes:
        return nodes

    # Build adjacency lists
    incoming = {node['id']: [] for node in nodes}
    outgoing = {node['id']: [] for node in nodes}

    for edge in edges:
        source, target = edge['source'], edge['target']
        if source in outgoing and target in incoming:
            outgoing[source].append(target)
            incoming[target].append(source)

    # Find root nodes (no incoming edges)
    root_nodes = [node['id'] for node in nodes if not incoming[node['id']]]
    if not root_nodes:
        # If no roots (cycle), just pick the first node
        root_nodes = [nodes[0]['id']]

    # Perform level-order layout
    levels = []
    visited = set()
    queue = [(node_id, 0) for node_id in root_nodes]

    max_level = 0
    while queue:
        node_id, level = queue.pop(0)
        if node_id in visited:
            continue

        visited.add(node_id)

        # Ensure we have enough levels
        while len(levels) <= level:
            levels.append([])

        levels[level].append(node_id)
        max_level = max(max_level, level)

        # Add children to next level
        for child_id in outgoing[node_id]:
            if child_id not in visited:
                queue.append((child_id, level + 1))

    # Add any unvisited nodes to the end
    for node in nodes:
        if node['id'] not in visited:
            levels[-1].append(node['id'])

    # Calculate positions
    positioned_nodes = []
    node_map = {node['id']: node for node in nodes}

    level_height = 150
    node_width = 200

    for level_idx, level_nodes in enumerate(levels):
        y = level_idx * level_height
        level_width = len(level_nodes) * node_width
        start_x = -level_width / 2

        for node_idx, node_id in enumerate(level_nodes):
            x = start_x + (node_idx * node_width) + (node_width / 2)

            node = node_map[node_id].copy()
            node['position'] = {'x': x, 'y': y}
            positioned_nodes.append(node)

    return positioned_nodes


def convert_api_nodes_to_reactflow(nodes_data: List[Dict[str, Any]], edges_data: List[Dict[str, Any]]) -> tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Convert API node format to ReactFlow format with auto-layout."""
    import time

    # Convert nodes to ReactFlow format
    reactflow_nodes = []
    for i, node_data in enumerate(nodes_data):
        node_id = node_data.get("id", f"node-{int(time.time() * 1000)}-{i}")

        if node_data.get("type") == "content":
            # Content node
            node = {
                "id": node_id,
                "type": "contentNode",
                "data": {
                    "label": node_data.get("label", "Content Node"),
                    "contentGuid": node_data.get("contentGuid", ""),
                    "contentType": node_data.get("contentType", "unknown"),
                    "contentUrl": node_data.get("contentUrl", ""),
                    "author": node_data.get("author", "Unknown"),
                    "description": node_data.get("description", "")
                }
            }
        else:
            # Custom node
            node = {
                "id": node_id,
                "type": "customNode",
                "data": {
                    "label": node_data.get("label", "Custom Node"),
                    "nodeType": node_data.get("customType", "webhook"),
                    "customType": node_data.get("customType", "webhook"),
                    "description": node_data.get("description", ""),
                    "icon": node_data.get("icon", "⚙️"),
                    "config": node_data.get("config", {})
                }
            }

        reactflow_nodes.append(node)

    # Convert edges to ReactFlow format
    reactflow_edges = []
    for i, edge_data in enumerate(edges_data):
        edge = {
            "id": edge_data.get("id", f"edge-{i}"),
            "source": edge_data["source"],
            "target": edge_data["target"],
            "type": "deletable"
        }
        reactflow_edges.append(edge)

    # Auto-layout nodes
    positioned_nodes = auto_layout_nodes(reactflow_nodes, reactflow_edges)

    return positioned_nodes, reactflow_edges


def validate_api_dag_input(body: Dict[str, Any]) -> tuple[bool, List[str]]:
    """Validate API DAG input and return validation status and errors."""
    errors = []

    title = body.get("title", "")
    nodes_data = body.get("nodes", [])
    edges_data = body.get("edges", [])

    if not title.strip():
        errors.append("DAG title is required")

    if not nodes_data:
        errors.append("DAG must have at least one node")

    # Validate required node fields
    for i, node in enumerate(nodes_data):
        if not node.get("id"):
            errors.append(f"Node {i} missing required 'id' field")

        if node.get("type") == "content":
            if not node.get("contentGuid"):
                errors.append(f"Content node {i} missing required 'contentGuid' field")
        elif node.get("type") == "custom":
            if not node.get("customType"):
                errors.append(f"Custom node {i} missing required 'customType' field")

    # Validate edge references
    node_ids = {node.get("id") for node in nodes_data if node.get("id")}
    for i, edge in enumerate(edges_data):
        source = edge.get("source")
        target = edge.get("target")

        if not source:
            errors.append(f"Edge {i} missing required 'source' field")
        elif source not in node_ids:
            errors.append(f"Edge {i} references unknown source node: {source}")

        if not target:
            errors.append(f"Edge {i} missing required 'target' field")
        elif target not in node_ids:
            errors.append(f"Edge {i} references unknown target node: {target}")

    return len(errors) == 0, errors