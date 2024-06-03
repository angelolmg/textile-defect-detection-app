import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';

interface Model {
  id: number;
  modelName: string;
  modelArchitecture: string;
  epochs: number;
  dataset: string;
  trainSplit: number;
  valSplit: number;
  testSplit: number;
  augmentationRecipe: string;
}

@Injectable({
  providedIn: 'root'
})
export class ModelsService {
  private apiUrl = 'http://localhost:8090/api/models';

  constructor(private http: HttpClient) {}

  getModels(): Observable<Model[]> {
    return this.http.get<Model[]>(this.apiUrl);
  }

  addModel(model: Model): Observable<Model> {
    return this.http.post<Model>(this.apiUrl, model);
  }
}
