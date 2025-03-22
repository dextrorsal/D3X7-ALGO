#!/bin/bash

# Set the database path
DB_PATH="/home/dex/mcp_servers/sqlite/test.db"

# Create empty database file if it doesn't exist
touch "$DB_PATH"

# Log file
LOG_FILE="/home/dex/mcp_servers/sqlite/sqlite_conda.log"
echo "=== Starting SQLite MCP server with Conda Python at $(date) ===" > $LOG_FILE

# Ensure we're using the correct Python from the ML-bot environment
export PATH="/home/dex/anaconda3/envs/ML-bot/bin:$PATH"

# Run the server
/home/dex/anaconda3/envs/ML-bot/bin/python -m mcp_server_sqlite --db-path "$DB_PATH" 2>&1 | tee -a $LOG_FILE
