import os
import json
import threading
import cv2
import shutil
from ultralytics import YOLO
import base64
import matplotlib.pyplot as plt
import pandas as pd
import json
import time
import requests
from flask import Flask, request, jsonify
from flask_cors import CORS
from process import process_bp, db, add, check_process_by_name

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = Flask(__name__)
CORS(app)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(BASE_DIR, 'mydatabase.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
app.register_blueprint(process_bp)

@app.route('/upload_images', methods=['POST'])
def upload_images():
    # Check if the POST request has files
    if 'files' not in request.files:
        return jsonify({'error': 'No files found in the request'}), 400

    files = request.files.getlist('files')
    if not files:
        return jsonify({'error': 'No files found in the request'}), 400

    # Check for additional info in the form data
    dataset_name = request.form.get('datasetName')
    resize_x = request.form.get('resizeX')
    resize_y = request.form.get('resizeY')
    patch_size = request.form.get('patchSize')
    class_names = request.form.get('classNames')

    # Validate the additional info
    if not all([dataset_name, resize_x, resize_y, patch_size, class_names]):
        return jsonify({'error': 'Missing additional information in the request'}), 400

    try:
        resize_x = int(resize_x)
        resize_y = int(resize_y)
        patch_size = int(patch_size)
        class_names_array = class_names.split(',')
    except ValueError:
        return jsonify({'error': 'Invalid numerical values in the additional information'}), 400

    # Validate resize dimensions and patch size
    if resize_x < 320 or resize_y < 320 or patch_size < 32 or resize_x % patch_size != 0 or resize_y % patch_size != 0:
        return jsonify({'error': 'Invalid resize or patch size dimensions'}), 400

    # Check if Process with dataset_name already exists
    if check_process_by_name(dataset_name):
        return jsonify({'error': f'Process with name "{dataset_name}" already exists'}), 400

    # Check if dataset with dataset_name already exists
    response = requests.get(f'http://localhost:8080/check_dataset/{dataset_name}')
    if response.status_code == 200:
        data = response.json()
        if data.get('exists'):
            return jsonify({'error': f'Dataset with name "{dataset_name}" already exists'}), 400
    else:
        return jsonify({'error': 'Failed to check if dataset exists'}), 500


    folder_path = os.path.join('datasets', dataset_name)
    
    # Create the folder if it doesn't exist
    os.makedirs(folder_path, exist_ok=True)

    # Save each file to the disk
    saved_files = []
    for file in files:
        file_path = os.path.join(folder_path, file.filename)
        file.save(file_path)
        saved_files.append(file.filename)
    
    add(dataset_name, len(files), resize_x, resize_y, patch_size, class_names)

    # Return the response including additional info
    return jsonify({
        'message': 'Files uploaded successfully',
        'files': saved_files,
        'dataset_name': dataset_name,
        'resize_x': resize_x,
        'resize_y': resize_y,
        'patch_size': patch_size,
        'class_names': class_names_array
    }), 201

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400

    uploaded_file = request.files['file']
    # Check if the file is a video file (modify the condition as needed)
    if uploaded_file.filename.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):

        # Construct folder path based on current timestamp
        timestamp = time.strftime("%Y%m%d%H%M%S")
        folder_path = os.path.join(BASE_DIR, 'working', timestamp)
        # Create the folder if it doesn't exist
        os.makedirs(folder_path, exist_ok=True)
        # Construct absolute file path
        file_path = os.path.join(folder_path, uploaded_file.filename)

        # Save the file to disk
        uploaded_file.save(file_path)

        # Create active_session.json file
        active_session_file_path = os.path.join(BASE_DIR, 'active_session.json')
        with open(active_session_file_path, 'w') as active_session_file:
            json.dump({'active_session': timestamp}, active_session_file)

        return jsonify({'message': 'File uploaded successfully'}), 200
    else:
        return jsonify({'error': 'Only video files are allowed'}), 400

