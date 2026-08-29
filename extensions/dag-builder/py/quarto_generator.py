"""
Quarto Document Generation for DAG Builder

This module handles the generation of Quarto documents for DAG execution,
including Mermaid diagrams, custom node code generation, and deployment files.
"""

from typing import List, Dict, Any
from pathlib import Path
import json
from jinja2 import Environment, FileSystemLoader, select_autoescape


def generate_mermaid_diagram(nodes: List[Dict[str, Any]], edges: List[Dict[str, str]], dag_batches: List[List[Dict[str, Any]]]) -> str:
    """Generate Mermaid flowchart diagram from DAG data."""
    mermaid_lines = ["flowchart TD"]

    # Add nodes with styling based on type
    for node in nodes:
        node_id = node.get('id', 'unknown').replace('-', '_')
        node_data = node.get('data', {})
        label = node_data.get('label', 'Unknown')

        # Determine node type and styling
        if node_data.get('contentGuid'):
            # Content node (Posit Connect content)
            content_type = node_data.get('contentType', 'content')
            mermaid_lines.append(f'    {node_id}["{label}<br/><small>{content_type}</small>"]')
            mermaid_lines.append(f'    class {node_id} contentNode')
        elif node_data.get('customType'):
            # Custom action node
            custom_type = node_data.get('customType', 'custom')
            icon = node_data.get('icon', '⚙️')
            mermaid_lines.append(f'    {node_id}["{icon} {label}<br/><small>{custom_type}</small>"]')
            mermaid_lines.append(f'    class {node_id} customNode')
        else:
            # Unknown node type
            mermaid_lines.append(f'    {node_id}["{label}"]')
            mermaid_lines.append(f'    class {node_id} unknownNode')

    # Add edges
    for edge in edges:
        source_id = edge.get('source', '').replace('-', '_')
        target_id = edge.get('target', '').replace('-', '_')
        if source_id and target_id:
            mermaid_lines.append(f'    {source_id} --> {target_id}')

    # Add batch grouping (subgraphs)
    for i, batch in enumerate(dag_batches, 1):
        if len(batch) > 1:  # Only show subgraph if batch has multiple nodes
            batch_nodes = [node.get('id', '').replace('-', '_') for node in batch if node.get('id')]
            if batch_nodes:
                mermaid_lines.append(f'    subgraph batch{i} ["Batch {i} (Parallel)"]')
                for node_id in batch_nodes:
                    mermaid_lines.append(f'        {node_id}')
                mermaid_lines.append('    end')

    # Add styling classes
    mermaid_lines.extend([
        '',
        '    %% Styling',
        '    classDef contentNode fill:#e1f5fe,stroke:#0277bd,stroke-width:2px,color:#000',
        '    classDef customNode fill:#fce4ec,stroke:#c2185b,stroke-width:2px,color:#000',
        '    classDef unknownNode fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,color:#000'
    ])

    return '\n'.join(mermaid_lines)


