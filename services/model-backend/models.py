import os
import requests
import zipfile
import shutil
from flask_cors import CORS
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from ultralytics import YOLO
import threading
import mlflow
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
mlflow.set_experiment("/Shared/YOLOv8")

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
        
        # mlflow.log_param("testname",55)
        # # Start MLflow run

        mlflow.log_param('kkk', 0.001)
        #     mlflow.log_param("model_name", model_name)
        #     mlflow.log_param("model_architecture", model_architecture)
        #     mlflow.log_param("epochs", epochs)
        #     mlflow.log_param("seed", 42)
        #     mlflow.log_param("dataset", dataset)
        #     mlflow.log_param("train_split", train_split)
        #     mlflow.log_param("val_split", val_split)
        #     mlflow.log_param("test_split", test_split)
        #     mlflow.log_param("augmentation_recipe", augmentation_recipe)
        #     mlflow.log_param("num_augmentations", num_augmentations)

        # Load the model
        model = YOLO(model_architecture)

        # Train the model
        model.train(data=model_folder, epochs=epochs, imgsz=64, seed=42)
            # metrics = model.val()  # no arguments needed, dataset and settings remembered
            # metrics.top1  # top1 accuracy

            # # Log metrics (example: you may want to log other metrics relevant to your task)
            # mlflow.log_metric("val_accuracy_top1", metrics.top1)

            # training_status['progress'] = 'Training completed successfully.'
            # mlflow.log_metric("training_status", 1)
            
            # Log artifacts
            # mlflow.log_artifacts(os.path.join(tmp_folder, 'results'))

            # Log the model
            # mlflow.pytorch.log_model(model, "model")
    except Exception as e:
        print("Error during training:", str(e))
        training_status['progress'] = f'Error during training: {str(e)}'
        # mlflow.log_metric("training_status", 0)
        # mlflow.log_param("error_message", str(e))
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
    global mlflowrun_id

    # # Create MLflow experiment
    # experiment_id = create_mlflow_experiment(
    #     experiment_name="testing_mlflow1",
    #     tags={"env": "dev", "version": "1.0.0"},
    # )

    # mlflowrun_id = experiment_id

    # Start the Flask server
    app.run(port=8090, debug=True)