def calculate_summary_data(json_file_path):
    summary_data = {
        'session_id': "",
        'elapsed_time': 0,
        'captures': 0,
        'speed': 13,
        'position': 0,
        'defect_count': 0
    }

    active_session = find_active_session()
    
    if active_session:
        summary_data['session_id'] = active_session

        if os.path.exists(json_file_path):
            df = pd.read_json(json_file_path, orient='records', lines=True)

            if not df.empty:
                first_entry = df.iloc[0]
                last_entry = df.iloc[-1]

                summary_data['defect_count'] = len(df)
                summary_data['elapsed_time'] = int(last_entry['time'] - first_entry['time'])
                summary_data['captures'] = int(last_entry['frame_pos']) + 1
                summary_data['position'] = int(summary_data['captures'] * summary_data['speed'])

    return summary_data

@app.route('/get-frame', methods=['GET'])
def get_frame_info():

    # Check if there's an active session
    active_session = find_active_session()

    if not active_session:
        return jsonify({'message': 'No active session'}), 404

    session_folder = os.path.join(BASE_DIR, 'working', active_session)
    if not os.path.exists(session_folder):
        return jsonify({'message': 'Session folders not created'}), 500

    # Move a file that is ready to be displayed, if there's any
    ready_folder = os.path.join(session_folder, "ready")
    destination_path = os.path.join(session_folder, 'last.jpg')
    ready_files = []
    if os.path.exists(ready_folder):
        ready_files = [f for f in os.listdir(ready_folder) if f.startswith('frame_') and f.endswith('.jpg')]
        ready_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))

    if ready_files:
        frame_to_process = ready_files[0]
        frame_path = os.path.join(ready_folder, frame_to_process)

        # Move the image file to the session folder
        shutil.move(frame_path, destination_path)

    # Get frame data from last image
    frame_data = None
    if os.path.exists(destination_path):
        with open(destination_path, 'rb') as frame_file:
            frame_data = base64.b64encode(frame_file.read()).decode('utf-8')

    # Get rollmap information from session
    rollmaps_images = []
    rollmaps_folder = os.path.join(session_folder, 'rollmaps')
    if os.path.exists(rollmaps_folder):
        rollmaps_files = [f for f in os.listdir(rollmaps_folder) if f.endswith('.jpg')]
        for rollmap_file in rollmaps_files:
            rollmap_path = os.path.join(rollmaps_folder, rollmap_file)
            with open(rollmap_path, 'rb') as rollmap_file:
                rollmap_data = base64.b64encode(rollmap_file.read()).decode('utf-8')
                rollmaps_images.append(rollmap_data)
    
    # Read defect.json to build the summary_data object
    defect_json_path = os.path.join(session_folder, 'defects.json')
    summary_data = calculate_summary_data(defect_json_path)

    return jsonify({
        'frame_data': frame_data,
        'rollmaps': rollmaps_images,
        'summary': summary_data,
        'message': f'Found image and {len(rollmaps_images)} rollmaps'
    }), 200

def find_active_session():
    active_session_file_path = os.path.join(BASE_DIR, 'active_session.json')

    if os.path.exists(active_session_file_path):
        with open(active_session_file_path, 'r') as active_session_file:
            data = json.load(active_session_file)
            return data.get('active_session')
    else:
        return None

