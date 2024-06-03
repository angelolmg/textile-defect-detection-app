import os
from flask_cors import CORS
from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'models.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

# Define the ModelTemplate model
class ModelTemplate(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    model_name = db.Column(db.String(80), nullable=False)
    model_architecture = db.Column(db.String(80), nullable=False)
    epochs = db.Column(db.Integer, nullable=False)
    dataset = db.Column(db.String(80), nullable=False)
    train_split = db.Column(db.Float, nullable=False)
    val_split = db.Column(db.Float, nullable=False)
    test_split = db.Column(db.Float, nullable=False)
    augmentation_recipe = db.Column(db.String(80), nullable=False)

# Initialize the database
with app.app_context():
    db.create_all()

# Endpoint to receive and print the object
@app.route('/api/models', methods=['POST'])
def add_model():
    data = request.json
    new_model = ModelTemplate(
        model_name=data['modelName'],
        model_architecture=data['modelArchitecture'],
        epochs=data['epochs'],
        dataset=data['dataset'],
        train_split=data['trainSplit'],
        val_split=data['valSplit'],
        test_split=data['testSplit'],
        augmentation_recipe=data['augmentationRecipe']
    )
    db.session.add(new_model)
    db.session.commit()

    return jsonify({'id': new_model.id}), 201

# Endpoint to get all models
@app.route('/api/models', methods=['GET'])
def get_models():
    models = ModelTemplate.query.all()
    model_list = [{
        'id': model.id,
        'modelName': model.model_name,
        'modelArchitecture': model.model_architecture,
        'epochs': model.epochs,
        'dataset': model.dataset,
        'trainSplit': model.train_split,
        'valSplit': model.val_split,
        'testSplit': model.test_split,
        'augmentationRecipe': model.augmentation_recipe
    } for model in models]

    return jsonify(model_list), 200

if __name__ == '__main__':
    app.run(port=8090, debug=True)
