import os, uuid, json
import onnx
import requests
import zipfile
import shutil
from flask_cors import CORS
from flask import Flask, request, jsonify, send_file
from flask_sqlalchemy import SQLAlchemy
from ultralytics import YOLO
import threading
import mlflow
from mlflow import MlflowClient
import random
import numpy as np
import torch
from mlflow.entities.model_registry import ModelVersion

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
        with mlflow.start_run(run_id=myrun.info.run_id) as run:
            mlflow.log_metric("training_status", 1)
            mlflow.log_metric("speed.preprocess-ms", metrics.speed['preprocess'])
            mlflow.log_metric("speed.inference-ms", metrics.speed['inference'])

            # Export to ONNX format and log the model
            # Batch specifies export model batch inference size or the max number of images the exported model will process concurrently in predict mode.
            model.export(format="onnx", batch=999)
            model_onnx_path = BASE_DIR + "/" + experiment_name + "/" + str(run_name) + "/weights/best.onnx"
            onnx_model = onnx.load_model(model_onnx_path)
            model_info = mlflow.onnx.log_model(onnx_model, "model", registered_model_name="test01")
            client.set_registered_model_alias("test01", model_name, model_info.registered_model_version)

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

@app.route('/api/mlflow/models', methods=['GET'])
def list_registered_models():
    client = MlflowClient()
    model_name = request.args.get('modelName')

    if model_name:
        # Fetch specific model versions
        model_versions = []
        for mv in client.search_model_versions(f"name='{model_name}'"):
            mv_dict = dict(mv)
            
            # Fetch the corresponding run
            run_id = mv.run_id
            run_info = client.get_run(run_id).info
            run_data = client.get_run(run_id).data

            # Extract additional info
            mv_dict['model_name'] = run_data.params.get('model_name', 'N/A')
            mv_dict['dataset'] = run_data.params.get('dataset', 'N/A')
            mv_dict['accuracy_top1'] = run_data.metrics.get('metrics/accuracy_top1', 'N/A')
            mv_dict['description'] = mv.description if mv.description else 'No description available'
            mv_dict['model_architecture'] = run_data.params.get('model_architecture', 'N/A')
            mv_dict['augmentation_recipe'] = run_data.params.get('augmentation_recipe', 'N/A')
            
            model_versions.append(mv_dict)
        return jsonify(model_versions), 200
    else:
        # Fetch all registered models
        registered_models = []
        for rm in client.search_registered_models():
            latest_versions = rm.latest_versions
            rm.latest_versions = [dict(mv) for mv in latest_versions]
            registered_models.append(dict(rm))
        return jsonify(registered_models), 200

@app.route('/fetch_model', methods=['GET'])
def fetch_model():
    """
    Fetch the registered model from the MLflow registry using the alias provided as a query parameter
    and return the model weights file.
    """
    model_name = request.args.get('model')
    if not model_name:
        return jsonify({'error': 'Model name not provided'}), 400

    try:
        client = mlflow.tracking.MlflowClient()
        model_version = client.get_model_version_by_alias("test01", model_name)
        run_id = model_version.run_id
        artifacts_uri = client.get_run(run_id).info.artifact_uri
        model_file_path = os.path.join(artifacts_uri, "weights", "best.pt")
        
        if os.path.exists(model_file_path):
            return send_file(model_file_path, as_attachment=True)
        else:
            return jsonify({'error': 'Model file not found'}), 404
    except Exception as e:
        return jsonify({'error': f'Failed to fetch model: {str(e)}'}), 500

def get_model_version_by_alias(name: str, alias: str) -> ModelVersion:
    # This function should use mlflow to get the model version by alias
    client = mlflow.tracking.MlflowClient()
    model_version = client.get_model_version_by_alias(name, alias)
    return model_version

def delete_model_version(name: str, version: str) -> None:
    # This function should use mlflow to delete the model version
    client = mlflow.tracking.MlflowClient()
    client.delete_model_version(name, version)

@app.route('/api/mlflow/models', methods=['DELETE'])
def delete_model():
    model_alias = request.args.get('modelName')
    model_name = "test01"

    if not model_alias:
        return jsonify({"error": "Model alias is required"}), 400

    try:
        # Step 1: Get the model version by alias
        model_version = get_model_version_by_alias(model_name, model_alias)
        version_number = model_version.version

        # Step 2: Delete the model using the model name and version number
        delete_model_version(model_name, version_number)

        return jsonify({"message": f"Model {model_name} version {version_number} deleted successfully"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':

    # Start the Flask server
    app.run(port=8090, debug=True)