@app.route('/reset-sessions', methods=['GET'])
def reset_sessions():
    working_folder = os.path.join(BASE_DIR, 'working')
    active_session_file_path = os.path.join(BASE_DIR, 'active_session.json')

    try:
        # Delete all folders inside the working folder
        for folder_name in os.listdir(working_folder):
            folder_path = os.path.join(working_folder, folder_name)
            if os.path.isdir(folder_path):
                shutil.rmtree(folder_path)

        # Delete the active_session.json file
        if os.path.exists(active_session_file_path):
            os.remove(active_session_file_path)

        return jsonify({'message': 'Sessions reset successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/get-defects', methods=['GET'])
def get_defects_info():

    active_session = find_active_session()

    if not active_session:
        return jsonify({'message': 'No active session'}), 404

    json_file_path = os.path.join(BASE_DIR, 'working', active_session, 'defects.json')

    try:
        # Check if the file exists
        if os.path.exists(json_file_path) and os.path.isfile(json_file_path):
            # Read the content of the JSON file
            with open(json_file_path, 'r') as file:
                json_data = [json.loads(line) for line in file]
            # Return the JSON data as a response
            return jsonify({'defects': json_data}), 200
        else:
            # Return a JSON response with an error message if the file does not exist
            return jsonify({'error': 'File not found'}), 404
    except Exception as e:
        # Return a JSON response with the error message if an exception occurs
        return jsonify({'error': str(e)}), 500


# ANSI escape codes for text formatting
RESET = "\033[0m"
BOLD = "\033[1m"
UNDERLINE = "\033[4m"

# ANSI escape codes for text colors
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

# Get images from feed only every FRAME_SKIP frames
# SECONDS TO SKIP = VIDEO ORIGINAL HEIGHT / (VIDEO ORIGINAL FPS * VIDEO SPEED PER FRAME IN PIXELS)
# SECONDS TO SKIP = 600 / (60 * 5) = 2
# FRAMES TO SKIP = (VIDEO ORIGINAL FPS * SECONDS TO SKIP) - 1 = (60 * 2) - 1 = 119
FRAME_SKIP = 119
CLOCK_SECS = 1
ROLLMAP_XLIMIT = 80

# Considering 512px = 15cm, 0.3 is the approximate ratio px/cm
CAM_FRAME_HEIGHT_PX = 512
CAM_FRAME_HEIGHT_CM = 15

def create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

# Global variables
processing = False
active_session = None

working_folder = create_folder(os.path.join(BASE_DIR, 'working'))
session_folder = None
frames_folder = None
ready_folder = None
defects_data_json_path = None
rollmaps_folder = None

defect_summary_data = { 
        'Elapsed time (s)': 0,
        'Captures': 0,
        'Speed (m/min)': 49.6,
        'Position (m)': 0,
        'Defect Count': 0
    }

# Function to check active_session.json and update global variable if necessary
def check_active_session():
    global active_session, session_folder, frames_folder, ready_folder, rollmaps_folder, defects_data_json_path
    while True:
        print(RED + "[check_active_session]"  + RESET + " Checking for changes in active session...")
        try:
            active_session_file_path = os.path.join(BASE_DIR, 'active_session.json')
            if os.path.exists(active_session_file_path):
                with open(active_session_file_path, 'r') as active_session_file:
                    data = json.load(active_session_file)
                    new_active_session = data.get('active_session')

                    # If there's no active session 
                    # or new active session is different then current, change it
                    if not active_session or int(new_active_session) != int(active_session):
                        active_session = new_active_session

                        print(RED + "[check_active_session]"  + RESET + f" Active session changed from {active_session} to {new_active_session}")

                        # Construct folder path for the new active session
                        session_folder = os.path.join(working_folder, new_active_session)

                        # Create necessary folders/files inside session folder
                        frames_folder = create_folder(os.path.join(session_folder, "frames"))
                        ready_folder = create_folder(os.path.join(session_folder, "ready"))
                        defects_data_json_path = os.path.join(session_folder, "defects.json")
                        rollmaps_folder = create_folder(os.path.join(session_folder, 'rollmaps'))
            else:
                print(RED + "[check_active_session]" + RESET + " No session folder found")

            time.sleep(5)  # Check every 5 seconds
        except Exception as e:
            print("Error occurred:", e)

def split_list_by_limit(input_list, limit):
    result = []
    current_sum = 0
    curr_limit = limit
    sublist = []

    for value in input_list:
        if value <= curr_limit:
            sublist.append(value)
        else:
            result.append(sublist)
            sublist = [value]
            curr_limit += limit

    if sublist:
        result.append(sublist)

    return result

def split_list_into_structure(input_list, structure):
    result = []
    idx = 0

    for length in structure:
        sublist = input_list[idx: idx + length]
        result.append(sublist)
        idx += length

    return result

def save_entries_to_json(json_file, entries):
    # Check if JSON file already exists
    file_exists = os.path.exists(json_file)

    # Convert the list of dictionaries to a pandas DataFrame
    df = pd.DataFrame(entries)

    if file_exists:
        mode = 'a'
    else:
        mode = 'w'
    
    # Save the DataFrame to the JSON file
    df.to_json(json_file, mode=mode, orient='records', lines=True)

def read_entries_from_json(json_file):
    df = pd.read_json(json_file)
    entries = df.values.tolist()
    return entries

def break_video_into_frames():
    global defect_summary_data
    while True:
        print(BLUE + "[break_video_into_frames]" + RESET + " Searching for new videos in session...")

        if session_folder and os.path.exists(session_folder):
            video_files = [f for f in os.listdir(session_folder) if f.endswith('.mp4')]
            if video_files:
                print(BLUE + "[break_video_into_frames]" + RESET + " Found new video in session folder!")
                video_file = video_files[0]  # Assume only one video file in the folder
                video_path = os.path.join(session_folder, video_file)

                # Open the video file
                cap = cv2.VideoCapture(video_path)

                frame_count = 0
                success, frame = cap.read()

                while success:
                    if frame_count % FRAME_SKIP == 0:
                        frame_path = os.path.join(frames_folder, f"frame_{frame_count}.jpg")
                        cv2.imwrite(frame_path, frame)
                        defect_summary_data['Captures'] += 1

                    success, frame = cap.read()
                    frame_count += 1

                # Release the video capture object
                cap.release()

                # Delete the video file
                os.remove(video_path)

        # Wait for 5 seconds before checking again
        time.sleep(5)

# Function to get coordinates of neighbors
def get_neighbors_coordinates(x, y, img_width, img_height, cell_size):
    neighbors = []
    for i in range(max(0, x - cell_size), min(img_width, x + cell_size + 1), cell_size):
        for j in range(max(0, y - cell_size), min(img_height, y + cell_size + 1), cell_size):
            if i != x or j != y:
                neighbors.append((i, j, i + cell_size, j + cell_size))

    return neighbors

def process_frames_in_frames_folder():
    global model, defect_summary_data
    while True:
        print(GREEN + "[process_frames_in_frames_folder]" + RESET + f" Searching for frames...")

        if frames_folder and os.path.exists(frames_folder):
            frame_files = [f for f in os.listdir(frames_folder) if f.startswith('frame_') and f.endswith('.jpg')]
            frame_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))

            if frame_files:
                print(GREEN + "[process_frames_in_frames_folder]" + RESET + f" Found frames!")
                frame_to_process = frame_files[0]
                frame_path = os.path.join(frames_folder, frame_to_process)
                destination_path = os.path.join(ready_folder, frame_to_process)

                # Read the frame, grayscale, resize frame
                input_image = cv2.imread(frame_path)
                gray_image = cv2.cvtColor(input_image, cv2.COLOR_BGR2GRAY)
                input_image = cv2.merge((gray_image, gray_image, gray_image))
                input_image = cv2.resize(input_image, (768, 512))

                # Break the image into cells
                cell_size = 64
                img_height, img_width, _ = input_image.shape
                images = []
                image_coordinates = []
                for y in range(0, img_height, cell_size):
                    for x in range(0, img_width, cell_size):
                        image = input_image[y:y+cell_size, x:x+cell_size]
                        images.append(image)
                        image_coordinates.append((x, y, x+cell_size, y+cell_size))

                print(GREEN + "[process_frames_in_frames_folder]" + RESET + f" Number of patches: {len(images)}")

                # Defect inference
                conf1 = 0.999
                results = model.predict(source=images)

                # Filter defects and collect neighbors cells (8 cells around central cell)
                # We perform a second detection on neighboring cells for the main class
                neighbors_dict = {}  # Dictionary to store neighbors for each class
                marked_images = []
                top1 = []
                confs = []
                marked_coordinates = []
                for i in range(len(images)):
                    if results[i].probs.top1 != 0 and results[i].probs.top1conf > conf1:
                        top1.append(int(results[i].probs.top1))
                        confs.append(results[i].probs.top1conf)
                        marked_images.append(images[i])
                        marked_coordinates.append(image_coordinates[i])

                        # Calculate neighbor cells
                        # Create/update dictionary based on class
                        neighbors = get_neighbors_coordinates(*image_coordinates[i][:2], img_height, img_width, cell_size)
                        class_id = results[i].probs.top1

                        if class_id not in neighbors_dict:
                            neighbors_dict[class_id] = set()
                        neighbors_dict[class_id].update(neighbors)

                        # Remove marked images since they are not neighboring cells
                        neighbors_dict[class_id] = neighbors_dict[class_id] - set(marked_coordinates)

                # Perform second prediction for neighbors
                # Second prediction should have a smaller threshold
                conf2 = 0.5

                for class_id, neighbors in neighbors_dict.items():
                    neighbor_images = []
                    ncoords = []

                    for neighbor_coords in neighbors:
                        for i, coord in enumerate(image_coordinates):
                            if neighbor_coords == coord:
                                neighbor_images.append(images[i])
                                ncoords.append(image_coordinates[i])

                    if neighbor_images:
                        neighbor_results = model.predict(source=neighbor_images)
                        for i in range(len(neighbor_images)):
                            if neighbor_results[i].probs.top1 == class_id and \
                                neighbor_results[i].probs.top1conf > conf2:
                                
                                top1.append(class_id)
                                confs.append(neighbor_results[i].probs.top1conf)
                                marked_images.append(neighbor_images[i])
                                marked_coordinates.append(ncoords[i])

                print(GREEN + "[process_image]" + RESET +
                      f' Number of patches with defect: {len(marked_images)}')
                print(GREEN + "[process_image]" + RESET +
                      f' Ratio defect/good: {len(marked_images)/len(images)*100}%')
                defect_summary_data['Defect Count'] += len(marked_images)

                # Save defect images to dictionary
                classes = ['good', 'hole', 'objects', 'oil spot', 'thread error']
                new_entries = []
                for i in range(len(marked_images)):
                    # Convert the image to a base64 string
                    _, buffer = cv2.imencode('.jpg', marked_images[i])
                    base64_image = base64.b64encode(buffer).decode('utf-8')
                    index = int(frame_to_process.split('_')[1].split('.')[0])
                    new_entries.append({'frame_pos': int(index/FRAME_SKIP),
                                        'frame_index': index,
                                        'camera': 'Cam_0',
                                        'class': classes[top1[i]],
                                        'confidence': float(confs[i]),
                                        'pos_x': marked_coordinates[i][0],
                                        'pos_y': marked_coordinates[i][1],
                                        'time': int(time.time()),
                                        'img_base64': base64_image})

                save_entries_to_json(defects_data_json_path, new_entries)

                # Color the input image using colored markings
                color_mapping = {
                    'good': (0, 255, 255),
                    'hole': (0, 0, 255),
                    'objects': (255, 0, 0),
                    'oil spot': (0, 255, 0),
                    'thread error': (42, 42, 165)
                }
                for i in range(len(marked_coordinates)):
                    x1, y1, x2, y2 = marked_coordinates[i]
                    cv2.rectangle(input_image, (x1, y1), (x2, y2), color_mapping[new_entries[i]['class']], 2)

                # Save the colored image to the ready folder
                cv2.imwrite(destination_path, input_image)
                print(f"Moved {frame_to_process} to ready folder")

                create_defect_scatter_plot()

                # Remove the processed frame from the frames folder
                os.remove(frame_path)
            else:
                global processing
                processing = False

        # Wait for 5 seconds before checking again
        time.sleep(5)

