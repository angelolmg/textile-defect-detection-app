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

# Navigate to angular-frontend and run ng serve
cd angular-frontend || { echo "Directory angular-frontend not found"; exit 1; }
ng serve &

# Navigate back and then to services/main-backend, activate virtual environment, and run server.py
cd - || exit
cd services/main-backend || { echo "Directory services/data-backend not found"; exit 1; }
source bin/activate
python server.py &

# Navigate back and then to services/data-backend, activate virtual environment, and run database.py
cd - || exit
cd services/data-backend || { echo "Directory services/data-backend not found"; exit 1; }
source bin/activate
python database.py &

# Navigate back and then to services/model-backend, activate virtual environment, and run models.py
cd - || exit
cd services/model-backend || { echo "Directory services/model-backend not found"; exit 1; }
source bin/activate
python models.py &

# Run mlflow server on specified port
mlflow server --backend-store-uri runs/mlflow --port 5005 &

echo "All tasks initiated."
