# TODO: Save dataset info to the database if theres already a metadata file

from flask import Flask, request, jsonify
from flask_sqlalchemy import SQLAlchemy
import os, json
import zipfile
from PIL import Image
from flask_cors import CORS

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)

CORS(app)

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

class AugmentationRecipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    recipe_name = db.Column(db.String(80), nullable=False)
    horizontal_flip = db.Column(db.Float, default=0)
    vertical_flip = db.Column(db.Float, default=0)
    random_rotate90 = db.Column(db.Float, default=0)
    rotate = db.Column(db.Float, default=0)
    random_brightness_contrast = db.Column(db.Float, default=0)
    advanced_blur = db.Column(db.Float, default=0)
    random_brightness = db.Column(db.Float, default=0)
    random_contrast = db.Column(db.Float, default=0)
    gauss_noise = db.Column(db.Float, default=0)
    unsharp_mask = db.Column(db.Float, default=0)

    def __repr__(self):
        return f'<AugmentationRecipe {self.recipe_name}>'


with app.app_context():
    db.create_all()

@app.route('/get_augmentations', methods=['GET'])
def get_augmentations():
    recipes = AugmentationRecipe.query.all()
    recipes_list = [{
        'id': recipe.id,
        'recipeName': recipe.recipe_name,
        'horizontalFlip': recipe.horizontal_flip,
        'verticalFlip': recipe.vertical_flip,
        'randomRotate90': recipe.random_rotate90,
        'rotate': recipe.rotate,
        'randomBrightnessContrast': recipe.random_brightness_contrast,
        'advancedBlur': recipe.advanced_blur,
        'randomBrightness': recipe.random_brightness,
        'randomContrast': recipe.random_contrast,
        'gaussNoise': recipe.gauss_noise,
        'unsharpMask': recipe.unsharp_mask
    } for recipe in recipes]

    return jsonify(recipes_list), 200

@app.route('/save_augmentation', methods=['POST'])
def save_augmentation():
    data = request.json
    recipe_name = data.get('recipeName')
    if not recipe_name:
        return jsonify({'error': 'Recipe name is required'}), 400

    augmentation_recipe = AugmentationRecipe(
        recipe_name=recipe_name,
        horizontal_flip=data.get('horizontalFlip', 0),
        vertical_flip=data.get('verticalFlip', 0),
        random_rotate90=data.get('randomRotate90', 0),
        rotate=data.get('rotate', 0),
        random_brightness_contrast=data.get('randomBrightnessContrast', 0),
        advanced_blur=data.get('advancedBlur', 0),
        random_brightness=data.get('randomBrightness', 0),
        random_contrast=data.get('randomContrast', 0),
        gauss_noise=data.get('gaussNoise', 0),
        unsharp_mask=data.get('unsharpMask', 0)
    )

    db.session.add(augmentation_recipe)
    db.session.commit()

    return jsonify({'message': 'Augmentation recipe saved successfully'}), 200

@app.route('/upload_zip_dataset', methods=['POST'])
def upload_zip_dataset():
    print("Uploading zip dataset")
    if 'file' not in request.files:
        print("No file part")
        return jsonify({'error': 'No file part'}), 400

    file = request.files['file']
    dataset_name = request.form['dataset_name']

    if file.filename == '':
        print("No selected file")
        return jsonify({'error': 'No selected file'}), 400

    # Save the file
    filepath = os.path.join('/tmp', file.filename)
    file.save(filepath)

    # Create a cover folder named after the zip file (excluding the .zip extension)
    cover_folder_name = os.path.splitext(file.filename)[0]
    cover_folder_path = os.path.join('datasets', cover_folder_name)
    os.makedirs(cover_folder_path, exist_ok=True)

    # Unzip the file to the cover folder
    with zipfile.ZipFile(filepath, 'r') as zip_ref:
        zip_ref.extractall(cover_folder_path)

    os.remove(filepath)

    # Check if metadata.json exists
    metadata_path = os.path.join(cover_folder_path, 'metadata.json')
    if not os.path.exists(metadata_path):
        print("Creating metadata.json")
        # Create metadata.json if it doesn't exist
        class_names = os.listdir(cover_folder_path)
        class_names = [d for d in class_names if os.path.isdir(os.path.join(cover_folder_path, d))]
        total_patches = 0
        patches_per_class = {}

        for class_name in class_names:
            class_path = os.path.join(cover_folder_path, class_name)
            image_files = [f for f in os.listdir(class_path) if os.path.isfile(os.path.join(class_path, f))]
            num_images = len(image_files)
            patches_per_class[class_name] = num_images
            total_patches += num_images

        sample_image_path = None
        for class_name in class_names:
            class_path = os.path.join(cover_folder_path, class_name)
            image_files = [f for f in os.listdir(class_path) if os.path.isfile(os.path.join(class_path, f))]
            if image_files:
                sample_image_path = os.path.join(class_path, image_files[0])
                break
        
        if sample_image_path:
            with Image.open(sample_image_path) as img:
                patch_size, _ = img.size
        else:
            patch_size, _ = 31, 31  # default values if no images found

        metadata = {
            "process": {
                "class_names": ','.join(class_names),
                "id": 1,
                "images_left": 0,
                "name": cover_folder_name,
                "patch_size": patch_size,  # Assuming patch size is the same as resize dimensions
                "resize_x": 320,
                "resize_y": 320,
                "total_images": 0
            },
            "patches_per_class": patches_per_class,
            "total_patches": total_patches
        }

        with open(metadata_path, 'w') as metadata_file:
            json.dump(metadata, metadata_file, indent=4)

        # Save dataset info to the database
        dataset = Dataset(
            dataset_name=cover_folder_name,
            total_patches=total_patches,
            patch_size=patch_size,
            class_names=','.join(class_names)
        )
        db.session.add(dataset)
        db.session.commit()

    print("Uploaded and dataset information saved successfully")
    return jsonify({'message': 'File uploaded and dataset information saved successfully'}), 200

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
        class_names="test"
    )
    db.session.add(dataset)
    db.session.commit()

    return jsonify({'message': 'File uploaded and dataset information saved successfully'}), 200

@app.route('/datasets', methods=['GET'])
def get_datasets():
    datasets = Dataset.query.all()
    datasets_list = [{
        'id': dataset.id,
        'dataset_name': dataset.dataset_name,
        'total_patches': dataset.total_patches,
        'patch_size': dataset.patch_size,
        'class_names': dataset.class_names
    } for dataset in datasets]

    return jsonify(datasets_list), 200

@app.route('/check_dataset/<string:dataset_name>', methods=['GET'])
def check_dataset(dataset_name):
    if not dataset_name:
        return jsonify({'error': 'Dataset name not provided'}), 400

    dataset = Dataset.query.filter_by(dataset_name=dataset_name).first()

    if dataset:
        return jsonify({'exists': True}), 200
    else:
        return jsonify({'exists': False}), 200


if __name__ == '__main__':
    app.run(port=8080, debug=True)
