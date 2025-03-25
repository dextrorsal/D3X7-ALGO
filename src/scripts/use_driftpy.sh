#!/bin/bash
# Deactivate any active environment first
if [[ "$VIRTUAL_ENV" != "" ]]; then
    deactivate
fi
# Activate driftpy_env
source driftpy_env/bin/activate
echo "Switched to driftpy_env (Python 3.10)"
