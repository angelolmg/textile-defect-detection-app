from flask import Blueprint, request, jsonify
from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

class Process(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(80), nullable=False)
    total_images = db.Column(db.Integer, nullable=False)
    images_left = db.Column(db.Integer, nullable=False)

    def __repr__(self):
        return f'<Process {self.name}>'

process_bp = Blueprint('process', __name__)

@process_bp.before_app_request
def create_tables():
    db.create_all()

@process_bp.route('/add_process', methods=['POST'])
def add_process():
    data = request.get_json()
    new_process = Process(
        name=data['name'], 
        total_images=data['total_images'], 
        images_left=data['total_images']  # Initialize images_left with total_images
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
        'images_left': process.images_left
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
    db.session.commit()
    return jsonify({'message': 'Process updated successfully'}), 200
