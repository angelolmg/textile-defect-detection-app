import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators, FormArray } from '@angular/forms';
import { ModelsService } from 'src/app/shared/services/models.service';
import { DatasetsService } from '../../shared/services/datasets.service';

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
  models: any[] = [];
  modelArchitectures = ['yolov8s-cls.pt'];
  datasets: any[] = [];
  augmentationRecipes: any[] = [];

  trainModelForm: FormGroup;

  constructor(private fb: FormBuilder, private modelsService: ModelsService, private datasetsService: DatasetsService) {
    this.trainModelForm = this.fb.group({
      modelName: ['', Validators.required],
      modelArchitecture: ['', Validators.required],
      epochs: ['', [Validators.required, Validators.min(1)]],
      dataset: ['', Validators.required],
      trainSplit: [0.8, [Validators.required, Validators.min(0), Validators.max(1)]],
      valSplit: [0.1, [Validators.required, Validators.min(0), Validators.max(1)]],
      testSplit: [0.1, [Validators.required, Validators.min(0), Validators.max(1)]],
      augmentationRecipe: ['', Validators.required],
      numAugmentations: this.fb.array([]),
      augmentationSeed: [null],
      trainingSeed: [null]
    });

    this.trainModelForm.get('dataset')?.valueChanges.subscribe(datasetName => {
      this.updateAugmentationFields(datasetName);
    });
  }

  ngOnInit(): void {
    this.datasetsService.getDatasets().subscribe(datasets => {
      this.datasets = datasets;
      console.log('Datasets:', this.datasets);
    });

    this.datasetsService.getAugmentationRecipes().subscribe(recipes => {
      this.augmentationRecipes = recipes;
      console.log('Augmentation Recipes:', this.augmentationRecipes);
    });

    this.getModelVersions('test01');
  }

  getRegisteredModels(): void {
    this.modelsService.getRegisteredModels().subscribe(
      data => {
        console.log('Registered Models:', data);
      },
      error => {
        console.error('Error fetching registered models:', error);
      }
    );
  }

  getModelVersions(modelName: string): void {
    this.modelsService.getModelVersions(modelName).subscribe(
      data => {
        this.models = data;
        console.log(`Model Versions for ${modelName}:`, this.models);
      },
      error => {
        console.error(`Error fetching model versions for ${modelName}:`, error);
      }
    );
  }

  get numAugmentations() {
    return this.trainModelForm.get('numAugmentations') as FormArray;
  }

  updateAugmentationFields(datasetName: string): void {
    this.numAugmentations.clear();
    const selectedDataset = this.datasets.find((d: any) => d.dataset_name === datasetName);
    console.log(selectedDataset);
    if (selectedDataset) {
      selectedDataset.class_names.split(',').forEach((className: string) => {
        this.numAugmentations.push(this.fb.group({
          className: [className],
          num: ['', [Validators.required, Validators.min(1), Validators.max(20)]]
        }));
      });
    }
  }

  onSubmit(): void {
    if (this.trainModelForm.valid) {
      const formValue = this.trainModelForm.value;
      const numAugmentations = formValue.numAugmentations.reduce((acc: any, item: any) => {
        acc[item.className] = item.num;
        return acc;
      }, {});

      const trainingTemplate = {
        ...formValue,
        numAugmentations
      };

      console.log('Training model with values:', trainingTemplate);
      this.modelsService.trainModel(trainingTemplate).subscribe((response) => {
        alert(response.message);
      });
    } else {
      console.error('Form is invalid');
    }
  }
}
