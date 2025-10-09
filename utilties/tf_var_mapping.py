import os
import json
import csv
import argparse
import hcl2
from pathlib import Path
from typing import Dict, List, Any
import logging
from openpyxl import Workbook

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_terraform_file(file_path: str) -> Dict:
    """Parse a Terraform (.tf or .tfvars) file and return its contents."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            return hcl2.load(f)
    except Exception as e:
        logging.error(f"Error parsing file {file_path}: {str(e)}")
        return {}

def extract_variables_from_tf(file_path: str) -> List[Dict[str, Any]]:
    """Extract variable definitions from a .tf file."""
    variables = []
    data = parse_terraform_file(file_path)
    
    if 'variable' in data:
        for var_block in data['variable']:
            for var_name, var_details in var_block.items():
                variable_info = {
                    'name': var_name,
                    'file': file_path,
                    'type': var_details.get('type', 'unspecified'),
                    'default': var_details.get('default', None),
                    'description': var_details.get('description', None)
                }
                variables.append(variable_info)
    return variables

def extract_values_from_tfvars(file_path: str) -> Dict[str, Any]:
    """Extract variable values from a .tfvars file."""
    values = {}
    data = parse_terraform_file(file_path)
    
    for key, value in data.items():
        values[key] = value
    return values

def collect_terraform_variables(root_dir: str) -> Dict[str, Any]:
    """Recursively collect variables and their values from Terraform directories."""
    inventory = {
        'variables': [],
        'values': {}
    }
    
    # Walk through the directory
    for root, _, files in os.walk(root_dir):
        for file in files:
            file_path = os.path.join(root, file)
            
            # Process .tf files for variable definitions
            if file.endswith('.tf'):
                logging.info(f"Processing Terraform file: {file_path}")
                variables = extract_variables_from_tf(file_path)
                inventory['variables'].extend(variables)
            
            # Process .tfvars files for variable values
            if file.endswith('.tfvars'):
                logging.info(f"Processing tfvars file: {file_path}")
                values = extract_values_from_tfvars(file_path)
                inventory['values'].update(values)
    
    return inventory

def merge_variable_info(inventory: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Merge variable definitions with their values for documentation."""
    documented_vars = []
    
    for var in inventory['variables']:
        var_name = var['name']
        documented_var = var.copy()
        
        # Add assigned value from .tfvars if available
        assigned_value = inventory['values'].get(var_name, None)
        documented_var['assigned_value'] = assigned_value
        
        # Determine effective value (assigned value takes precedence over default)
        documented_var['effective_value'] = assigned_value if assigned_value is not None else var['default']
        
        documented_vars.append(documented_var)
    
    return documented_vars

