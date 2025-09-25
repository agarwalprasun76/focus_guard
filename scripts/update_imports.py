"""
Script to update import paths from core_v2 to focus_guard.core in the browser extension code.
"""

import os
import re
import sys
from pathlib import Path
from typing import List, Tuple

# Set console output encoding to UTF-8
if sys.platform == 'win32':
    import io
    import sys
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Define checkmark symbol that works across platforms
CHECKMARK = '✓'  # Will be replaced with [OK] on Windows if needed

# Directory containing the browser extension code
BROWSER_EXTENSION_DIR = Path("focus_guard/core/browser")

# Files to update
FILES_TO_UPDATE = [
    "extension/installer.py",
    "extension/manager.py",
    "extension/tab_server.py",
    "extension/native_host.py",
    "integration/browser_integration.py"
]

def update_imports(file_path: Path) -> Tuple[bool, int]:
    """Update import paths in a file.
    
    Args:
        file_path: Path to the file to update
        
    Returns:
        Tuple of (file_modified, num_changes)
    """
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            
        # Track if we made any changes
        modified = False
        changes = 0
        
        # Pattern to match from core_v2.module import ...
        pattern1 = re.compile(r'from\s+core_v2\.(\w+(?:\.\w+)*)\s+import')
        
        # Pattern to match import core_v2.module
        pattern2 = re.compile(r'import\s+core_v2\.(\w+(?:\.\w+)*)(?:\s+as\s+\w+)?(?:[\s,;]|$)')
        
        # Replace patterns
        def replace_pattern1(match):
            nonlocal modified, changes
            modified = True
            changes += 1
            return f'from focus_guard.core.{match.group(1)} import'
            
        def replace_pattern2(match):
            nonlocal modified, changes
            modified = True
            changes += 1
            return f'import focus_guard.core.{match.group(1)}'
        
        # Apply replacements
        new_content = pattern1.sub(replace_pattern1, content)
        new_content = pattern2.sub(replace_pattern2, new_content)
        
        # If changes were made, write the file back
        if modified:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
                
        return modified, changes
        
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False, 0

def main():
    """Main function to update imports in all specified files."""
    total_changes = 0
    total_files_updated = 0
    
    for rel_path in FILES_TO_UPDATE:
        file_path = BROWSER_EXTENSION_DIR / rel_path
        if not file_path.exists():
            print(f"Warning: File not found: {file_path}")
            continue
            
        print(f"Updating imports in {file_path}...")
        modified, changes = update_imports(file_path)
        
        if modified:
            print(f"  {CHECKMARK} Updated {changes} import(s)")
            total_changes += changes
            total_files_updated += 1
        else:
            print(f"  {CHECKMARK} No changes needed")
    
    print(f"\nUpdate complete!")
    print(f"- Files updated: {total_files_updated}")
    print(f"- Total import statements updated: {total_changes}")

if __name__ == "__main__":
    main()
