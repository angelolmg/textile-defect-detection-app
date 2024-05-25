from flask import Blueprint, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from PIL import Image
import os, base64, json, zipfile, shutil, requests

db = SQLAlchemy()

class Process(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    total_images = db.Column(db.Integer, nullable=False)
    images_left = db.Column(db.Integer, nullable=False)
    resize_x = db.Column(db.Integer, nullable=False)
    resize_y = db.Column(db.Integer, nullable=False)
    patch_size = db.Column(db.Integer, nullable=False)
    class_names = db.Column(db.String(255), nullable=False)

    def __repr__(self):
        return f'<Process {self.name}>'

process_bp = Blueprint('process', __name__)

@process_bp.before_app_request
def create_tables():
    db.create_all()

def add(name, total_images, resize_x, resize_y, patch_size, class_names):
    new_process = Process(
        name=name,
        total_images=total_images,
        images_left=total_images,  # Initialize images_left with total_images
        resize_x=resize_x,
        resize_y=resize_y,
        patch_size=patch_size,
        class_names=class_names
    )
    db.session.add(new_process)
    db.session.commit()
    return True

@process_bp.route('/process_dataset', methods=['POST'])
def process_dataset():
    data = request.json
    dataset_name = data.get('datasetName')
    coordinates_data = data.get('coordinatesData')
    
    if not dataset_name or not coordinates_data:
        return jsonify({'error': 'Invalid input data'}), 400
    
    process_response = get_process_by_name(dataset_name)
    
    if process_response.status_code != 200:
        return process_response

    process = process_response.get_json()
    resize_x = process['resize_x']
    resize_y = process['resize_y']
    patch_size = process['patch_size']
    class_names = process['class_names'].split(',')

    dataset_path = os.path.join('datasets', dataset_name)
    if not os.path.exists(dataset_path):
        return jsonify({'error': 'Dataset not found'}), 404

    class_paths = {}
    for class_name in class_names:
        class_path = os.path.join(dataset_path, class_name)
        os.makedirs(class_path, exist_ok=True)
        class_paths[class_name] = class_path

    total_patches = 0
    patches_per_class = {class_name: 0 for class_name in class_names}

    for image_name, classes in coordinates_data.items():
        image_path = os.path.join(dataset_path, image_name)
        image = Image.open(image_path)
        image = image.resize((resize_x, resize_y))
        width, height = image.size
        cols = width // patch_size
        rows = height // patch_size

        for row in range(rows):
            for col in range(cols):
                left = col * patch_size
                upper = row * patch_size
                right = left + patch_size
                lower = upper + patch_size
                patch = image.crop((left, upper, right, lower))
                patch_name = f'{image_name}_{row}_{col}.png'

                patch_class = class_names[0]
                for class_name, coords in classes.items():
                    if [col, row] in coords:
                        patch_class = class_name
                        break

                patch_path = os.path.join(class_paths[patch_class], patch_name)
                patch.save(patch_path)
                total_patches += 1
                patches_per_class[patch_class] += 1

    metadata = {
        'process': process,
        'patches_per_class': patches_per_class,
        'total_patches': total_patches
    }

    metadata_path = os.path.join(dataset_path, 'metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=4)

    # Zip the dataset folder
    zip_path = f'{dataset_path}.zip'
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(dataset_path):
            for file in files:
                file_path = os.path.join(root, file)
                arcname = os.path.relpath(file_path, os.path.join(dataset_path, '..'))
                zipf.write(file_path, arcname)
    
    # Send the zip file to the data server
    with open(zip_path, 'rb') as f:
        files = {'file': f}
        response = requests.post('http://localhost:8080/upload_dataset', files=files)
    
    if response.status_code != 200:
        return jsonify({'error': 'Failed to upload dataset to data server'}), 500

    # Remove the dataset folder and the zip file
    shutil.rmtree(dataset_path)
    os.remove(zip_path)

    # Delete the process after successful upload
    delete_process_by_name(dataset_name)

    return jsonify({'message': 'Dataset processed and uploaded successfully', 'metadata': metadata}), 201

@process_bp.route('/add_process', methods=['POST'])
def add_process():
    data = request.get_json()
    new_process = Process(
        name=data['name'],
        total_images=data['total_images'],
        images_left=data['total_images'],  # Initialize images_left with total_images
        resize_x=data['resize_x'],
        resize_y=data['resize_y'],
        patch_size=data['patch_size'],
        class_names=data['class_names']
    )
    db.session.add(new_process)
    db.session.commit()
    return jsonify({'message': 'Process added successfully'}), 201

@process_bp.route('/processes', methods=['GET'])
def get_processes():
    processes = Process.query.all()
    return jsonify([{
        'id': process.id,
        'name': process.name,
        'total_images': process.total_images,
        'images_left': process.images_left,
        'resize_x': process.resize_x,
        'resize_y': process.resize_y,
        'patch_size': process.patch_size,
        'class_names': process.class_names
    } for process in processes])

@process_bp.route('/process/<string:process_name>', methods=['GET'])
def get_process_by_name(process_name):
    process = Process.query.filter_by(name=process_name).first()
    if not process:
        return jsonify({'error': 'Process not found'}), 404
    
    return jsonify({
        'id': process.id,
        'name': process.name,
        'total_images': process.total_images,
        'images_left': process.images_left,
        'resize_x': process.resize_x,
        'resize_y': process.resize_y,
        'patch_size': process.patch_size,
        'class_names': process.class_names
    })

def delete_process_by_name(process_name):
    process = Process.query.filter_by(name=process_name).first()
    if not process:
        return jsonify({'error': 'Process not found'}), 404

    db.session.delete(process)
    db.session.commit()
    return jsonify({'message': 'Process deleted successfully'}), 200

@process_bp.route('/delete_process/<int:process_id>', methods=['DELETE'])
def delete_process(process_id):
    process = Process.query.get_or_404(process_id)
    db.session.delete(process)
    db.session.commit()
    return jsonify({'message': 'Process deleted successfully'}), 200

@process_bp.route('/edit_process/<int:process_id>', methods=['PUT'])
def edit_process(process_id):
    data = request.get_json()
    process = Process.query.get_or_404(process_id)
    process.name = data.get('name', process.name)
    process.total_images = data.get('total_images', process.total_images)
    process.images_left = data.get('images_left', process.images_left)
    process.resize_x = data.get('resize_x', process.resize_x)
    process.resize_y = data.get('resize_y', process.resize_y)
    process.patch_size = data.get('patch_size', process.patch_size)
    process.class_names = data.get('class_names', process.class_names)
    db.session.commit()
    return jsonify({'message': 'Process updated successfully'}), 200

@process_bp.route('/get_images/<dataset_name>', methods=['GET'])
def get_images(dataset_name):
    folder_path = os.path.join('datasets', dataset_name)
    
    if not os.path.exists(folder_path):
        return jsonify({'error': 'Dataset not found'}), 404

    if not os.path.isdir(folder_path):
        return jsonify({'error': 'Invalid dataset folder'}), 400

    image_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.bmp')
    images = []
    for filename in os.listdir(folder_path):
        if filename.lower().endswith(image_extensions):
            with open(os.path.join(folder_path, filename), "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
                images.append({'filename': filename, 'data': encoded_string})
    
    return jsonify({'images': images, 'dataset_name': dataset_name})
