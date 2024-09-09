#!/bin/bash

# Kill processes at specified ports
kill_ports=(4200 8070 8080 8090 5005)
for port in "${kill_ports[@]}"; do
    pid=$(lsof -ti tcp:"$port")
    if [ -n "$pid" ]; then
        kill -9 "$pid"
        echo "Killed process on port $port"
    else
        echo "No process found on port $port"
    fi
done

# Function to open a new gnome-terminal tab and run a command
open_tab() {
    gnome-terminal --tab -- bash -c "$1; exec bash"
}

# Navigate to angular-frontend and run ng serve
open_tab "cd angular-frontend && ng serve"

# Navigate to services/main-backend, activate virtual environment, and run server.py
open_tab "cd services/main-backend && python server.py"

# Navigate to services/data-backend, activate virtual environment, and run database.py
open_tab "cd services/data-backend && python database.py"

# Navigate to services/model-backend, activate virtual environment, and run models.py
open_tab "cd services/model-backend && python models.py"

# Run mlflow server on specified port
open_tab "cd services/model-backend && mlflow server --backend-store-uri runs/mlflow --port 5005"

echo "All tasks initiated in separate terminal tabs."
