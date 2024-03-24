import os
import csv
import base64
import time
import json
import shutil
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

def calculate_summary_data(csv_file_path):
    summary_data = {
        'elapsed_time': 0,
        'captures': 0,
        'speed': 13,
        'position': 0,
        'defect_count': 0
    }

    with open(csv_file_path, 'r') as csv_file:
        csv_reader = csv.DictReader(csv_file)
        rows = list(csv_reader)
        if rows:
            first_row = rows[0]
            last_row = rows[-1]
            summary_data['defect_count'] = len(rows)
            summary_data['elapsed_time'] = int(last_row['time']) - int(first_row['time'])
            summary_data['captures'] = int(last_row['frame_pos']) + 1 if last_row else 0
            summary_data['position'] = summary_data['captures'] * summary_data['speed']
    return summary_data

def get_frame_info(request):
    active_session_file_path = os.path.join(settings.BASE_DIR, 'detection_server', 'active_session.json')

    if os.path.exists(active_session_file_path):
        with open(active_session_file_path, 'r') as active_session_file:
            data = json.load(active_session_file)
            new_active_session = data.get('active_session')
    else:
        return JsonResponse({'message': 'No active session'}, status=404)

    
    session_folder = os.path.join(settings.BASE_DIR, 'detection_server', 'working', new_active_session)
    ready_folder = os.path.join(session_folder, "ready")
    rollmaps_folder = os.path.join(session_folder, 'rollmaps')

    if not os.path.exists(ready_folder):
        return JsonResponse({'message': 'Session folders not created'}, status=500)
        
    ready_files = [f for f in os.listdir(ready_folder) if f.startswith('frame_') and f.endswith('.jpg')]
    ready_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))

    if ready_files:
        frame_to_process = ready_files[0]
        frame_path = os.path.join(ready_folder, frame_to_process)

        with open(frame_path, 'rb') as frame_file:
            frame_data = base64.b64encode(frame_file.read()).decode('utf-8')

        image_info = {'title': 'Frame Image', 'description': 'Frame Image Description'}

        frame_response = HttpResponse(content=frame_data, content_type='image/jpeg')
        frame_response['Content-Disposition'] = 'attachment; filename="frame.jpg"'

        os.remove(frame_path)

        rollmaps_images = []
        if os.path.exists(rollmaps_folder):
            rollmaps_files = [f for f in os.listdir(rollmaps_folder) if f.endswith('.jpg')]
            for rollmap_file in rollmaps_files:
                rollmap_path = os.path.join(rollmaps_folder, rollmap_file)
                with open(rollmap_path, 'rb') as rollmap_file:
                    rollmap_data = base64.b64encode(rollmap_file.read()).decode('utf-8')
                    rollmaps_images.append(rollmap_data)
        
        # Read defect.csv to calculate summary_data
        defect_csv_path = os.path.join(session_folder, 'defects.csv')
        summary_data = calculate_summary_data(defect_csv_path)

    else:
        return JsonResponse({'message': 'No images available'}, status=404)

    return JsonResponse({
        'frame_info': image_info,
        'frame_data': frame_data,
        'rollmaps': rollmaps_images,
        'summary': summary_data,
        'message': f'Found image and {len(rollmaps_images)} rollmaps'
    }, status=200)

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