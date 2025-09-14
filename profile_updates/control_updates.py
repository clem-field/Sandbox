import os
import re
from pathlib import Path

def rename_and_update_controls(profile_path, old_prefix='V-', new_prefix='FR-'):
    """
    Renames InSpec control files from old_prefix to new_prefix and updates their content.
    
    Args:
        profile_path (str): Path to the InSpec profile directory (e.g., './my_profile').
        old_prefix (str): Prefix to replace (e.g., 'V-').
        new_prefix (str): New prefix to use (e.g., 'FR-').
    """
    # Resolve the controls directory
    controls_dir = Path(profile_path) / 'controls'
    if not controls_dir.exists():
        print(f"Error: Controls directory {controls_dir} does not exist.")
        return

    # Iterate over all .rb files in controls/
    for file_path in controls_dir.glob('*.rb'):
        # Check if file matches the old prefix
        if file_path.name.startswith(old_prefix):
            # Generate new filename
            new_filename = new_prefix + file_path.name[len(old_prefix):]
            new_file_path = controls_dir / new_filename

            print(f"Renaming {file_path.name} to {new_filename}")

            # Read the file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()

            # Update control ID (e.g., control 'V-12345' to control 'FR-12345')
            updated_content = re.sub(
                rf"control\s+['\"]{old_prefix}(\d+)['\"]",
                rf"control '{new_prefix}\1'",
                content
            )

            # Update tags (e.g., tag 'V-12345' to tag 'FR-12345')
            updated_content = re.sub(
                rf"tag\s+['\"]{old_prefix}(\d+)['\"]",
                rf"tag '{new_prefix}\1'",
                updated_content
            )

            # Write updated content to the original file temporarily
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(updated_content)

            # Rename the file
            file_path.rename(new_file_path)
            print(f"Updated and renamed {file_path.name} to {new_filename}")

def main():
    # Specify the path to your InSpec profile
    profile_path = './path/to/your/inspec/profile'  # Update this path
    rename_and_update_controls(profile_path)

if __name__ == '__main__':
    main()