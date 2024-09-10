import { Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { DatasetsService } from '../../shared/services/datasets.service';
import { HttpClient } from '@angular/common/http';

@Component({
  selector: 'app-patching',
  templateUrl: './patching.component.html',
  styleUrls: ['./patching.component.scss']
})
export class PatchingComponent implements OnInit {
  datasetName: string  = '';
  images: { filename: string, data: string }[] = [];
  currentIndex: number = 0;
  process: any = null;
  defaultClass: string = '';
  remainingClasses: string[] = [];
  selectedClass: string = '';
  resizeX: number = 0;
  resizeY: number = 0;
  patchSize: number = 0;
  isCanvasClickHandlerSet = false; // Flag to track if the canvas click handler is already set
  datasetSubmited: boolean = false;

  // Data structure to hold coordinates
  coordinatesData: { [key: string]: { [key: string]: [number, number][] } } = {};

  constructor(
    private route: ActivatedRoute,
    private datasetsService: DatasetsService,
    private http: HttpClient,
    private router: Router
  ) { }

  ngOnInit(): void {
    this.datasetName = this.route.snapshot.paramMap.get('datasetName') || '';
    this.fetchImages();
    this.fetchProcess();
  }

   // Method to check if there are unsaved changes
   canDeactivate(): boolean {
    // You can implement a more sophisticated check here
    // For simplicity, we'll assume that if there is any data in coordinatesData, there are unsaved changes
    // You can also check if the dataset has been submitted
    return Object.keys(this.coordinatesData).length === 0 || this.datasetSubmited;
  }

  fetchImages(): void {
    this.datasetsService.getImages(this.datasetName).subscribe(
      (data) => {
        this.images = data.images;
        this.currentIndex = 0;
        this.drawImageWithGrid();
      },
      (error) => console.error('There was an error!', error)
    );
  }

  fetchProcess(): void {
    this.datasetsService.getProcessByName(this.datasetName).subscribe(
      (data) => {
        this.process = data;
        const classNames = this.process.class_names.split(',');
        this.defaultClass = classNames[0];
        this.remainingClasses = classNames.slice(1);
        this.selectedClass = this.defaultClass; // Set the default class
        this.resizeX = this.process.resize_x;
        this.resizeY = this.process.resize_y;
        this.patchSize = this.process.patch_size;

        // Initialize the coordinatesData structure
        this.images.forEach(image => {
          this.coordinatesData[image.filename] = {};
          this.remainingClasses.forEach(cls => this.coordinatesData[image.filename][cls] = []);
        });

        this.drawImageWithGrid();
        this.setupCanvasClickHandler();
      },
      (error) => console.error('There was an error!', error)
    );
  }

  prevImage(): void {
    if (this.currentIndex > 0) {
      this.currentIndex--;
      this.drawImageWithGrid();
    }
  }

  nextImage(): void {
    if (this.currentIndex < this.images.length - 1) {
      this.currentIndex++;
      this.drawImageWithGrid();
    }
  }

  getCurrentImage() {
    return this.images[this.currentIndex];
  }

  getColorForClass(cls: string): string {
    const colors = ['#FF0000', '#00FF00', '#0000FF', '#FFFF00', '#FF00FF', '#00FFFF'];
    const index = this.remainingClasses.indexOf(cls);
    return colors[index % colors.length];
  }

  drawImageWithGrid(): void {
    const imageData = this.getCurrentImage();
    if (!imageData || !this.process) return;

    const canvas: HTMLCanvasElement = <HTMLCanvasElement>document.getElementById('imageCanvas');
    const ctx: CanvasRenderingContext2D | null = canvas.getContext('2d');
    if (!ctx) return;

    const image = new Image();
    image.onload = () => {
      // Clear the canvas
      ctx.clearRect(0, 0, canvas.width, canvas.height);

      // Set canvas size
      canvas.width = this.resizeX;
      canvas.height = this.resizeY;

      // Draw the image
      ctx.drawImage(image, 0, 0, this.resizeX, this.resizeY);

      // Draw the grid
      for (let x = 0; x < this.resizeX; x += this.patchSize) {
        for (let y = 0; y < this.resizeY; y += this.patchSize) {
          // Check if this cell is selected in any class
          let isSelected = false;
          let selectedClass = '';
          Object.keys(this.coordinatesData[imageData.filename] || {}).forEach(cls => {
            if (this.coordinatesData[imageData.filename][cls].some(coord => coord[0] === x / this.patchSize && coord[1] === y / this.patchSize)) {
              isSelected = true;
              selectedClass = cls;
            }
          });

          // Set the stroke style based on whether the cell is selected
          if (isSelected) {
            ctx.strokeStyle = this.getColorForClass(selectedClass);
            ctx.lineWidth = 8; // Thicker line for selected cells
          } else {
            ctx.strokeStyle = 'rgba(0, 0, 0, 0.5)';
            ctx.lineWidth = 1; // Normal line for non-selected cells
          }

          // Draw the grid line
          ctx.beginPath();
          ctx.rect(x, y, this.patchSize, this.patchSize);
          ctx.stroke();
        }
      }
    };
    image.src = 'data:image/png;base64,' + imageData.data;
  }

  onClassChange(event: any): void {
    this.selectedClass = event.target.value;
  }

  onSubmit(): void {
    const url = `http://localhost:8070/process_dataset`;
    this.http.post(url, { datasetName: this.datasetName, coordinatesData: this.coordinatesData }).subscribe(
      (response: any) => {
        this.datasetSubmited = true;
        console.log('Data submitted successfully', response);
        alert(response.message);
        this.router.navigate(['/list-datasets']);
      },
      (error) => {
        console.error('Error submitting data', error);
        alert('Error submitting coordinates data.');
      }
    );
  }

  setupCanvasClickHandler(): void {
    if (this.isCanvasClickHandlerSet) {
      return; // If the click handler is already set up, exit the method
    }
    const canvas: HTMLCanvasElement = <HTMLCanvasElement>document.getElementById('imageCanvas');
    if (!canvas) {
      console.error('Canvas element not found');
      return;
    }
    canvas.addEventListener('click', (event) => {
      const rect = canvas.getBoundingClientRect();
      const x = event.clientX - rect.left;
      const y = event.clientY - rect.top;
      const cellX = Math.floor(x / this.patchSize);
      const cellY = Math.floor(y / this.patchSize);
      console.log(`Clicked cell: (${cellX},${cellY})`);

      const imageName = this.getCurrentImage().filename;
      if (!this.coordinatesData[imageName]) {
        this.coordinatesData[imageName] = {};
        this.remainingClasses.forEach(cls => this.coordinatesData[imageName][cls] = []);
      }

      let cellRemoved = false;
      let cellFoundInOtherClass = false;

      // Check all classes except the selected class
      this.remainingClasses.forEach(cls => {
        const index = this.coordinatesData[imageName][cls].findIndex(coord => coord[0] === cellX && coord[1] === cellY);
        if (index !== -1) {
          if (cls === this.selectedClass) {
            // If cell is in the selected class, remove it (toggle functionality)
            this.coordinatesData[imageName][cls].splice(index, 1);
            cellRemoved = true;
          } else {
            // If cell is in a different class, remove it from that class
            this.coordinatesData[imageName][cls].splice(index, 1);
            cellFoundInOtherClass = true;
          }
        }
      });

      // If the cell was found in another class or wasn't removed (meaning it wasn't in the selected class), add it to the selected class
      if (!cellRemoved && this.selectedClass && this.selectedClass !== this.defaultClass) {
        this.coordinatesData[imageName][this.selectedClass].push([cellX, cellY]);
      }

      console.log(this.coordinatesData);

      // Redraw the grid with the updated selection
      this.drawImageWithGrid();
    });
    this.isCanvasClickHandlerSet = true; // Set the flag to true after setting up the click handler
  }
}
