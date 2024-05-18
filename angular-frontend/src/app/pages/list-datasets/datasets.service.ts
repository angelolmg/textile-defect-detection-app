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

@Injectable({
  providedIn: 'root'
})
export class DatasetsService {
  private apiUrl = 'http://localhost:8000'; // Adjust this URL to your backend's URL

  constructor(private http: HttpClient) { }

  getProcesses(): Observable<Process[]> {
    return this.http.get<Process[]>(`${this.apiUrl}/processes`);
  }
}
