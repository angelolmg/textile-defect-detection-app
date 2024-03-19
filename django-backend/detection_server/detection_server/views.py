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

    ready_files = [f for f in os.listdir(ready_folder) if f.startswith('frame_') and f.endswith('.jpg')]
    ready_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0])) 

    # Check if there are any images ready to send
    if ready_files:
        # Path to the first image file in the sorted list
        frame_to_process = ready_files[0] 
        image_path = os.path.join(ready_folder, frame_to_process)

        # Read the image file content
        with open(image_path, 'rb') as image_file:
            image_data = base64.b64encode(image_file.read()).decode('utf-8')

        # Additional information about the image (if needed)
        image_info = {'title': 'Image Title', 'description': 'Image Description'} 

        # Create an HttpResponse object with the image data as content
        response = HttpResponse(content=image_data, content_type='image/jpeg')

        # Set additional headers (optional)
        response['Content-Disposition'] = 'attachment; filename="image.jpg"'

        # Remove the processed image file
        os.remove(image_path)

        # Return the JSON response with the image data and additional information
        return JsonResponse({'image_info': image_info, 'image_data': response.content.decode('latin1')})
    else:
        # Return a JSON response indicating that there are no images available
        return JsonResponse({'message': 'No images available'}, status=404)
