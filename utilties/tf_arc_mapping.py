import hcl2
import os
import json
import argparse

def parse_terraform_files(root_dir):
    """Parse .tf files in the given directory and subdirectories."""
    resources = []
    dependencies = []
    
    for root, _, files in os.walk(root_dir):
        for file in files:
            if file.endswith('.tf'):
                with open(os.path.join(root, file), 'r') as f:
                    try:
                        config = hcl2.load(f)
                        for resource in config.get('resource', []):
                            for res_type, res_blocks in resource.items():
                                for res_name, attrs in res_blocks.items():
                                    resources.append({
                                        'type': res_type,
                                        'name': res_name,
                                        'attrs': attrs
                                    })
                                    for attr_key, attr_val in attrs.items():
                                        if isinstance(attr_val, str) and '${' in attr_val:
                                            dep_parts = attr_val.split('.')
                                            if len(dep_parts) > 1:
                                                dep_res = '.'.join(dep_parts[:2]).replace('${', '').strip()
                                                dependencies.append((f"{res_type}.{res_name}", dep_res))
                    except Exception as e:
                        print(f"Error parsing {file}: {e}")
    
    return resources, dependencies

def parse_terraform_json(json_file):
    """Parse Terraform plan or state JSON file."""
    resources = []
    dependencies = []
    
    try:
        with open(json_file, 'r') as f:
            data = json.load(f)
        
        # Handle Terraform plan JSON
        plan_resources = data.get('planned_values', {}).get('root_module', {}).get('resources', [])
        # Handle Terraform state JSON
        state_resources = data.get('resources', [])
        target_resources = plan_resources or state_resources
        
        for res in target_resources:
            res_type = res.get('type')
            res_name = res.get('name')
            resources.append({
                'type': res_type,
                'name': res_name,
                'attrs': res.get('values', {})
            })
            
            # Extract dependencies from expressions or depends_on
            depends_on = res.get('depends_on', [])
            for dep in depends_on:
                dependencies.append((f"{res_type}.{res_name}", dep))
            
            # Parse attribute references (simplified)
            for attr_val in res.get('values', {}).values():
                if isinstance(attr_val, str) and '.' in attr_val:
                    dep_parts = attr_val.split('.')
                    if len(dep_parts) > 1:
                        dep_res = '.'.join(dep_parts[:2])
                        dependencies.append((f"{res_type}.{res_name}", dep_res))
        
        # Handle child modules recursively
        child_modules = data.get('planned_values', {}).get('root_module', {}).get('child_modules', [])
        for module in child_modules:
            for res in module.get('resources', []):
                res_type = res.get('type')
                res_name = res.get('name')
                resources.append({
                    'type': res_type,
                    'name': res_name,
                    'attrs': res.get('values', {})
                })
                depends_on = res.get('depends_on', [])
                for dep in depends_on:
                    dependencies.append((f"{res_type}.{res_name}", dep))
    
    except Exception as e:
        print(f"Error parsing JSON file {json_file}: {e}")
    
    return resources, dependencies

def generate_mermaid_diagram(resources, dependencies):
    """Generate Mermaid diagram syntax."""
    mermaid_lines = ["graph TD;"]
    for res in resources:
        node_id = f"{res['type']}.{res['name']}"
        label = f"{res['type']}\\n{res['name']}"
        mermaid_lines.append(f'    {node_id}["{label}"];')
    for src, dst in dependencies:
        mermaid_lines.append(f"    {src} --> {dst};")
    return "\n".join(mermaid_lines)

def generate_graphviz_diagram(resources, dependencies):
    """Generate Graphviz DOT syntax."""
    dot_lines = ["digraph G {"]
    for res in resources:
        node_id = f"{res['type']}.{res['name']}"
        label = f"{res['type']}\\n{res['name']}"
        dot_lines.append(f'    "{node_id}" [label="{label}"];')
    for src, dst in dependencies:
        dot_lines.append(f'    "{src}" -> "{dst}";')
    dot_lines.append("}")
    return "\n".join(dot_lines)

def wrap_in_markdown(diagram, format_type):
    """Wrap the diagram syntax in a Markdown code block."""
    code_fence = f"```{format_type}\n"
    markdown_content = [
        "# Terraform Architecture Diagram",
        "",
        f"This diagram represents the Terraform infrastructure parsed from {'code' if args.source == 'code' else args.source}.",
        "",
        code_fence,
        diagram,
        "```"
    ]
    return "\n".join(markdown_content)

def main():
    parser = argparse.ArgumentParser(description="Generate architectural diagram in Markdown from Terraform code, plan, or state.")
    parser.add_argument("-i", "input", type=str, help="Terraform parent directory or JSON file (plan/state).")
    parser.add_argument("-o", "--output", type=str, default="architecture.md", help="Output Markdown file path (default: architecture.md).")
    parser.add_argument("-f", "--format", choices=['mermaid', 'graphviz'], default='mermaid', help="Diagram format: mermaid or graphviz (default: mermaid).")
    parser.add_argument("-s", "--source", choices=['code', 'plan', 'state'], default='code', help="Source type: code (directory), plan (JSON), or state (JSON, default: code).")
    
    global args  # Store args globally for use in wrap_in_markdown
    args = parser.parse_args()
    
    # Ensure output has .md extension
    if not args.output.endswith('.md'):
        args.output += '.md'
    
    # Parse based on source type
    if args.source == 'code':
        if not os.path.isdir(args.input):
            print(f"Error: {args.input} is not a directory.")
            return
        resources, dependencies = parse_terraform_files(args.input)
    else:
        if not os.path.isfile(args.input):
            print(f"Error: {args.input} is not a valid file.")
            return
        resources, dependencies = parse_terraform_json(args.input)
    
    # Generate diagram based on format
    if args.format == 'mermaid':
        diagram = generate_mermaid_diagram(resources, dependencies)
        markdown = wrap_in_markdown(diagram, 'mermaid')
    else:  # graphviz
        diagram = generate_graphviz_diagram(resources, dependencies)
        markdown = wrap_in_markdown(diagram, 'dot')
    
    # Write output
    try:
        with open(args.output, "w") as f:
            f.write(markdown)
        print(f"Markdown file with {args.format} diagram generated and saved to {args.output}")
    except Exception as e:
        print(f"Error writing to {args.output}: {e}")

if __name__ == "__main__":
    main()