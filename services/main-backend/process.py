from flask import Blueprint, request, jsonify
from flask_sqlalchemy import SQLAlchemy

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
