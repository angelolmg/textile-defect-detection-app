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

@Component({
  selector: 'app-process-list',
  templateUrl: './list-datasets.component.html',
  styleUrls: ['./list-datasets.component.scss']
})
export class ListDatasetsComponent implements OnInit {
  processes: Process[] = [];

  constructor(private datasetsService: DatasetsService, private router: Router) { }

  ngOnInit(): void {
    this.fetchProcesses();
  }

  fetchProcesses(): void {
    this.datasetsService.getProcesses().subscribe(
      (data: Process[]) => this.processes = data,
      error => console.error('There was an error!', error)
    );
  }

  navigateToHome(): void {
    this.router.navigate(['/home']);
  }
}
