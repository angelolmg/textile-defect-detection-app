# TODO: Save dataset info to the database if theres already a metadata file

import os, shutil, json
import zipfile
import cv2
from PIL import Image
import albumentations as A
import numpy as np
import random
from flask_cors import CORS
from flask import Flask, request, jsonify, send_file, make_response
from flask_sqlalchemy import SQLAlchemy
import matplotlib
matplotlib.use('agg')
import matplotlib.pyplot as plt

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
    gauss_noise = db.Column(db.Float, default=0)
    unsharp_mask = db.Column(db.Float, default=0)

    def __repr__(self):
        return f'<AugmentationRecipe {self.recipe_name}>'


with app.app_context():
    db.create_all()
    if not AugmentationRecipe.query.first():
        sample_recipes = [
            AugmentationRecipe(
                recipe_name="Sample recipe 1",
                horizontal_flip=0.5,
                vertical_flip=0.5,
                random_rotate90=0.5,
                rotate=0.75,
                random_brightness_contrast=0.5,
                advanced_blur=0.33,
                gauss_noise=0.25,
                unsharp_mask=0.1
            )
        ]
        db.session.bulk_save_objects(sample_recipes)
        db.session.commit()

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

# Split and save images with augmentations
def split_and_save_images(class_input_folder, class_output_folder, selected_image_files, num_aug, augmentations):
    for filename in selected_image_files:
        image_path = os.path.join(class_input_folder, filename)
        image = Image.open(image_path)
        for i in range(num_aug):
            augmented_image = augmentations(image=np.array(image))['image']
            new_image_path = os.path.join(class_output_folder, f"{os.path.splitext(filename)[0]}_{i+1}.png")
            Image.fromarray(augmented_image).save(new_image_path)

# Create and split folders for train, val, test sets
def create_and_split_folders(input_folder, output_folder, splits, num_augmentations, augmentations):
    train_split, val_split, test_split = splits
    class_image_counts = {}
    
    for class_name, num_aug in num_augmentations.items():
        class_input_folder = os.path.join(input_folder, class_name)
        class_train_folder = os.path.join(output_folder, 'train', class_name)
        class_val_folder = os.path.join(output_folder, 'val', class_name)
        class_test_folder = os.path.join(output_folder, 'test', class_name)

        os.makedirs(class_train_folder, exist_ok=True)
        os.makedirs(class_val_folder, exist_ok=True)
        os.makedirs(class_test_folder, exist_ok=True)

        image_files = [filename for filename in os.listdir(class_input_folder) if filename.endswith('.png')]
        selected_image_files = random.sample(image_files, min(1000, len(image_files))) if len(image_files) > 1000 else image_files

        split_and_save_images(class_input_folder, class_train_folder, selected_image_files[:int(len(selected_image_files) * train_split)], num_aug, augmentations)
        split_and_save_images(class_input_folder, class_val_folder, selected_image_files[int(len(selected_image_files) * train_split):int(len(selected_image_files) * (train_split + val_split))], num_aug, augmentations)
        split_and_save_images(class_input_folder, class_test_folder, selected_image_files[int(len(selected_image_files) * (train_split + val_split)):], num_aug, augmentations)

        # Count images for each class
        train_count = len(os.listdir(class_train_folder))
        val_count = len(os.listdir(class_val_folder))
        test_count = len(os.listdir(class_test_folder))
        class_image_counts[class_name] = {'train': train_count, 'val': val_count, 'test': test_count}
    
    # Plot the distribution of images for each class
    plot_image_distribution(class_image_counts, output_folder)

