import os, uuid, json
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

def set_seed(seed):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(seed)

def generate_random_seed():
    return random.randint(0, 2**32 - 1)

def train_yolo_model(data, zip_path, dataset_info):
    training_status['is_training'] = True
    training_status['progress'] = 'Starting training...'
    client = MlflowClient()
    
    try:
        training_seed = data['trainingSeed']
        if training_seed == None:
            training_seed = generate_random_seed()

        set_seed(training_seed)  # Set the seed for reproducibility

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
        
        # Log run params
        mlflow.log_param("model_name", model_name)
        mlflow.log_param("model_architecture", model_architecture)
        mlflow.log_param("epochs", epochs)
        mlflow.log_param("training_seed", training_seed)
        mlflow.log_param("dataset", dataset)
        mlflow.log_param("train_split", train_split)
        mlflow.log_param("val_split", val_split)
        mlflow.log_param("test_split", test_split)
        mlflow.log_param("augmentation_recipe", augmentation_recipe)
        mlflow.log_param("num_augmentations", num_augmentations)
        
        # Log dataset information
        mlflow.log_param("total_patches", dataset_info['total_patches'])
        mlflow.log_param("patch_size", dataset_info['patch_size'])
        mlflow.log_param("class_names", dataset_info['class_names'])

        # Log model tags
        mlflow.set_tag('model.type', 'yolov8')
        mlflow.set_tag('model.size', 'small')
        mlflow.set_tag('patch.size', dataset_info['patch_size'])

        # Load the model
        model = YOLO(model_architecture)

        # Train the model
        experiment_name = "YOLOv8 Experiments"
        run_name = str(uuid.uuid4())
        model.train(data=model_folder, epochs=epochs, imgsz=64, seed=training_seed, name=run_name, project=experiment_name)
        metrics = model.val()

        experiment = client.get_experiment_by_name(experiment_name)
        myrun = client.search_runs(experiment.experiment_id, filter_string=f"params.name = '{run_name}'", max_results=1)[0]
        with mlflow.start_run(run_id=myrun.info.run_id):
            mlflow.log_metric("training_status", 1)
            mlflow.log_metric("speed.preprocess-ms", metrics.speed['preprocess'])
            mlflow.log_metric("speed.inference-ms", metrics.speed['inference'])

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

    # Generate a random seed for augmentation if not provided
    augmentation_seed = data['augmentationSeed']
    if augmentation_seed == None:
        augmentation_seed = generate_random_seed()

    mlflow.log_param("augmentation_seed", augmentation_seed)

    # Create object for dataset and augmentation details
    augmentation_data = {
        'dataset': data['dataset'],
        'trainSplit': data['trainSplit'],
        'valSplit': data['valSplit'],
        'testSplit': data['testSplit'],
        'augmentationRecipe': data['augmentationRecipe'],
        'numAugmentations': data['numAugmentations'],
        'augmentationSeed': augmentation_seed
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

        # Extract dataset information from response headers
        dataset_info = json.loads(response.headers['X-Dataset-Info'])
        
        # Start training in a new thread
        threading.Thread(target=train_yolo_model, args=(data, zip_path, dataset_info)).start()

        return jsonify({'message': 'Training started and augmented dataset saved.'}), 200
    else:
        return jsonify({'error': 'Training failed or dataset augmentation unsuccessful.'}), 500

@app.route('/api/models/train/status', methods=['GET'])
def get_training_status():
    return jsonify(training_status), 200

if __name__ == '__main__':

    # Start the Flask server
    app.run(port=8090, debug=True)
