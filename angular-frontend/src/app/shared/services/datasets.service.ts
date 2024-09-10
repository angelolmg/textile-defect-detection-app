import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

interface Process {
  id: number;
  name: string;
  total_images: number;
  images_left: number;
  resize_x: number;
  resize_y: number;
  patch_size: number;
  class_names: string;
}

interface Dataset {
  id: number;
  dataset_name: string;
  total_patches: number;
  patch_size: number;
  class_names: string;
}

@Injectable({
  providedIn: 'root'
})
export class DatasetsService {
  private apiUrl = 'http://localhost:8070'; // Adjust this URL to your backend's URL
  private dataUrl = 'http://localhost:8080'; // Adjust this URL to your backend's URL

  constructor(private http: HttpClient) { }

  getProcesses(): Observable<Process[]> {
    return this.http.get<Process[]>(`${this.apiUrl}/processes`);
  }

  getProcessByName(processName: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/process/${processName}`);
  }

  getImages(datasetName: string): Observable<any> {
    return this.http.get(`${this.apiUrl}/get_images/${datasetName}`);
  }

  getDatasets(): Observable<Dataset[]> {
    return this.http.get<Dataset[]>(`${this.dataUrl}/datasets`);
  }

  uploadZipDataset(formData: FormData): Observable<any> {
    return this.http.post(`${this.dataUrl}/upload_zip_dataset`, formData);
  }

  saveAugmentationRecipe(recipe: any): Observable<any> {
    return this.http.post(`${this.dataUrl}/save_augmentation`, recipe);
  }

  getAugmentationRecipes(): Observable<any> {
    return this.http.get(`${this.dataUrl}/get_augmentations`);
  }
}
