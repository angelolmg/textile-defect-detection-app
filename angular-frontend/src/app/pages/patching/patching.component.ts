import { AfterViewInit, Component, OnInit } from '@angular/core';
import { ActivatedRoute, Router } from '@angular/router';
import { DatasetsService } from '../list-datasets/datasets.service';

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


  constructor(
    private route: ActivatedRoute,
    private datasetsService: DatasetsService,
    private router: Router
  ) { }

  ngOnInit(): void {
    this.datasetName = this.route.snapshot.paramMap.get('datasetName') || '';
    this.fetchImages();
    this.fetchProcess();
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
      ctx.strokeStyle = 'rgba(0, 0, 0, 0.5)';
      for (let x = 0; x < this.resizeX; x += this.patchSize) {
        ctx.beginPath();
        ctx.moveTo(x, 0);
        ctx.lineTo(x, this.resizeY);
        ctx.stroke();
      }
      for (let y = 0; y < this.resizeY; y += this.patchSize) {
        ctx.beginPath();
        ctx.moveTo(0, y);
        ctx.lineTo(this.resizeX, y);
        ctx.stroke();
      }
    };
    image.src = 'data:image/png;base64,' + imageData.data;
  }

  onClassChange(event: any): void {
    this.selectedClass = event.target.value;
  }

  onSubmit(): void {
    console.log(`Marked ${this.getCurrentImage().filename} as ${this.selectedClass}`);
    // Add your submit logic here
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
    });
    this.isCanvasClickHandlerSet = true; // Set the flag to true after setting up the click handler
  }

}
