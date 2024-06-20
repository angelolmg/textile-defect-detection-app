#!/bin/bash

# Array of ports to check and kill processes
ports=(4200 8080 8090 5005)

# Function to kill process running on specified port
kill_process_on_port() {
    pids=$(lsof -ti tcp:"$1")
    if [ -n "$pids" ]; then
        for pid in $pids; do
            kill -9 "$pid"
            echo "Killed process on port $1 (PID: $pid)"
        done
    else
        echo "No process found on port $1"
    fi
}

# Kill processes running on specified ports
for port in "${ports[@]}"; do
    kill_process_on_port "$port"
done

echo "All specified services have been stopped."
