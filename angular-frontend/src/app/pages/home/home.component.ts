import { Component } from '@angular/core';
import { Subscription, interval } from 'rxjs';
import { HttpClient } from '@angular/common/http';

@Component({
  templateUrl: 'home.component.html',
  styleUrls: [ './home.component.scss' ]
})

export class HomeComponent {
  constructor(private http: HttpClient) {}

  images: string[] = [
    'assets/img01.jpg',
    'assets/img02.jpg',
    'assets/img03.jpg',

  ];
  currentImageIndex = 0;
  imageChangeSubscription: Subscription = new Subscription();

  ngOnInit() {
    this.startImageTimer();
  }

  startImageTimer() {
    this.imageChangeSubscription = interval(3000).subscribe(() => {
      this.currentImageIndex = (this.currentImageIndex + 1) % this.images.length;
    });
  }

  ngOnDestroy() {
    // Unsubscribe from the timer to avoid memory leaks
    if (this.imageChangeSubscription) {
      this.imageChangeSubscription.unsubscribe();
    }
  }

  selectedFile!: File;

  onFileSelected(event: any): void {
    this.selectedFile = event.target.files[0];
  }

  onSubmit(event: any): void {
    event.preventDefault(); // Prevent the default form submission behavior
    
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
