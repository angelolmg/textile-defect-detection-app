import { Component, ViewChild, ElementRef } from '@angular/core';
import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Router } from '@angular/router';

@Component({
  selector: 'app-datasets',
  templateUrl: './datasets.component.html',
  styleUrls: ['./datasets.component.scss']
})
export class DatasetsComponent {
  selectedFiles: File[] = [];
  datasetName: string = '';
  resizeX: number = 320;
  resizeY: number = 320;
  patchSize: number = 32;
  classNames: string = '';
  minImagesUpload: number = 3;

  constructor(private http: HttpClient,
              private router: Router) {}

  onFileSelected(event: any): void {
    this.selectedFiles = Array.from(event.target.files);
  }

  onDragOver(event: DragEvent): void {
    event.preventDefault();
  }

  onDrop(event: DragEvent): void {
    event.preventDefault();
    if (event.dataTransfer) {
      this.selectedFiles = Array.from(event.dataTransfer.files);
    }
  }

  validateInputs(): boolean {
    const classList = this.classNames.split(',');
    if (classList.length === 0 || classList.some(cls => !cls.trim())) {
      alert('Class names must be a comma-separated list of non-empty strings.');
      return false;
    }
    if (this.resizeX < 320 || this.resizeY < 320) {
      alert('Minimum resize size is 320x320.');
      return false;
    }
    if (this.patchSize < 32) {
      alert('Minimum patch size is 32.');
      return false;
    }
    if (this.resizeX % this.patchSize !== 0 || this.resizeY % this.patchSize !== 0) {
      alert('Resize dimensions must be evenly divisible by patch size.');
      return false;
    }
    return true;
  }

  uploadFiles(): void {
    if (this.selectedFiles.length < this.minImagesUpload) {
      alert('You must select at least '+ this.minImagesUpload +' images to upload.');
      return;
    }
    if (!this.validateInputs()) {
      return;
    }

    const formData = new FormData();
    this.selectedFiles.forEach(file => formData.append('files', file, file.name));

    formData.append('datasetName', this.datasetName);
    formData.append('resizeX', this.resizeX.toString());
    formData.append('resizeY', this.resizeY.toString());
    formData.append('patchSize', this.patchSize.toString());
    formData.append('classNames', this.classNames.toString());

    const headers = new HttpHeaders();
    headers.append('Content-Type', 'multipart/form-data');

    this.http.post('http://localhost:8000/upload_images', formData, { headers }).subscribe(
      (response) => {
        alert('Files uploaded successfully');
        this.selectedFiles = []; // Clear the selected files after upload
        this.router.navigate(['/list-datasets']);
      },
      (error) => {
        alert('Failed to upload files');
      }
    );
  }
}

