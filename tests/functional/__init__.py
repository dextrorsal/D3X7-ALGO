"""
Test initialization file to prevent test modules from being imported and executed automatically.
This file is used to mark the directory as a Python package, but we want to ensure that
test modules are not imported and executed when importing other parts of the codebase.
"""

import sys
import os

# Check if we're being imported outside of pytest
if not any('pytest' in arg for arg in sys.argv) and 'PYTEST_CURRENT_TEST' not in os.environ:
    # Block imports of test modules when not running pytest
    __all__ = []
    
    class BlockImports:
        def __init__(self, *args, **kwargs):
            pass
        
        def __getattr__(self, name):
            raise ImportError(f"Test module {name} is not available for import outside pytest.")
    
    # Create a custom module object that blocks imports
    sys.modules[__name__] = BlockImports()
