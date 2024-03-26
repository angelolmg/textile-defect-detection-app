import { HttpClient } from '@angular/common/http';
import { Component } from '@angular/core';
import 'devextreme/data/odata/store';

@Component({
  templateUrl: 'details.component.html',
  styleUrls: ['./details.component.scss'],
})
export class DetailsComponent {
  defectsData: any[] = [];

  constructor(private http: HttpClient) { }

  ngOnInit(): void {
    // Fetch defects data from the server
    this.http.get<any>('http://localhost:8000/get-defects/').subscribe(
      (response) => {
        // Assuming the response contains defects data in an array
        this.defectsData = response.defects;
      },
      (error) => {
        console.error('Error fetching defects data:', error);
      }
    );
  }
}
