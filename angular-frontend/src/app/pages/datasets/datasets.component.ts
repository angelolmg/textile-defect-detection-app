import { Component, ViewChild, ElementRef } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';

@Component({
  selector: 'app-datasets',
  templateUrl: './datasets.component.html',
  styleUrls: ['./datasets.component.scss']
})
export class DatasetsComponent {
  @ViewChild('fileInput') fileInput: ElementRef<HTMLInputElement> | undefined;

  selectedFiles: File[] = [];

  constructor(private http: HttpClient) {}

  onFileSelected(event: any): void {
    this.selectedFiles.push(...event.target.files);
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    event.stopPropagation();
    if (event.dataTransfer && event.dataTransfer.files) {
      this.selectedFiles.push(...Array.from(event.dataTransfer.files));
    }
  }

  uploadFiles(): void {
    const formData = new FormData();
    this.selectedFiles.forEach(file => formData.append('files', file, file.name));

    const headers = new HttpHeaders();
    headers.append('Content-Type', 'multipart/form-data');

    this.http.post('http://localhost:8000/upload_images', formData, { headers }).subscribe(
      (response) => {
        alert('Files uploaded successfully');
        this.selectedFiles = []; // Clear the selected files after upload
      },
      (error) => {
        alert('Failed to upload files');
      }
    );
  }
}

