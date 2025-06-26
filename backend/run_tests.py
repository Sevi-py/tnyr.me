#!/usr/bin/env python3
"""
Test runner script for the URL shortener backend
"""

import sys
import subprocess
import os

def run_tests():
    """Run the test suite with different options"""
    
    print("🧪 Running URL Shortener Backend Tests\n")
    
    # Basic test commands
    commands = {
        "all": ["pytest"],
        "crypto": ["pytest", "-m", "crypto", "tests/test_crypto.py"],
        "api": ["pytest", "-m", "api", "tests/test_api.py"],  
        "database": ["pytest", "-m", "database", "tests/test_database.py"],
        "utils": ["pytest", "tests/test_utils.py"],
        "coverage": ["pytest", "--cov=main", "--cov-report=html", "--cov-report=term"],
        "fast": ["pytest", "-x", "--tb=line"],  # Stop on first failure, short traceback
        "verbose": ["pytest", "-v", "-s"],
    }
    
    # Check if specific test type was requested
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        if test_type in commands:
            cmd = commands[test_type]
            print(f"Running {test_type} tests...")
            result = subprocess.run(cmd)
            return result.returncode
        elif test_type == "help":
            print("Available test options:")
            for key, cmd in commands.items():
                print(f"  {key}: {' '.join(cmd)}")
            return 0
        else:
            print(f"Unknown test type: {test_type}")
            print("Use 'help' to see available options")
            return 1
    
    # Run all tests by default
    print("Running all tests...")
    result = subprocess.run(commands["all"])
    return result.returncode

if __name__ == "__main__":
    exit_code = run_tests()
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")
    
    sys.exit(exit_code) 