import { Component, OnInit, OnDestroy } from '@angular/core';
import { FormBuilder, FormGroup } from '@angular/forms';
import { Subscription, catchError, interval, of, switchMap } from 'rxjs';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';
import { ModelsService } from 'src/app/shared/services/models.service';

interface ClassColors {
  [key: string]: string;
}

class SummaryData {
  session_id: string = '';
  elapsed_time: number = 0;
  captures: number = 0;
  speed: number = 0;
  position: number = 0;
  defect_count: number = 0;
}

@Component({
  templateUrl: 'home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent implements OnInit, OnDestroy {
  form: FormGroup;
  summaryData: SummaryData = new SummaryData();
  currentImageSource = '';
  imageChangeSubscription: Subscription = new Subscription();
  loading: boolean = false;
  rollmaps: any[] = [];
  currentRollmapIndex: number = 0;
  models: string[] = [];
  intervalDelayMs: number = 5000;

  classes: ClassColors = {
    'hole': 'red',
    'objects': 'blue',
    'oil spot': 'green',
    'thread error': 'brown',
  };

  constructor(
    private http: HttpClient,
    private modelsService: ModelsService,
    private fb: FormBuilder
  ) {
    // Initialize the form with form controls
    this.form = this.fb.group({
      file: [null],
      model: [''],
    });
  }

  ngOnInit() {
    this.update_image();
    this.fetchModelNames();
    // Subscribe to model changes
    this.form.get('model')?.valueChanges.subscribe((value) => {
      console.log('Selected model:', value);
    });
  }

  getClassNames(): string[] {
    return Object.keys(this.classes);
  }

  get session_id(): string {
    return this.summaryData.session_id ? this.summaryData.session_id : '';
  }

  fetchModelNames() {
    this.modelsService.getModelVersions('test01').subscribe(
      (models: any[]) => {
        // Extract model_name from each object and assign to this.models
        this.models = models.map(model => model.model_name);
      },
      (error: any) => {
        console.error('Error fetching model names:', error);
      }
    );
  }

  update_image() {
    this.imageChangeSubscription = interval(this.intervalDelayMs)
      .pipe(
        switchMap(() => {
          return this.http.get<any>('http://localhost:8070/get-frame').pipe(
            catchError((error: HttpErrorResponse) => {
              if (error.status === 404) {
                console.log('No images available');
                this.loading = false;
                return of(null); // Return an observable with a null value to continue the observable chain
              } else {
                console.error('Error occurred:', error);
                return of(null); // Continue the observable chain even if an error occurs
              }
            })
          );
        })
      )
      .subscribe(
        (response) => {
          if (response) {
            console.log(response);

            // Display the received image on the img tag
            if (response.frame_data)
              this.currentImageSource =
                'data:image/jpeg;charset=utf-8;base64,' + response.frame_data;

            this.rollmaps = response.rollmaps;
            this.summaryData = response.summary;
          }
        },
        (error) => {
          console.error('Error occurred in subscription:', error);
        }
      );
  }

  ngOnDestroy() {
    // Unsubscribe from the timer to avoid memory leaks
    if (this.imageChangeSubscription) {
      this.imageChangeSubscription.unsubscribe();
    }
  }

  onFileSelected(event: any): void {
    const file = event.target.files[0];
    this.form.patchValue({
      file: file,
    });
    this.form.get('file')?.updateValueAndValidity();
  }

  onSubmit(): void {
    if (this.form.invalid) {
      return;
    }

    const formData = new FormData();
    formData.append('file', this.form.get('file')?.value);
    formData.append('model', this.form.get('model')?.value);

    this.loading = true;
    this.http.post('http://localhost:8070/upload', formData).subscribe(
      (response) => {
        console.log('File uploaded successfully:', response);
        this.loading = false;
      },
      (error) => {
        console.error('Error uploading file:', error);
        this.loading = false;
      }
    );
  }

  get currentRollmapImage(): string {
    return this.rollmaps.length > 0
      ? 'data:image/jpeg;charset=utf-8;base64,' +
          this.rollmaps[this.currentRollmapIndex]
      : '';
  }

  nextRollmapImage(): void {
    if (this.rollmaps.length > 0) {
      this.currentRollmapIndex =
        (this.currentRollmapIndex + 1) % this.rollmaps.length;
    }
  }

  prevRollmapImage(): void {
    if (this.rollmaps.length > 0) {
      this.currentRollmapIndex =
        (this.currentRollmapIndex - 1 + this.rollmaps.length) %
        this.rollmaps.length;
    }
  }

  clearSessions() {
    this.http
      .get<any>('http://localhost:8070/reset-sessions')
      .subscribe((response) => {
        console.log(response.message);
      });
  }
}
