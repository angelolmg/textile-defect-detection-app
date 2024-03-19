import { Component, ElementRef, ViewChild } from '@angular/core';
import { Subscription, catchError, interval, of, switchMap } from 'rxjs';
import { HttpClient, HttpErrorResponse } from '@angular/common/http';

@Component({
  templateUrl: 'home.component.html',
  styleUrls: ['./home.component.scss'],
})
export class HomeComponent {
  constructor(private http: HttpClient) {}

  currentImageSource = '';
  imageChangeSubscription: Subscription = new Subscription();
  loading: boolean = false;

  ngOnInit() {
    this.update_image();
  }

  update_image() {
    this.imageChangeSubscription = interval(5000)
      .pipe(
        switchMap(() => {
          return this.http.get<any>('http://localhost:8000/get-frame/').pipe(
            catchError((error: HttpErrorResponse) => {
              if (error.status === 404) {
                console.log('No images available');
                this.loading = false;
                return of(null); // Return an observable with a null value to continue the observable chain
              } else {
                throw error; // Re-throw the error for other status codes
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
            const imageData = this.arrayBufferToBase64(response.image_data);
            this.currentImageSource =
              'data:image/jpeg;charset=utf-8;base64,' + response.image_data;
            console.log(this.currentImageSource);
          }
        },
        (error) => {
          console.error(error);
        }
      );
  }

  arrayBufferToBase64(buffer: ArrayBuffer): string {
    console.log(buffer);

    let binary = '';
    const bytes = new Uint8Array(buffer);
    const len = bytes.byteLength;
    for (let i = 0; i < len; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    return btoa(binary);
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

    this.http.post('http://localhost:8000/upload/', formData).subscribe(
      (response) => {
        console.log('File uploaded successfully:', response);
      },
      (error) => {
        console.error('Error uploading file:', error);
      }
    );
  }
}