# Plot the distribution of images for each class
def plot_image_distribution(class_image_counts, output_folder):
    classes = list(class_image_counts.keys())
    train_counts = [class_image_counts[cls]['train'] for cls in classes]
    val_counts = [class_image_counts[cls]['val'] for cls in classes]
    test_counts = [class_image_counts[cls]['test'] for cls in classes]
    
    x = range(len(classes))
    
    plt.figure(figsize=(10, 6))
    plt.bar(x, train_counts, width=0.2, label='Train', align='center')
    plt.bar(x, val_counts, width=0.2, label='Val', align='center')
    plt.bar(x, test_counts, width=0.2, label='Test', align='center', bottom=train_counts)
    
    plt.xlabel('Class')
    plt.ylabel('Number of Images')
    plt.title('Distribution of Images for Different Classes')
    plt.xticks(ticks=x, labels=classes, rotation=45)
    plt.legend()
    
    for i, (train_count, val_count, test_count) in enumerate(zip(train_counts, val_counts, test_counts)):
        plt.text(i, train_count / 2, str(train_count), ha='center', va='bottom', color='white')
        plt.text(i, train_count + val_count / 2, str(val_count), ha='center', va='bottom', color='white')
        plt.text(i, train_count + val_count + test_count / 2, str(test_count), ha='center', va='bottom', color='white')
    
    plt.tight_layout()
    
    # Save the histogram plot
    histogram_path = os.path.join(output_folder, 'class_distribution_histogram.png')
    plt.savefig(histogram_path)
    plt.close()
    
# Endpoint to augment and zip dataset
@app.route('/api/augment', methods=['POST'])
def augment_dataset():
    data = request.json
    dataset_name = data['dataset']
    train_split = data['trainSplit']
    val_split = data['valSplit']
    test_split = data['testSplit']
    augmentation_recipe_name = data['augmentationRecipe']
    num_augmentations = data['numAugmentations']
    augmentation_seed = data['augmentationSeed']

    random.seed(augmentation_seed)  # Set seed for augmentation reproducibility

    # Retrieve the dataset details from the database
    dataset = Dataset.query.filter_by(dataset_name=dataset_name).first()
    if not dataset:
        return jsonify({'error': 'Dataset not found'}), 404

    # Retrieve the augmentation recipe from the database
    augmentation_recipe = AugmentationRecipe.query.filter_by(recipe_name=augmentation_recipe_name).first()
    if not augmentation_recipe:
        return jsonify({'error': 'Augmentation recipe not found'}), 404

    input_folder = os.path.join('datasets', dataset_name)
    output_folder = os.path.join('datasets', f'{dataset_name}_augmented')
    if not os.path.exists(output_folder):
        os.makedirs(output_folder)

    # Define augmentations dynamically
    augmentations = A.Compose([
        A.HorizontalFlip(p=augmentation_recipe.horizontal_flip),
        A.VerticalFlip(p=augmentation_recipe.vertical_flip),
        A.RandomRotate90(p=augmentation_recipe.random_rotate90),
        A.Rotate(limit=180, interpolation=cv2.INTER_LANCZOS4, border_mode=cv2.BORDER_REFLECT, p=augmentation_recipe.rotate),
        A.RandomBrightnessContrast(p=augmentation_recipe.random_brightness_contrast),
        A.AdvancedBlur(p=augmentation_recipe.advanced_blur),
        A.GaussNoise(p=augmentation_recipe.gauss_noise),
        A.UnsharpMask(p=augmentation_recipe.unsharp_mask),
    ])

    # Augment images and split into train/val/test folders
    create_and_split_folders(input_folder, output_folder, (train_split, val_split, test_split), num_augmentations, augmentations)

    # Zip the augmented dataset
    zip_filename = f"{output_folder}.zip"
    with zipfile.ZipFile(zip_filename, 'w') as zipf:
        for root, _, files in os.walk(output_folder):
            for file in files:
                zipf.write(os.path.join(root, file), os.path.relpath(os.path.join(root, file), output_folder))

    # Clean up intermediate folders
    shutil.rmtree(output_folder)

    # Create a response with the zip file
    response = make_response(send_file(zip_filename, mimetype='application/zip'))
    
    # Set the Content-Disposition header to make the browser prompt the user to download the file with the specified name
    response.headers['Content-Disposition'] = f'attachment; filename={os.path.basename(zip_filename)}'

    # Include dataset information in the response
    dataset_info = {
        'dataset_name': dataset.dataset_name,
        'total_patches': dataset.total_patches,
        'patch_size': dataset.patch_size,
        'class_names': dataset.class_names
    }

    response.headers['X-Dataset-Info'] = json.dumps(dataset_info)

    return response

if __name__ == '__main__':
    app.run(port=8080, debug=True)
