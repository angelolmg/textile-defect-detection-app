from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os
import zipfile

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'datainfo.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)

class Dataset(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    dataset_name = db.Column(db.String(80), nullable=False)
    total_patches = db.Column(db.Integer, nullable=False)
    patch_size = db.Column(db.Integer, nullable=False)
    class_names = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Dataset {self.dataset_name}>'

with app.app_context():
    db.create_all()

@app.route('/upload_dataset', methods=['POST'])
def upload_dataset():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    dataset_name = request.form['dataset_name']
    total_patches = int(request.form['total_patches'])
    patch_size = int(request.form['patch_size'])
    class_names = request.form['class_names']

    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400

    # Save the file
    filepath = os.path.join('/tmp', file.filename)
    file.save(filepath)

    # Unzip the file to the datasets folder
    dataset_path = os.path.join('datasets', dataset_name)
    os.makedirs(dataset_path, exist_ok=True)
    with zipfile.ZipFile(filepath, 'r') as zip_ref:
        zip_ref.extractall(dataset_path)

    os.remove(filepath)

    # Save dataset info to the database
    dataset = Dataset(
        dataset_name=dataset_name,
        total_patches=total_patches,
        patch_size=patch_size,
        class_names=class_names
    )
    db.session.add(dataset)
    db.session.commit()

    return jsonify({'message': 'File uploaded and dataset information saved successfully'}), 200

if __name__ == '__main__':
    app.run(port=8080)