def generate_custom_node_code(node: Dict[str, Any]) -> str:
    """Generate Python code for custom nodes based on their type and configuration."""
    node_data = node.get('data', {})
    custom_type = node_data.get('customType')
    config = node_data.get('config', {})
    node_id = node.get('id', 'unknown')

    if custom_type == 'webhook':
        url = config.get('url', '')
        method = config.get('method', 'GET').upper()
        headers = config.get('headers', '{}')
        body = config.get('body', '')

        # Use repr() to safely embed strings with quotes
        url_repr = repr(url)
        method_repr = repr(method)
        headers_repr = repr(headers)
        body_repr = repr(body)

        return f"""def execute_webhook_{node_id.replace('-', '_')}():
    import requests
    import json

    try:
        url = {url_repr}
        method = {method_repr}
        headers_str = {headers_repr}
        body_str = {body_repr}

        headers = json.loads(headers_str)

        print(f"🔗 WEBHOOK [{node_id}]: {{method}} {{url}}")

        if method in ['POST', 'PUT', 'PATCH'] and body_str.strip():
            body_data = json.loads(body_str)
            response = requests.request(method, url, headers=headers, json=body_data, timeout=30)
        else:
            response = requests.request(method, url, headers=headers, timeout=30)

        print(f"✅ WEBHOOK [{node_id}]: Status {{response.status_code}}")
        if response.status_code >= 400:
            print(f"⚠️  WEBHOOK [{node_id}]: Response: {{response.text[:200]}}")

        response.raise_for_status()
        return {{"status": "success", "status_code": response.status_code, "response": response.text[:500]}}

    except requests.exceptions.RequestException as e:
        error_msg = f"❌ WEBHOOK [{node_id}]: Request failed: {{str(e)}}"
        print(error_msg)
        return {{"status": "error", "error": error_msg}}
    except json.JSONDecodeError as e:
        error_msg = f"❌ WEBHOOK [{node_id}]: JSON parsing error: {{str(e)}}"
        print(error_msg)
        return {{"status": "error", "error": error_msg}}
    except Exception as e:
        error_msg = f"❌ WEBHOOK [{node_id}]: Unexpected error: {{str(e)}}"
        print(error_msg)
        return {{"status": "error", "error": error_msg}}

webhook_result_{node_id.replace('-', '_')} = execute_webhook_{node_id.replace('-', '_')}()"""

    elif custom_type == 'delay':
        duration = config.get('duration', 5)
        unit = config.get('unit', 'seconds')

        # Convert to seconds
        multiplier = {'seconds': 1, 'minutes': 60, 'hours': 3600}.get(unit, 1)
        total_seconds = duration * multiplier

        return f"""def execute_delay_{node_id.replace('-', '_')}():
    import time

    duration = {duration}
    unit = "{unit}"
    total_seconds = {total_seconds}

    print(f"⏱️  DELAY [{node_id}]: Waiting {{duration}} {{unit}}")
    time.sleep(total_seconds)
    print(f"✅ DELAY [{node_id}]: Wait completed")
    return {{"status": "success", "duration": total_seconds}}

delay_result_{node_id.replace('-', '_')} = execute_delay_{node_id.replace('-', '_')}()"""

    elif custom_type == 'condition':
        condition = config.get('condition', 'True')
        true_action = config.get('trueAction', 'continue')
        false_action = config.get('falseAction', 'skip_remaining')
        notification_message = config.get('notificationMessage', '')

        # Escape quotes in the condition for safe inclusion in the generated code
        safe_condition = (condition if condition.strip() else 'True').replace('"', '\\"')

        return f"""def execute_condition_{node_id.replace('-', '_')}(previous_nodes, runtime_context):
    try:
        # Available variables for condition evaluation
        # previous_nodes: dict of all previous node results
        # runtime_context: current time, environment, utilities

        print(f"🔀 CONDITION [{node_id}]: Evaluating condition")
        print(f"🔀 CONDITION [{node_id}]: Available previous nodes: {{list(previous_nodes.keys())}}")

        # Evaluate condition: {condition}
        condition_expression = "{safe_condition}"
        condition_result = bool(eval(condition_expression))

        print(f"🔀 CONDITION [{node_id}]: Expression: {{condition_expression}}")
        print(f"🔀 CONDITION [{node_id}]: Result: {{condition_result}}")

        if condition_result:
            action = "{true_action}"
            print(f"✅ CONDITION [{node_id}]: True - Action: {{action}}")
        else:
            action = "{false_action}"
            print(f"❌ CONDITION [{node_id}]: False - Action: {{action}}")

        # Handle notification actions
        if action == "notify":
            notification = "{notification_message}" or f"Condition {node_id} triggered"
            print(f"📢 NOTIFICATION [{node_id}]: {{notification}}")

        result = {{
            "status": "success",
            "condition_result": condition_result,
            "action": action,
            "condition_expression": condition_expression
        }}

        # Handle special actions that affect execution flow
        if action in ["stop", "skip_remaining"]:
            result["halt_execution"] = True
            result["halt_reason"] = action

        return result

    except NameError as e:
        error_msg = f"❌ CONDITION [{node_id}]: Variable not found: {{str(e)}}"
        print(error_msg)
        print(f"🔍 Available variables: previous_nodes={{list(previous_nodes.keys())}}, runtime_context={{list(runtime_context.keys())}}")
        return {{"status": "error", "error": error_msg}}
    except Exception as e:
        error_msg = f"❌ CONDITION [{node_id}]: Evaluation failed: {{str(e)}}"
        print(error_msg)
        return {{"status": "error", "error": error_msg}}

condition_result_{node_id.replace('-', '_')} = execute_condition_{node_id.replace('-', '_')}(previous_nodes, runtime_context)"""

    else:
        return f"""# Unknown custom node type: {custom_type} for node {node_id}
print(f"⚠️  UNKNOWN [{node_id}]: Custom node type '{custom_type}' not implemented")"""


