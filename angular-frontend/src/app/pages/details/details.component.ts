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
    this.http.get<any>('http://localhost:8070/get-defects').subscribe(
      (response) => {
        // Assuming the response contains defects data in an array
        this.defectsData = response.defects;
      },
      (error) => {
        console.error('Error fetching defects data:', error);
      }
    );
  }

  sortedBy: string = ''; // Property to track the currently sorted column
  reverseSort: boolean = false; // Property to track the sorting order

  sortBy(key: string) {
    if (this.sortedBy === key) {
      this.reverseSort = !this.reverseSort;
    } else {
      this.sortedBy = key;
      this.reverseSort = false;
    }

    this.defectsData.sort((a, b) => {
      if (a[key] < b[key]) return this.reverseSort ? 1 : -1;
      if (a[key] > b[key]) return this.reverseSort ? -1 : 1;
      return 0;
    });
  }
}
