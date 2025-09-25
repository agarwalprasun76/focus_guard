"""
Check what's actually in the Edge extensions directory.
"""

import os
import json

def check_edge_extensions():
    """Check Edge extensions directory contents."""
    user_profile = os.path.expanduser("~")
    edge_extensions_dir = os.path.join(
        user_profile, "AppData", "Local", "Microsoft", "Edge", 
        "User Data", "Default", "Extensions"
    )
    
    print(f"Edge extensions directory: {edge_extensions_dir}")
    print(f"Directory exists: {os.path.exists(edge_extensions_dir)}")
    
    if not os.path.exists(edge_extensions_dir):
        return
    
    print("\nContents:")
    try:
        items = os.listdir(edge_extensions_dir)
        print(f"Total items: {len(items)}")
        
        for item in items:
            item_path = os.path.join(edge_extensions_dir, item)
            print(f"\n📁 {item}")
            
            if os.path.isdir(item_path):
                # Check for manifest.json
                manifest_path = os.path.join(item_path, "manifest.json")
                if os.path.exists(manifest_path):
                    try:
                        with open(manifest_path, 'r', encoding='utf-8') as f:
                            manifest = json.load(f)
                            name = manifest.get('name', 'Unknown')
                            version = manifest.get('version', 'Unknown')
                            print(f"   📄 manifest.json - Name: {name}, Version: {version}")
                            
                            if "focus" in name.lower() or "guard" in name.lower():
                                print(f"   ✅ This is Focus Guard!")
                    except Exception as e:
                        print(f"   ❌ Error reading manifest: {e}")
                else:
                    print(f"   📂 Directory (no manifest.json)")
                    
                # List subdirectories
                try:
                    subitems = os.listdir(item_path)
                    if subitems:
                        print(f"   Contains: {', '.join(subitems[:5])}")
                        if len(subitems) > 5:
                            print(f"   ... and {len(subitems) - 5} more items")
                except:
                    pass
            else:
                print(f"   📄 File")
                
    except Exception as e:
        print(f"Error reading directory: {e}")

if __name__ == "__main__":
    check_edge_extensions()
