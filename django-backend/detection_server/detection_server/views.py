import os
from django.conf import settings
from django.http import JsonResponse

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
