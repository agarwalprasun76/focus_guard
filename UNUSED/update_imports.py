import os
import re
from pathlib import Path

def update_file_imports(file_path):
    """Update import paths in a single file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Handle 'from core_v2.module.submodule import name'
        new_content = re.sub(
            r'from\s+core_v2\.(\w+(?:\.\w+)*)\s+import',
            r'from focus_guard.core.\1 import',
            content
        )
        
        # Handle 'import core_v2.module.submodule as alias'
        new_content = re.sub(
            r'import\s+core_v2\.(\w+(?:\.\w+)*)(\s+as\s+\w+)?([\s,;]|$)',
            r'from focus_guard.core import \1\2\3',
            new_content
        )
        
        # Handle 'import core_v2'
        new_content = re.sub(
            r'import\s+core_v2(\s|$|,|;)',
            r'import focus_guard.core as core_v2\1',
            new_content
        )
        
        # Handle relative imports that might reference core_v2
        new_content = re.sub(
            r'from\s+\.+\.*core_v2\.(\w+(?:\.\w+)*)\s+import',
            r'from ...core.\1 import',
            new_content
        )
        
        # Update any remaining references to core_v2 in the code
        # This handles cases like function calls, class references, etc.
        new_content = re.sub(
            r'(?<!\.)core_v2\.(?!__version__\b)(\w+)',
            r'core.\1',
            new_content
        )
        
        # Update any remaining direct references to core_v2 (e.g., in docstrings, comments)
        new_content = new_content.replace('core_v2', 'core')
        
        if new_content != content:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            return True
        return False
    except Exception as e:
        print(f"Error processing {file_path}: {e}")
        return False

def process_directory(directory: Path):
    """Process all Python files in the given directory."""
    updated_files = 0
    total_processed = 0
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = Path(root) / file
                print(f"Processing {file_path}...")
                if update_file_imports(file_path):
                    updated_files += 1
                    print(f"  -> Updated imports in {file_path}")
                total_processed += 1
    
    return updated_files, total_processed

def main():
    base_dir = Path(__file__).parent
    core_dir = base_dir / 'focus_guard' / 'core'
    tests_dir = base_dir / 'focus_guard' / 'tests' / 'core'
    
    if not core_dir.exists():
        print("Error: Could not find focus_guard/core directory")
        return
    
    total_updated = 0
    total_processed = 0
    
    # Process core directory
    print("\n=== Processing core directory ===")
    updated, processed = process_directory(core_dir)
    total_updated += updated
    total_processed += processed
    
    # Process tests directory if it exists
    if tests_dir.exists():
        print("\n=== Processing tests directory ===")
        updated, processed = process_directory(tests_dir)
        total_updated += updated
        total_processed += processed
    
    print(f"\nProcessing complete!")
    print(f"Updated {total_updated} out of {total_processed} Python files.")

if __name__ == '__main__':
    main()
