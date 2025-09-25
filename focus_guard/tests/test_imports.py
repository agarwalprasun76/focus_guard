"""Test script to diagnose import issues."""

import sys
import os

# Add the project root to the Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("Python Path:")
for p in sys.path:
    print(f"  {p}")

print("\nCurrent working directory:", os.getcwd())
print("Project root:", project_root)

# Test importing the main module
print("\nTrying to import focus_guard...")
try:
    import focus_guard
    print("Successfully imported focus_guard")
    print("focus_guard.__file__:", getattr(focus_guard, "__file__", "Not found"))
    print("focus_guard.__path__:", getattr(focus_guard, "__path__", "Not found"))
    
    # Test importing a submodule
    print("\nTrying to import focus_guard.core...")
    try:
        from focus_guard import core
        print("Successfully imported focus_guard.core")
        print("core.__file__:", getattr(core, "__file__", "Not found"))
        print("core.__path__:", getattr(core, "__path__", "Not found"))
        
        # Test importing a deeper module
        print("\nTrying to import focus_guard.core.coordinator...")
        try:
            from focus_guard.core import coordinator
            print("Successfully imported focus_guard.core.coordinator")
            print("coordinator.__file__:", getattr(coordinator, "__file__", "Not found"))
            print("coordinator.__path__:", getattr(coordinator, "__path__", "Not found"))
            
            # Test importing the test module
            print("\nTrying to import test_coordinator_integration_pytest...")
            try:
                from focus_guard.tests.core.coordinator import test_coordinator_integration_pytest
                print("Successfully imported test_coordinator_integration_pytest")
                print("test_coordinator_integration_pytest.__file__:", 
                      getattr(test_coordinator_integration_pytest, "__file__", "Not found"))
            except ImportError as e:
                print(f"Failed to import test_coordinator_integration_pytest: {e}")
                print("Trying to import directly from file path...")
                try:
                    import importlib.util
                    test_path = os.path.join(project_root, 'focus_guard', 'tests', 'core', 'coordinator', 'test_coordinator_integration_pytest.py')
                    spec = importlib.util.spec_from_file_location("test_module", test_path)
                    test_module = importlib.util.module_from_spec(spec)
                    spec.loader.exec_module(test_module)
                    print(f"Successfully imported test module from {test_path}")
                except Exception as e2:
                    print(f"Failed to import test module from file path: {e2}")
        except ImportError as e:
            print(f"Failed to import focus_guard.core.coordinator: {e}")
    except ImportError as e:
        print(f"Failed to import focus_guard.core: {e}")
except ImportError as e:
    print(f"Failed to import focus_guard: {e}")
