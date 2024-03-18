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
from .views import upload_file

urlpatterns = [
    path('admin/', admin.site.urls),
    path('upload/', upload_file, name='upload_file'),
]

import os
import threading
import time
import cv2
import os
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

def create_folder(folder_path):
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)
    return folder_path

# Global variables
FRAME_SKIP = 119
processing = False
files_folder = create_folder(os.path.join(settings.BASE_DIR, 'detection_server', 'files'))
working_folder = create_folder(os.path.join(settings.BASE_DIR, 'detection_server', 'working'))
frames_folder = create_folder(os.path.join(working_folder, "frames"))
ready_folder = create_folder(os.path.join(working_folder, "ready"))


def search_video_to_process_in_files_folder():
    global processing

    while True:
        # Check if there are any video files in the 'files' directory
        print('Searching videos to process in the files folder...')
        files_folder_files = os.listdir(files_folder)
        video_files = [file for file in files_folder_files if file.lower().endswith(('.mp4', '.avi', '.mov', '.mkv', 'wmv.'))]

        if video_files and not processing:
            # If there are video files and not already processing, set processing flag to True
            processing = True
            video_file = video_files[0]  # Assuming you want to process the first video file found

            # Move the video file to the 'working' directory
            shutil.move(os.path.join(files_folder, video_file), working_folder)

            print(f"Processing video file: {video_file}")
            # Perform further processing here (e.g., analysis, conversion, etc.)

            # Once processing is complete, set processing flag back to False
            # processing = False

        # Wait for 5 seconds before checking again
        time.sleep(5)

def break_video_in_working_folder_into_frames():
    while True:
        video_files = [f for f in os.listdir(working_folder) if f.endswith('.mp4')]
        if video_files:
            video_file = video_files[0]  # Assume only one video file in the folder
            video_path = os.path.join(working_folder, video_file)
            frames_folder = os.path.join(working_folder, "frames")

            # Create frames folder if it doesn't exist
            os.makedirs(frames_folder, exist_ok=True)

            # Open the video file
            cap = cv2.VideoCapture(video_path)

            frame_count = 0
            success, frame = cap.read()

            while success:
                if frame_count % FRAME_SKIP == 0:
                    frame_path = os.path.join(frames_folder, f"frame_{frame_count}.jpg")
                    cv2.imwrite(frame_path, frame)

                success, frame = cap.read()
                frame_count += 1

            # Release the video capture object
            cap.release()

            # Delete the video file
            os.remove(video_path)
        else:
            print("No video file found in the working folder.")

        # Wait for 5 seconds before checking again
        time.sleep(5)

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

def process_frames_in_frames_folder():
    global model
    while True:
        frame_files = [f for f in os.listdir(frames_folder) if f.startswith('frame_') and f.endswith('.jpg')]
        frame_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))

        if frame_files:
            frame_to_process = frame_files[0]
            frame_path = os.path.join(frames_folder, frame_to_process)
            destination_path = os.path.join(ready_folder, frame_to_process)

            # Read the frame
            input_image = cv2.imread(frame_path)

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

            print("[process_frames_in_frames_folder] Number of patches:", len(images))

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

            print("[process_frames_in_frames_folder] Number of patches with defect:", len(marked_images))
            print("[process_frames_in_frames_folder] Ratio defect/good:", len(marked_images)/len(images)*100, "%")

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
                                    'date': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                                    'img_base64': base64_image})

                # Print new entries
                print("New entry:", new_entries[-1])

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

            # Remove the processed frame from the frames folder
            os.remove(frame_path)
        else:
            print('No files to process in frames folder.')

        # Wait for 5 seconds before checking again
        time.sleep(5)


# Start the thread
thread = threading.Thread(target=search_video_to_process_in_files_folder)
thread.daemon = True  # Daemonize the thread so it will be terminated when the main program exits
thread.start()

# Create and start the thread
model_file = os.path.join(settings.BASE_DIR, 'detection_server', 'models', 'yolov8s-cls_tilda400_50ep', 'weights', 'best.pt')
model = YOLO(model_file)
print(model.names)
process_frames_in_frames_folder_thread = threading.Thread(target=process_frames_in_frames_folder)
process_frames_in_frames_folder_thread.daemon = True
process_frames_in_frames_folder_thread.start()

# Create and start the thread
video_processing_thread = threading.Thread(target=break_video_in_working_folder_into_frames)
video_processing_thread.daemon = True
video_processing_thread.start()