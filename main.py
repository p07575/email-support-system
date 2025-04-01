#!/usr/bin/env python3
"""
Entry point for Email Support System - redirects to the new modular structure
"""
import sys
import os

# Add current directory to path so we can import from src
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
sys.dont_write_bytecode = True

# Import and run the new modular application
if __name__ == "__main__":
    from src.main import main
    main()