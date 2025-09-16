#!/bin/bash

# Script to launch MCP servers
# Usage: ./start-mcp-server.sh [all | compute | db | network | security | observability | cost]

set -e

# Change to project root
SCRIPT_DIR=$(dirname "$0")
PARENT1=$(dirname "$SCRIPT_DIR")
PARENT2=$(dirname "$PARENT1")
PARENT3=$(dirname "$PARENT2")
cd "$PARENT3"
# Ensure src/ is on PYTHONPATH so servers can import src/mcp_oci_common
export PYTHONPATH="$(pwd)/src:$(pwd):${PYTHONPATH}"

# Function to launch a single server
launch_server() {
    local server=$1
    echo "Launching $server server..."
    poetry run python "mcp_servers/$server/server.py" &
    echo "$server server launched with PID $!"
}

# List of all servers
SERVERS=("compute" "db" "network" "security" "observability" "cost")

if [ "$1" = "all" ]; then
    for server in "${SERVERS[@]}"; do
        launch_server "$server"
    done
    echo "All MCP servers launched. Use 'pkill -f server.py' to stop them if needed."
elif [ -n "$1" ] && [[ " ${SERVERS[*]} " =~ " $1 " ]]; then
    launch_server "$1"
else
    echo "Usage: $0 [all | ${SERVERS[*]}]"
    exit 1
fi

# Wait for all background processes
wait
