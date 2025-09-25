#!/usr/bin/env python3
"""
Focus Guard Extension Testing - Unified Entry Point

Usage:
    python test.py --help
    python test.py all
    python test.py robust
    python test.py admin
    python test.py edge
    python test.py functionality
"""

import sys
import argparse
import subprocess
from pathlib import Path

def run_test(test_path):
    """Run a test script."""
    try:
        cmd = [sys.executable, test_path]
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"PASSED: {test_path.name}")
        print(result.stdout)
        return True
    except subprocess.CalledProcessError as e:
        print(f"FAILED: {test_path.name}")
        if e.stdout:
            print(f"Output: {e.stdout}")
        if e.stderr:
            print(f"Error: {e.stderr}")
        return False

def main():
    parser = argparse.ArgumentParser(description="Focus Guard Extension Testing")
    subparsers = parser.add_subparsers(dest='command', help='Test commands')
    
    # Run all tests
    all_parser = subparsers.add_parser('all', help='Run all tests')
    
    # Individual test categories
    robust_parser = subparsers.add_parser('robust', help='Run robust installation tests')
    admin_parser = subparsers.add_parser('admin', help='Run admin functionality tests')
    edge_parser = subparsers.add_parser('edge', help='Run Edge-specific tests')
    func_parser = subparsers.add_parser('functionality', help='Run functionality tests')
    real_parser = subparsers.add_parser('real', help='Run real installation tests')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    testing_dir = Path(__file__).parent / "testing"
    
    test_files = {
        'robust': testing_dir / "test_robust_extension_installation.py",
        'admin': testing_dir / "test_admin_functionality.py", 
        'edge': testing_dir / "test_edge_installation.py",
        'functionality': testing_dir / "test_actual_functionality.py",
        'real': testing_dir / "test_real_installation.py"
    }
    
    if args.command == 'all':
        print("Running All Focus Guard Extension Tests...")
        results = []
        for test_name, test_file in test_files.items():
            print(f"\n--- Running {test_name} tests ---")
            success = run_test(test_file)
            results.append((test_name, success))
        
        print("\n" + "="*50)
        print("TEST SUMMARY")
        print("="*50)
        passed = 0
        for test_name, success in results:
            status = "PASSED" if success else "FAILED"
            print(f"{test_name:15} {status}")
            if success:
                passed += 1
        
        print(f"\nResults: {passed}/{len(results)} tests passed")
        
    else:
        if args.command in test_files:
            print(f"Running {args.command} tests...")
            success = run_test(test_files[args.command])
            if not success:
                sys.exit(1)

if __name__ == "__main__":
    main()
