import os
import base64
from django.conf import settings
from django.http import JsonResponse, HttpResponse

def upload_file(request):
    if request.method == 'POST' and request.FILES.get('file'):
        uploaded_file = request.FILES['file']
        # Check if the file is a video file (modify the condition as needed)
        if uploaded_file.name.lower().endswith(('.mp4', '.avi', '.mov', '.mkv')):
            # Construct absolute file path
            file_path = os.path.join(settings.BASE_DIR, 'detection_server', 'files', uploaded_file.name)
            # Save the file to disk
            with open(file_path, 'wb+') as destination:
                for chunk in uploaded_file.chunks():
                    destination.write(chunk)
            return JsonResponse({'message': 'File uploaded successfully'})
        else:
            return JsonResponse({'error': 'Only video files are allowed'}, status=400)
    return JsonResponse({'error': 'No file uploaded'}, status=400)

def get_frame_info(request):
    working_folder = os.path.join(settings.BASE_DIR, 'detection_server', 'working')
    ready_folder = os.path.join(working_folder, "ready")
    rollmaps_folder = os.path.join(working_folder, 'rollmaps')

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
    else:
        return JsonResponse({'message': 'No images available'}, status=404)

    return JsonResponse({
        'frame_info': image_info,
        'frame_data': frame_data,
        'rollmaps': rollmaps_images,
        'message': f'Found image and {len(rollmaps_images)} rollmaps'
    }, status=200)