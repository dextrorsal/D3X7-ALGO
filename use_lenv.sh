#!/bin/bash
# Deactivate any active environment first
if [[ "$VIRTUAL_ENV" != "" ]]; then
    deactivate
fi
# Activate lenv
source lenv/bin/activate
echo "Switched to lenv (Python 3.12)"
