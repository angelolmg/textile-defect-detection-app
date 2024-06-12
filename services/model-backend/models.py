import os, uuid
import requests
import zipfile
import shutil
from flask_cors import CORS
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from ultralytics import YOLO
import threading
import mlflow
from mlflow import MlflowClient
import random
import numpy as np
import torch
from mlflow_utils import create_mlflow_experiment, get_mlflow_experiment

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'models.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Set MLflow tracking URI and token
mlflow.set_tracking_uri("runs/mlflow")
mlflow.set_experiment("YOLOv8 Experiments")

# Initialize the database
with app.app_context():
    db.create_all()

training_status = {
    'is_training': False,
    'progress': None
}

def set_seed(seed=42):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def train_yolo_model(data, zip_path):
    training_status['is_training'] = True
    training_status['progress'] = 'Starting training...'
    client = MlflowClient()
    
    try:
        set_seed(42)  # Set the seed for reproducibility

        model_name = data['modelName']
        model_architecture = data['modelArchitecture']
        epochs = data['epochs']
        dataset = data['dataset']
        train_split = data['trainSplit']
        val_split = data['valSplit']
        test_split = data['testSplit']
        augmentation_recipe = data['augmentationRecipe']
        num_augmentations = data['numAugmentations']
        
        tmp_folder = os.path.join(BASE_DIR, 'tmp')
        model_folder = os.path.join(tmp_folder, model_name)

        # Unzip the augmented dataset
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(model_folder)
        
        # Start MLflow run
        mlflow.log_param("model_name", model_name)
        mlflow.log_param("model_architecture", model_architecture)
        mlflow.log_param("epochs", epochs)
        mlflow.log_param("seed", 42)
        mlflow.log_param("dataset", dataset)
        mlflow.log_param("train_split", train_split)
        mlflow.log_param("val_split", val_split)
        mlflow.log_param("test_split", test_split)
        mlflow.log_param("augmentation_recipe", augmentation_recipe)
        mlflow.log_param("num_augmentations", num_augmentations)

        # Load the model
        model = YOLO(model_architecture)

        # Train the model
        experiment_name = "YOLOv8 Experiments"
        run_name = str(uuid.uuid4())
        model.train(data=model_folder, epochs=epochs, imgsz=64, seed=42, name=run_name, project=experiment_name)

        experiment = client.get_experiment_by_name(experiment_name)
        myrun = client.search_runs(experiment.experiment_id, filter_string=f"params.name = '{run_name}'", max_results=1)[0]
        with mlflow.start_run(run_id=myrun.info.run_id):
            mlflow.log_metric("training_status", 1)

        training_status['progress'] = 'Training completed successfully.'

    except Exception as e:
        print("Error during training:", str(e))
        training_status['progress'] = f'Error during training: {str(e)}'

        experiment = client.get_experiment_by_name(experiment_name)
        myrun = client.search_runs(experiment.experiment_id, filter_string=f"params.name = '{run_name}'", max_results=1)[0]
        with mlflow.start_run(run_id=myrun.info.run_id):
            mlflow.log_metric("training_status", 0)
            mlflow.log_param("error_message", str(e))
    finally:
        print("Finishing training...")
        training_status['is_training'] = False

        # Clean up extracted dataset folder after training
        if os.path.exists(tmp_folder):
            shutil.rmtree(tmp_folder)

        # Delete the zip file after training
        if os.path.exists(zip_path):
            os.remove(zip_path)

@app.route('/api/models/train', methods=['POST'])
def train_model():
    data = request.json

    # Create object for dataset and augmentation details
    augmentation_data = {
        'dataset': data['dataset'],
        'trainSplit': data['trainSplit'],
        'valSplit': data['valSplit'],
        'testSplit': data['testSplit'],
        'augmentationRecipe': data['augmentationRecipe'],
        'numAugmentations': data['numAugmentations']
    }

    # Make request to endpoint for dataset augmentation and zipping
    response = requests.post('http://localhost:8080/api/augment', json=augmentation_data)
    tmp_folder = os.path.join(BASE_DIR, 'tmp')
    if not os.path.exists(tmp_folder):
        os.makedirs(tmp_folder)

    # Check if request was successful
    if response.status_code == 200:
        zip_path = os.path.join(tmp_folder, 'augmented_dataset.zip')
        # Save the received zip file
        with open(zip_path, 'wb') as f:
            f.write(response.content)
        
        # Start training in a new thread
        threading.Thread(target=train_yolo_model, args=(data, zip_path)).start()

        return jsonify({'message': 'Training started and augmented dataset saved.'}), 200
    else:
        return jsonify({'error': 'Training failed or dataset augmentation unsuccessful.'}), 500

@app.route('/api/models/train/status', methods=['GET'])
def get_training_status():
    return jsonify(training_status), 200

if __name__ == '__main__':

    # Start the Flask server
    app.run(port=8090, debug=True)
