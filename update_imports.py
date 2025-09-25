"""Script to update imports from focus_guard.platform to focus_guard.core.platform_utils."""

import os
import re

def update_file(file_path):
    """Update imports in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace import statements
        new_content = re.sub(
            r'from\s+focus_guard\.platform(\.|\s+import)',
            r'from focus_guard.core.platform_utils\1',
            content
        )
        
        # Only write if changes were made
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def main():
    """Main function to update imports in all Python files."""
    updated_files = 0
    
    # Walk through the project directory
    for root, _, files in os.walk('.'):
        # Skip virtual environment and other non-relevant directories
        if any(skip in root for skip in ['venv', '__pycache__', '.git', '.pytest_cache']):
            continue
            
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                if update_file(file_path):
                    print(f"Updated: {file_path}")
                    updated_files += 1
    
    print(f"\nUpdated {updated_files} files.")

if __name__ == "__main__":
    main()
