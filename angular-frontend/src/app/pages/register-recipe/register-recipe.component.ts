import { Component, OnInit } from '@angular/core';
import { FormBuilder, FormGroup, Validators } from '@angular/forms';
import { DatasetsService } from '../list-datasets/datasets.service';

@Component({
  selector: 'app-register-recipe',
  templateUrl: './register-recipe.component.html',
  styleUrls: ['./register-recipe.component.scss']
})
export class RegisterRecipeComponent implements OnInit{
  recipeForm: FormGroup;
  recipes: any[] = [];

  augmentations = [
    { name: 'horizontalFlip', label: 'Horizontal Flip' },
    { name: 'verticalFlip', label: 'Vertical Flip' },
    { name: 'randomRotate90', label: 'Random Rotate 90' },
    { name: 'rotate', label: 'Rotate' },
    { name: 'randomBrightnessContrast', label: 'Random Brightness Contrast' },
    { name: 'advancedBlur', label: 'Advanced Blur' },
    { name: 'randomBrightness', label: 'Random Brightness' },
    { name: 'randomContrast', label: 'Random Contrast' },
    { name: 'gaussNoise', label: 'Gauss Noise' },
    { name: 'unsharpMask', label: 'Unsharp Mask' },
  ];

  constructor(private fb: FormBuilder, private datasetsService: DatasetsService) {
    this.recipeForm = this.fb.group({
      recipeName: ['', Validators.required],
      horizontalFlip: [0, [Validators.min(0), Validators.max(1)]],
      verticalFlip: [0, [Validators.min(0), Validators.max(1)]],
      randomRotate90: [0, [Validators.min(0), Validators.max(1)]],
      rotate: [0, [Validators.min(0), Validators.max(1)]],
      randomBrightnessContrast: [0, [Validators.min(0), Validators.max(1)]],
      advancedBlur: [0, [Validators.min(0), Validators.max(1)]],
      randomBrightness: [0, [Validators.min(0), Validators.max(1)]],
      randomContrast: [0, [Validators.min(0), Validators.max(1)]],
      gaussNoise: [0, [Validators.min(0), Validators.max(1)]],
      unsharpMask: [0, [Validators.min(0), Validators.max(1)]]
    });
  }

  ngOnInit(): void {
    this.fetchRecipes();
  }

  onSubmit() {
    if (this.recipeForm.valid) {
      const formValues = this.recipeForm.value;
      this.datasetsService.saveAugmentationRecipe(formValues).subscribe(
        response => {
          console.log('Recipe saved successfully', response);
          alert(response.message);
        },
        error => {
          console.error('Error saving recipe', error);
          alert('Error saving recipe');
        }
      );
    } else {
      console.log('Form is not valid');
    }
  }

  fetchRecipes() {
    this.datasetsService.getAugmentationRecipes().subscribe(
      (response) => {
        this.recipes = response;
      },
      (error) => {
        console.error('Error fetching recipes', error);
      }
    );
  }
}
