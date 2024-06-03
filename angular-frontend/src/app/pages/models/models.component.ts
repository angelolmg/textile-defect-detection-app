import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { ModelsService } from 'src/app/shared/services/models.service';

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

@Component({
  selector: 'app-models',
  templateUrl: './models.component.html',
  styleUrls: ['./models.component.scss']
})
export class ModelsComponent implements OnInit {
  models = [
    { name: 'Model A', accuracy: '92%', dataset: 'Dataset 1', description: 'This is a description for Model A.' },
    { name: 'Model B', accuracy: '89%', dataset: 'Dataset 2', description: 'This is a description for Model B.' }
  ];

  mocks: Model[] = []

  modelArchitectures = ['Architecture 1', 'Architecture 2', 'Architecture 3'];
  datasets = ['Dataset 1', 'Dataset 2', 'Dataset 3'];
  augmentationRecipes = ['Recipe 1', 'Recipe 2', 'Recipe 3'];

  trainModelForm: FormGroup;

  constructor(private fb: FormBuilder, private modelsService: ModelsService) {
    this.trainModelForm = this.fb.group({
      modelName: ['', Validators.required],
      modelArchitecture: ['', Validators.required],
      epochs: ['', [Validators.required, Validators.min(1)]],
      dataset: ['', Validators.required],
      trainSplit: ['', [Validators.required, Validators.min(0), Validators.max(1)]],
      valSplit: ['', [Validators.required, Validators.min(0), Validators.max(1)]],
      testSplit: ['', [Validators.required, Validators.min(0), Validators.max(1)]],
      augmentationRecipe: ['', Validators.required]
    });
  }

  ngOnInit(): void {}

  onSubmit(): void {
    if (this.trainModelForm.valid) {
      console.log('Training model with values:', this.trainModelForm.value);
      this.modelsService.addModel(this.trainModelForm.value).subscribe((newModel: Model) => {
        this.mocks.push(newModel);
        this.trainModelForm.reset();
      });
    } else {
      console.error('Form is invalid');
    }
  }
}
