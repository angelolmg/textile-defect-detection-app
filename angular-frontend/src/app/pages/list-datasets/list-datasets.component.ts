import { Component, OnInit } from '@angular/core';
import { DatasetsService } from './datasets.service';
import { Router } from '@angular/router';

interface Process {
  id: number;
  name: string;
  total_images: number;
  images_left: number;
  resize_x: number;
  resize_y: number;
  patch_size: number;
  class_names: string;
}

interface Dataset {
  id: number;
  dataset_name: string;
  total_patches: number;
  patch_size: number;
  class_names: string;
}

@Component({
  selector: 'app-list-datasets',
  templateUrl: './list-datasets.component.html',
  styleUrls: ['./list-datasets.component.scss'],
})
export class ListDatasetsComponent implements OnInit {
  processes: Process[] = [];
  datasets: Dataset[] = [];

  constructor(
    private datasetsService: DatasetsService,
    private router: Router
  ) {}

  ngOnInit(): void {
    this.fetchProcesses();
    this.fetchDatasets();
  }

  fetchProcesses(): void {
    this.datasetsService.getProcesses().subscribe(
      (data: Process[]) => (this.processes = data),
      (error) => console.error('There was an error fetching processes!', error)
    );
  }

  fetchDatasets(): void {
    this.datasetsService.getDatasets().subscribe(
      (data: Dataset[]) => (this.datasets = data),
      (error) => console.error('There was an error fetching datasets!', error)
    );
  }

  navigateToHome(datasetName: string): void {
    this.router.navigate(['/patching/' + datasetName]);
  }

  viewDataset(datasetName: string): void {
    console.log(`Viewing dataset: ${datasetName}`);
  }
}
