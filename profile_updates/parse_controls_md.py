import json
from collections import defaultdict

# Load the JSON data from a file
with open('hdf_schema.json', 'r') as file:
    data = json.load(file)

# Prepare markdown content
markdown_content = "# Failed Controls Report\n\n"

# Group failed controls by severity
failed_controls = defaultdict(list)

# Iterate through profiles
for profile in data.get('profiles', []):
    # Iterate through controls in each profile
    for control in profile.get('controls', []):
        # Check if any result has status 'failed'
        failed = any(result.get('status') == 'failed' for result in control.get('results', []))
        if failed:
            severity = control.get('tags', {}).get('severity', 'unknown').lower()
            control_id = control.get('id', 'Unknown')
            # Extract 'check' from descriptions, clean up newlines and extra whitespace
            check = next((desc.get('data') for desc in control.get('descriptions', []) if desc.get('label') == 'check'), 'Not found')
            check = ' '.join(check.strip().split())  # Remove newlines and extra spaces
            # Extract 'fix' from descriptions, clean up newlines and extra whitespace
            fix = next((desc.get('data') for desc in control.get('descriptions', []) if desc.get('label') == 'fix'), 'Not found')
            fix = ' '.join(fix.strip().split())  # Remove newlines and extra spaces
            
            # Append to group
            failed_controls[severity].append((control_id, check, fix))

# Define order for severities
severity_order = ['high', 'medium', 'low']

# Add sections in order
for sev in severity_order:
    if sev in failed_controls:
        markdown_content += f"### {sev.capitalize()}\n\n"
        for cid, ch, fx in failed_controls[sev]:
            markdown_content += f"- {cid}\n"
            markdown_content += f"  - Check: {ch}\n"
            markdown_content += f"  - Fix: {fx}\n"
        markdown_content += "\n"

# Handle unknown or other severities
other_sevs = [s for s in failed_controls if s not in severity_order]
if other_sevs:
    for sev in sorted(other_sevs):
        markdown_content += f"### {sev.capitalize()}\n\n"
        for cid, ch, fx in failed_controls[sev]:
            markdown_content += f"- {cid}\n"
            markdown_content += f"  - Check: {ch}\n"
            markdown_content += f"  - Fix: {fx}\n"
        markdown_content += "\n"

# Write to markdown file
with open('failed_controls.md', 'w') as md_file:
    md_file.write(markdown_content)