import { Component } from '@angular/core';
import { Subscription, catchError, interval, of, switchMap } from 'rxjs';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';

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
export class HomeComponent {
  constructor(private http: HttpClient) {}

  summaryData: SummaryData = new SummaryData();

  currentImageSource = '';
  imageChangeSubscription: Subscription = new Subscription();
  loading: boolean = false;
  rollmaps: any[] = [];
  currentRollmapIndex: number = 0;

  classes: ClassColors = {
    'hole': 'red',
    'objects': 'blue',
    'oil spot': 'green',
    'thread error': 'brown',
  };

  // Get the keys of the classes object
  getClassNames(): string[] {
    return Object.keys(this.classes);
  }

  get session_id(): string {
    return this.summaryData.session_id ? this.summaryData.session_id : ''
  }

  ngOnInit() {
    this.update_image();
  }

  update_image() {
    this.imageChangeSubscription = interval(1000)
      .pipe(
        switchMap(() => {
          return this.http.get<any>('http://localhost:8000/get-frame').pipe(
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
            if(response.frame_data)
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

  selectedFile!: File;
  selectedFileName: string = '';

  onFileSelected(event: any): void {
    this.selectedFile = event.target.files[0];

    if (this.selectedFile) {
      this.selectedFileName = this.selectedFile.name;
    } else {
      this.selectedFileName = '';
    }
  }

  onSubmit(event: any): void {
    event.preventDefault(); // Prevent the default form submission behavior
    this.loading = true;

    const formData = new FormData();
    formData.append('file', this.selectedFile);

    this.http.post('http://localhost:8000/upload', formData).subscribe(
      (response) => {
        console.log('File uploaded successfully:', response);
      },
      (error) => {
        console.error('Error uploading file:', error);
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
      .get<any>('http://localhost:8000/reset-sessions')
      .subscribe((response) => {
        console.log(response.message);
      });
  }
}
