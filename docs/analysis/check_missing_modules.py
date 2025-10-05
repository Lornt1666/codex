#!/usr/bin/env python3
"""
Check for missing Python modules required by RenderToRealityApp.

This script attempts to import each required module and reports which ones
are missing from the current Python environment.
"""

import sys
from typing import List, Tuple

def check_module(module_name: str, import_statement: str = None) -> Tuple[bool, str]:
    """
    Check if a module can be imported.
    
    Args:
        module_name: Display name of the module
        import_statement: The actual import statement to execute
        
    Returns:
        Tuple of (success: bool, message: str)
    """
    if import_statement is None:
        import_statement = f"import {module_name}"
    
    try:
        exec(import_statement)
        return True, f"✅ {module_name} - Available"
    except ImportError as e:
        return False, f"❌ {module_name} - MISSING ({e})"
    except Exception as e:
        return False, f"⚠️  {module_name} - Error: {e}"

def main():
    print("=" * 70)
    print("RenderToRealityApp - Missing Modules Check")
    print("=" * 70)
    print()
    
    # List of all modules used in the RenderToRealityApp project
    modules_to_check = [
        # Standard library modules (should always be available)
        ("os", "import os"),
        ("sys", "import sys"),
        ("json", "import json"),
        ("threading", "import threading"),
        ("subprocess", "import subprocess"),
        ("math", "import math"),
        ("pathlib.Path", "from pathlib import Path"),
        ("datetime.datetime", "from datetime import datetime"),
        
        # Third-party modules from requirements.txt
        ("PyQt6.QtWidgets", "from PyQt6 import QtWidgets"),
        ("PyQt6.QtGui", "from PyQt6 import QtGui"),
        ("PyQt6.QtCore", "from PyQt6 import QtCore"),
        ("cv2 (opencv-python)", "import cv2"),
        ("numpy", "import numpy as np"),
        ("PIL (Pillow)", "from PIL import Image"),
        ("trimesh", "import trimesh"),
        ("openai", "import openai"),
        
        # Optional modules
        ("torch (PyTorch)", "import torch"),
        
        # Blender-specific (only needed when running Blender scripts)
        # ("bpy (Blender Python API)", "import bpy"),
    ]
    
    results: List[Tuple[bool, str]] = []
    missing_modules: List[str] = []
    
    print("Checking standard library modules...")
    print("-" * 70)
    for i, (name, stmt) in enumerate(modules_to_check[:8]):
        success, message = check_module(name, stmt)
        results.append((success, message))
        print(message)
        if not success:
            missing_modules.append(name)
    
    print()
    print("Checking third-party modules (from requirements.txt)...")
    print("-" * 70)
    for name, stmt in modules_to_check[8:15]:
        success, message = check_module(name, stmt)
        results.append((success, message))
        print(message)
        if not success:
            missing_modules.append(name)
    
    print()
    print("Checking optional modules...")
    print("-" * 70)
    for name, stmt in modules_to_check[15:]:
        success, message = check_module(name, stmt)
        results.append((success, message))
        print(message)
        # Don't add optional modules to missing list
    
    print()
    print("=" * 70)
    print("SUMMARY")
    print("=" * 70)
    
    total = len(results)
    available = sum(1 for success, _ in results if success)
    missing = total - available
    
    print(f"Total modules checked: {total}")
    print(f"Available: {available}")
    print(f"Missing: {missing}")
    
    if missing_modules:
        print()
        print("❌ MISSING REQUIRED MODULES:")
        for module in missing_modules:
            print(f"   - {module}")
        print()
        print("To install missing modules, run:")
        print("   pip install -r requirements.txt")
        print()
        return 1
    else:
        print()
        print("✅ All required modules are available!")
        print()
        return 0

if __name__ == "__main__":
    sys.exit(main())