def create_defect_scatter_plot():
    global defect_summary_data
    # Check if the 'defects.json' file exists
    if not os.path.exists(defects_data_json_path):
        print(
            YELLOW + "[create_defect_scatter_plot]" + RESET + f" No {defects_data_json_path} file found.")
        return -1

    # Read data from the JSON file using pandas
    df = pd.read_json(defects_data_json_path, orient='records', lines=True)

    x_positions = []
    y_positions = []
    defect_class_color = []

    # Get number of last detected frame to calculate actual cam position
    defect_summary_data['Position (m)'] = (
        (df.iloc[-1]['frame_pos'] + 1) + 1) * CAM_FRAME_HEIGHT_CM / 100

    classes = {'hole': 'red', 'objects': 'blue',
               'oil spot': 'green', 'thread error': 'brown'}

    for index, entry in df.iterrows():
        frame_pos = int(entry['frame_pos'])
        frame_class = entry['class']
        pos_x = int(entry['pos_x'])
        pos_y = int(entry['pos_y'])

        # For 512px = 15cm, 0.3 is the approximate ratio px/cm
        ratio = CAM_FRAME_HEIGHT_CM/CAM_FRAME_HEIGHT_PX
        x_positions.append(ratio * (frame_pos * CAM_FRAME_HEIGHT_PX + pos_y))
        y_positions.append(pos_x * ratio)
        defect_class_color.append(classes[frame_class])

    # If any position goes over limit it breaks it down into multiple lists
    x_positions = split_list_by_limit(x_positions, ROLLMAP_XLIMIT)

    # Match the same broken down structure of x_position to the others
    y_positions = split_list_into_structure(
        y_positions, [len(sublist) for sublist in x_positions])
    defect_class_color = split_list_into_structure(
        defect_class_color, [len(sublist) for sublist in x_positions])

    plot_index = -1

    for info in zip(x_positions, y_positions, defect_class_color):
        plot_index += 1
        x, y, c = info
        plt.figure(figsize=(8.7, 3), dpi=100)
        scatter = plt.scatter(x, y, marker='o', color=c)

        # Create a custom legend
        # legend_labels = [plt.Line2D([0], [0], marker='o', color='w', label=class_name,
        #                             markerfacecolor=class_color) for class_name, class_color in classes.items()]

        # plt.legend(handles=legend_labels, loc='upper right',
        #            bbox_to_anchor=(1.24, 1.0))

        plt.xlim(ROLLMAP_XLIMIT * plot_index - 5,
                 ROLLMAP_XLIMIT * (plot_index + 1))
        plt.ylim(-2, 24)
        plt.xlabel('Vertical position (cm)')
        plt.ylabel('Horizontal position (cm)')
        plt.grid(True)
        save_path = os.path.join(
            rollmaps_folder, f'rollmap_plot_{plot_index}.jpg')
        plt.savefig(save_path, bbox_inches='tight')
        plt.close()

    return plot_index

# Start the thread
active_session_thread = threading.Thread(target=check_active_session)
active_session_thread.daemon = True
active_session_thread.start()

# Create and start the thread
model_file = os.path.join(BASE_DIR, 'models', 'yolov8s-cls_tilda400_50ep', 'weights', 'best.pt')
model = YOLO(model_file)
process_frames_in_frames_folder_thread = threading.Thread(target=process_frames_in_frames_folder)
process_frames_in_frames_folder_thread.daemon = True
process_frames_in_frames_folder_thread.start()

# Create and start the thread
video_processing_thread = threading.Thread(target=break_video_into_frames)
video_processing_thread.daemon = True
video_processing_thread.start()

if __name__ == '__main__':
    app.run(debug=True, threaded=True, port=8000)