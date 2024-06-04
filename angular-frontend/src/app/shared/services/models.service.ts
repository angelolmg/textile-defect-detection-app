import { Injectable } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, of } from 'rxjs';

interface TrainingTemplate {
  modelName: string;
  modelArchitecture: string;
  epochs: number;
  dataset: string;
  trainSplit: number;
  valSplit: number;
  testSplit: number;
  augmentationRecipe: string;
  numAugmentations: any
}

@Injectable({
  providedIn: 'root'
})
export class ModelsService {
  private apiUrl = 'http://localhost:8090/api/models';

  constructor(private http: HttpClient) {}

  getModels(): Observable<TrainingTemplate[]> {
    return this.http.get<TrainingTemplate[]>(this.apiUrl);
  }

  trainModel(model: TrainingTemplate): Observable<any> {
    return this.http.post<TrainingTemplate>(this.apiUrl + '/train', model);
  }
}
