# Use a Python base image
FROM python:3.10

# Set the working directory
WORKDIR /app

# Copy the requirements file
COPY requirements.txt .

# Install the dependencies
RUN pip install -r requirements.txt

# Copy the rest of the application code
COPY . .

# Expose the port for the MLflow server and the models.py service
EXPOSE 8090 5005

# Start both the models.py script and the MLflow server
CMD ["sh", "-c", "python models.py & mlflow server --backend-store-uri runs/mlflow --host 0.0.0.0 --port 5005"]
