import os
import requests
import zipfile
import shutil
from flask_cors import CORS
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from ultralytics import YOLO
import threading

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'models.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Initialize the database
with app.app_context():
    db.create_all()

training_status = {
    'is_training': False,
    'progress': None
}

def train_yolo_model(data, zip_path):
    training_status['is_training'] = True
    training_status['progress'] = 'Starting training...'
    try:
        model_name = data['modelName']
        model_architecture = data['modelArchitecture']
        epochs = data['epochs']
        
        tmp_folder = os.path.join(BASE_DIR, 'tmp')
        model_folder = os.path.join(tmp_folder, model_name)

        # Unzip the augmented dataset
        with zipfile.ZipFile(zip_path, 'r') as zip_ref:
            zip_ref.extractall(model_folder)

        # Load the model
        model = YOLO(model_architecture)

        # Train the model
        model.train(data=model_folder, epochs=epochs, imgsz=64, seed=42)

        training_status['progress'] = 'Training completed successfully.'
    except Exception as e:
        training_status['progress'] = f'Error during training: {str(e)}'
    finally:
        training_status['is_training'] = False

        # Clean up extracted dataset folder after training
        if os.path.exists(tmp_folder):
            shutil.rmtree(tmp_folder)

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
    app.run(port=8090, debug=True)
