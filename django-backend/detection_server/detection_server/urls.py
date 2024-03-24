"""
URL configuration for detection_server project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path
from .views import upload_file, get_frame_info, reset_sessions

urlpatterns = [
    path('admin/', admin.site.urls),
    path('upload/', upload_file, name='upload_file'),
    path('get-frame/', get_frame_info, name='get_frame'),
    path('reset-sessions/', reset_sessions, name='reset_sessions'),
]

import os
import threading
import time
import cv2
import shutil
import ultralytics
from ultralytics import YOLO
from django.conf import settings
from PIL import Image
import base64
import datetime
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import json
import io

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

working_folder = create_folder(os.path.join(settings.BASE_DIR, 'detection_server', 'working'))
session_folder = None
frames_folder = None
ready_folder = None
defects_data_csv_path = None
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
    global active_session, session_folder, frames_folder, ready_folder, rollmaps_folder, defects_data_csv_path
    while True:
        print(RED + "[check_active_session]"  + RESET + " Checking for changes in active session...")
        try:
            active_session_file_path = os.path.join(settings.BASE_DIR, 'detection_server', 'active_session.json')
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
                        defects_data_csv_path = os.path.join(session_folder, "defects.csv")
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

def save_entries_to_csv(csv_file, entries):
    # Check if CSV file already exists
    file_exists = os.path.exists(csv_file)

    # Convert the list of dictionaries to a pandas DataFrame
    df = pd.DataFrame(entries)

    # If the file exists, append to it; otherwise, create a new file
    if file_exists:
        mode = 'a'
    else:
        mode = 'w'

    # Save the DataFrame to the CSV file
    df.to_csv(csv_file, mode=mode, index=False, header=not file_exists)

def read_entries_from_csv(csv_file):
    df = pd.read_csv(csv_file)
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
                rows, cols, _ = input_image.shape
                images = []
                image_coordinates = []
                for y in range(0, rows, cell_size):
                    for x in range(0, cols, cell_size):
                        image = input_image[y:y+cell_size, x:x+cell_size]
                        images.append(image)
                        image_coordinates.append((x, y, x+cell_size, y+cell_size))

                print(GREEN + "[process_frames_in_frames_folder]" + RESET + f" Number of patches: {len(images)}")

                # Defect inference
                results = model.predict(source=images, conf=0.25)

                # Filter defects
                marked_images = []
                top1 = []
                marked_coordinates = []
                for i in range(len(images)):
                    if results[i].probs.top1 != 0 and results[i].probs.top1conf > 0.99:
                        top1.append(int(results[i].probs.top1))
                        marked_images.append(images[i])
                        marked_coordinates.append(image_coordinates[i])

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
                                        'pos_x': marked_coordinates[i][0],
                                        'pos_y': marked_coordinates[i][1],
                                        'time': int(time.time()),
                                        'img_base64': base64_image})

                save_entries_to_csv(defects_data_csv_path, new_entries)

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
    # Check if the 'defects.csv' file exists
    if not os.path.exists(defects_data_csv_path):
        print(
            YELLOW + "[create_defect_scatter_plot]" + RESET + f" No {defects_data_csv_path} file found.")
        return -1

    # Read data from the CSV file using pandas
    df = pd.read_csv(defects_data_csv_path)

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
model_file = os.path.join(settings.BASE_DIR, 'detection_server', 'models', 'yolov8s-cls_tilda400_50ep', 'weights', 'best.pt')
model = YOLO(model_file)
process_frames_in_frames_folder_thread = threading.Thread(target=process_frames_in_frames_folder)
process_frames_in_frames_folder_thread.daemon = True
process_frames_in_frames_folder_thread.start()

# Create and start the thread
video_processing_thread = threading.Thread(target=break_video_into_frames)
video_processing_thread.daemon = True
video_processing_thread.start()