def save_inventory_to_json(documented_vars: List[Dict[str, Any]], output_file: str):
    """Save the inventory to a JSON file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(documented_vars, f, indent=2, sort_keys=True)
        logging.info(f"Inventory saved to {output_file}")
    except Exception as e:
        logging.error(f"Error saving inventory to {output_file}: {str(e)}")

def save_inventory_to_csv(documented_vars: List[Dict[str, Any]], output_file: str):
    """Save the inventory to a CSV file."""
    try:
        headers = ['name', 'type', 'default', 'assigned_value', 'effective_value', 'description', 'file']
        with open(output_file, 'w', encoding='utf-8', newline='') as f:
            writer = csv.DictWriter(f, fieldnames=headers)
            writer.writeheader()
            for var in documented_vars:
                writer.writerow({
                    'name': var['name'],
                    'type': var['type'],
                    'default': json.dumps(var['default']),  # Handle complex types
                    'assigned_value': json.dumps(var['assigned_value']),
                    'effective_value': json.dumps(var['effective_value']),
                    'description': var['description'],
                    'file': var['file']
                })
        logging.info(f"Inventory saved to {output_file}")
    except Exception as e:
        logging.error(f"Error saving inventory to {output_file}: {str(e)}")

def save_inventory_to_xlsx(documented_vars: List[Dict[str, Any]], output_file: str):
    """Save the inventory to an XLSX file."""
    try:
        wb = Workbook()
        ws = wb.active
        ws.title = "Terraform Inventory"
        
        # Write headers
        headers = ['Name', 'Type', 'Default', 'Assigned Value', 'Effective Value', 'Description', 'File']
        ws.append(headers)
        
        # Write data
        for var in documented_vars:
            ws.append([
                var['name'],
                var['type'],
                json.dumps(var['default']),
                json.dumps(var['assigned_value']),
                json.dumps(var['effective_value']),
                var['description'],
                var['file']
            ])
        
        wb.save(output_file)
        logging.info(f"Inventory saved to {output_file}")
    except Exception as e:
        logging.error(f"Error saving inventory to {output_file}: {str(e)}")

def save_inventory_to_markdown(documented_vars: List[Dict[str, Any]], output_file: str):
    """Save the inventory to a Markdown file with a table."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            # Write table header
            f.write("| Name | Type | Default | Assigned Value | Effective Value | Description | File |\n")
            f.write("|------|------|---------|----------------|-----------------|-------------|------|\n")
            
            # Write table rows
            for var in documented_vars:
                f.write(
                    f"| {var['name']} | {var['type']} | {json.dumps(var['default'])} | "
                    f"{json.dumps(var['assigned_value'])} | {json.dumps(var['effective_value'])} | "
                    f"{var['description'] or ''} | {var['file']} |\n"
                )
        logging.info(f"Inventory saved to {output_file}")
    except Exception as e:
        logging.error(f"Error saving inventory to {output_file}: {str(e)}")

def save_inventory(documented_vars: List[Dict[str, Any]], output_file: str, output_format: str):
    """Save the inventory in the specified format."""
    output_format = output_format.lower()
    if output_format == 'json':
        save_inventory_to_json(documented_vars, output_file)
    elif output_format == 'csv':
        save_inventory_to_csv(documented_vars, output_file)
    elif output_format == 'xlsx':
        save_inventory_to_xlsx(documented_vars, output_file)
    elif output_format == 'markdown':
        save_inventory_to_markdown(documented_vars, output_file)
    else:
        logging.error(f"Unsupported output format: {output_format}")

def main():
    """Main function to process Terraform directories and generate inventory."""
    parser = argparse.ArgumentParser(description="Generate Terraform variable inventory.")
    parser.add_argument(
        '--input-dir',
        type=str,
        required=True,
        help="Root directory containing Terraform files to process"
    )
    parser.add_argument(
        '--output-file',
        type=str,
        default='terraform_inventory',
        help="Output file name (without extension)"
    )
    parser.add_argument(
        '--output-format',
        type=str,
        choices=['json', 'csv', 'xlsx', 'markdown'],
        default='json',
        help="Output format: json, csv, xlsx, or markdown"
    )
    
    args = parser.parse_args()
    
    # Validate input directory
    if not os.path.isdir(args.input_dir):
        logging.error(f"Directory {args.input_dir} does not exist.")
        return
    
    # Append appropriate file extension based on output format
    output_extensions = {
        'json': '.json',
        'csv': '.csv',
        'xlsx': '.xlsx',
        'markdown': '.md'
    }
    output_file = f"{args.output_file}{output_extensions[args.output_format]}"
    
    # Collect variables and values
    inventory = collect_terraform_variables(args.input_dir)
    
    # Merge variable definitions with values
    documented_vars = merge_variable_info(inventory)
    
    # Save to output file
    save_inventory(documented_vars, output_file, args.output_format)
    
    # Print summary
    logging.info(f"Found {len(documented_vars)} variables in {args.input_dir}")
    for var in documented_vars:
        logging.info(
            f"Variable: {var['name']}, Type: {var['type']}, "
            f"Default: {var['default']}, Assigned: {var['assigned_value']}, "
            f"Effective: {var['effective_value']}, File: {var['file']}"
        )

if __name__ == "__main__":
    main()