def _get_jinja_env() -> Environment:
    """Get Jinja2 environment configured for templates."""
    template_dir = Path(__file__).parent / "templates"
    template_dir.mkdir(exist_ok=True)

    env = Environment(
        loader=FileSystemLoader(str(template_dir)),
        autoescape=select_autoescape(['html', 'xml']),
        trim_blocks=True,
        lstrip_blocks=True
    )
    return env


def _prepare_batch_data(batch: List[Dict[str, Any]], batch_num: int) -> Dict[str, Any]:
    """Prepare batch data for template rendering."""
    content_nodes = [node for node in batch if node.get('data', {}).get('contentGuid')]
    custom_nodes = [node for node in batch if node.get('data', {}).get('customType')]

    # Generate custom node code and metadata
    custom_nodes_data = []
    for node in custom_nodes:
        node_id = node.get('id', 'unknown')
        node_label = node.get('data', {}).get('label', 'Unknown')
        custom_type = node.get('data', {}).get('customType', 'unknown')

        custom_nodes_data.append({
            'id': node_id,
            'label': node_label,
            'type': custom_type,
            'code': generate_custom_node_code(node)
        })

    # Get GUIDs for content nodes
    content_guids = [node.get('data', {}).get('contentGuid', 'unknown') for node in content_nodes]

    return {
        'content_nodes': content_nodes,
        'custom_nodes': custom_nodes_data,
        'content_guids': content_guids
    }


def generate_quarto_document(nodes: List[Dict[str, Any]], edges: List[Dict[str, str]], dag_batches: List[List[Dict[str, Any]]]) -> str:
    """
    Generates a full Quarto document using Jinja2 templates.

    This is much cleaner and more maintainable than string concatenation.
    """
    # Get Jinja2 environment
    env = _get_jinja_env()

    # Generate Mermaid diagram
    mermaid_diagram = generate_mermaid_diagram(nodes, edges, dag_batches)

    # Count node types
    content_node_count = len([n for n in nodes if n.get('data', {}).get('contentGuid')])
    custom_node_count = len([n for n in nodes if n.get('data', {}).get('customType')])

    # Prepare batch data for template
    batches_data = []
    for i, batch in enumerate(dag_batches, 1):
        batch_data = _prepare_batch_data(batch, i)
        batches_data.append((i, batch_data))

    # Render template
    template = env.get_template('quarto_document.qmd.j2')
    return template.render(
        nodes=nodes,
        edges=edges,
        dag_batches=batches_data,
        mermaid_diagram=mermaid_diagram,
        content_node_count=content_node_count,
        custom_node_count=custom_node_count
    )


def create_deployment_files(quarto_content: str, temp_dir: str):
    """Create the necessary files for deployment."""
    # Create Quarto document
    quarto_path = Path(temp_dir) / "dag_execution.qmd"
    with open(quarto_path, "w") as f:
        f.write(quarto_content)

    # Create _quarto.yml project file
    quarto_yml_path = Path(temp_dir) / "_quarto.yml"
    quarto_yml_content = """project:
  type: website

format:
  html:
    theme: default
    toc: true
    code-fold: false

execute:
  enabled: true
"""
    with open(quarto_yml_path, "w") as f:
        f.write(quarto_yml_content)

    # Create requirements.txt
    requirements_path = Path(temp_dir) / "requirements.txt"
    with open(requirements_path, "w") as f:
        f.write("""posit-sdk
requests
""")

    return quarto_path, requirements_path, quarto_yml_path
