import os
import requests
from flask_cors import CORS
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'models.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define the TrainingTemplate model
class TrainingTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(80), nullable=False)
    model_architecture = db.Column(db.String(80), nullable=False)
    epochs = db.Column(db.Integer, nullable=False)
    dataset = db.Column(db.String(80), nullable=False)
    train_split = db.Column(db.Float, nullable=False)
    val_split = db.Column(db.Float, nullable=False)
    test_split = db.Column(db.Float, nullable=False)
    augmentation_recipe = db.Column(db.String(80), nullable=False)
    num_augmentations = db.Column(db.JSON, nullable=False)

    def __repr__(self):
        return f'<TrainingTemplate {self.model_name}>'

# Initialize the database
with app.app_context():
    db.create_all()

# Method to train model and augment dataset
@app.route('/api/models/train', methods=['POST'])
def train_model():
    data = request.json
    model_name = data['modelName']
    model_architecture = data['modelArchitecture']
    epochs = data['epochs']
    dataset_name = data['dataset']
    train_split = data['trainSplit']
    val_split = data['valSplit']
    test_split = data['testSplit']
    augmentation_recipe_name = data['augmentationRecipe']
    num_augmentations = data['numAugmentations']

    # Create object for dataset and augmentation details
    training_data = {
        'dataset': dataset_name,
        'trainSplit': train_split,
        'valSplit': val_split,
        'testSplit': test_split,
        'augmentationRecipe': augmentation_recipe_name,
        'numAugmentations': num_augmentations
    }

    # Make request to endpoint for dataset augmentation and zipping
    response = requests.post('http://localhost:8080/api/augment', json=training_data)
    tmp_folder = os.path.join(BASE_DIR, 'tmp')
    if not os.path.exists(tmp_folder):
        os.makedirs(tmp_folder)

    # Check if request was successful
    if response.status_code == 200:
        # Save the received zip file
        with open(os.path.join('tmp', 'augmented_dataset.zip'), 'wb') as f:
            f.write(response.content)
        return jsonify({'message': 'Training successful and augmented dataset saved.'}), 200
    else:
        return jsonify({'error': 'Training failed or dataset augmentation unsuccessful.'}), 500
    

if __name__ == '__main__':
    app.run(port=8090, debug=True)