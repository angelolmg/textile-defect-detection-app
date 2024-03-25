import os
import csv
import base64
import time
import json
import shutil
import pandas as pd
from django.conf import settings
from django.http import JsonResponse, HttpResponse

def upload_file(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        # Check if the file is a video file (modify the condition as needed)
        if uploaded_file.name.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):

            # Construct folder path based on current timestamp
            timestamp = time.strftime("%Y%m%d%H%M%S")
            folder_path = os.path.join(settings.BASE_DIR, 'detection_server', 'working', timestamp)
            # Create the folder if it doesn't exist
            os.makedirs(folder_path, exist_ok=True)
            # Construct absolute file path
            file_path = os.path.join(folder_path, uploaded_file.name)

            # Save the file to disk
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)

            # Create active_session.json file
            active_session_file_path = os.path.join(settings.BASE_DIR, 'detection_server', 'active_session.json')
            with open(active_session_file_path, 'w') as active_session_file:
                json.dump({'active_session': timestamp}, active_session_file)

            return JsonResponse({'message': 'File uploaded successfully'})
        else:
            return JsonResponse({'error': 'Only video files are allowed'}, status=400)
    return JsonResponse({'error': 'No file uploaded'}, status=400)

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

def get_frame_info(request):

    # Check if there's an active session
    active_session = find_active_session()

    if not active_session:
        return JsonResponse({'message': 'No active session'}, status=404)

    session_folder = os.path.join(settings.BASE_DIR, 'detection_server', 'working', active_session)
    if not os.path.exists(session_folder):
        return JsonResponse({'message': 'Session folders not created'}, status=500)

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

    return JsonResponse({
        'frame_data': frame_data,
        'rollmaps': rollmaps_images,
        'summary': summary_data,
        'message': f'Found image and {len(rollmaps_images)} rollmaps'
    }, status=200)

def find_active_session():
    active_session_file_path = os.path.join(settings.BASE_DIR, 'detection_server', 'active_session.json')

    if os.path.exists(active_session_file_path):
        with open(active_session_file_path, 'r') as active_session_file:
            data = json.load(active_session_file)
            return data.get('active_session')
    else:
        return None

def reset_sessions(request):
    working_folder = os.path.join(settings.BASE_DIR, 'detection_server', 'working')
    active_session_file_path = os.path.join(settings.BASE_DIR, 'detection_server', 'active_session.json')

    try:
        # Delete all folders inside the working folder
        for folder_name in os.listdir(working_folder):
            folder_path = os.path.join(working_folder, folder_name)
            if os.path.isdir(folder_path):
                shutil.rmtree(folder_path)

        # Delete the active_session.json file
        if os.path.exists(active_session_file_path):
            os.remove(active_session_file_path)

        return JsonResponse({'message': 'Sessions reset successfully'})
    except Exception as e:
        return JsonResponse({'error': str(e)}, status=500)

def get_defects_info(request):

    active_session = find_active_session()

    if not active_session:
        return JsonResponse({'message': 'No active session'}, status=404)

    json_file_path = os.path.join(settings.BASE_DIR, 'detection_server', 'working', active_session, 'defects.json')

    try:
        # Check if the file exists
        if os.path.exists(json_file_path) and os.path.isfile(json_file_path):
            # Read the content of the JSON file
            with open(json_file_path, 'r') as file:
                json_data = [json.loads(line) for line in file]
            # Return the JSON data as a response
            return JsonResponse({'defects': json_data})
        else:
            # Return a JSON response with an error message if the file does not exist
            return JsonResponse({'error': 'File not found'}, status=404)
    except Exception as e:
        # Return a JSON response with the error message if an exception occurs
        return JsonResponse({'error': str(e)}, status=500)
