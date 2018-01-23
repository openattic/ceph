import { Component, OnInit, ViewChild } from '@angular/core';
import { DatatableComponent } from '@swimlane/ngx-datatable';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Input } from '@angular/core';
import { TableData } from '../../models/table-data';
import { FilterConfig } from '../../models/filter-config';

@Component({
  selector: 'oa-table',
  templateUrl: './table.component.html',
  styleUrls: ['./table.component.scss']
})
export class TableComponent implements OnInit {
  @ViewChild(DatatableComponent) table: DatatableComponent;

  @Input() filter?: boolean;
  @Input() header? = true;

  @Input() process?: any;
  @Input() fetchURL?: string;

  @Input() rows?: any;
  temp = [];

  limits = [2, 10, 25, 50, 100];

  filterConfig: FilterConfig;

  constructor(private http: HttpClient) {}

  ngOnInit() {
    this.temp = [...this.rows];

    if (this.fetchURL) {
      this.fetch();
    }
  }

  fetch() {
    // Initialize Params Object
    let params = new HttpParams();

    // Begin assigning parameters
    params = params.append('page', (this.filterConfig.page + 1).toString());
    params = params.append('pageSize', this.filterConfig.entries.toString());
    params = params.append('search', this.filterConfig.search);
    params = params.append(
      'ordering',
      (this.filterConfig.sortorder === 'ASC' ? '' : '-') +
        this.filterConfig.sortfield
    );

    this.http
      .get(this.fetchURL, { params: params })
      .subscribe((data: TableData) => {
        if (this.process) {
          this.rows = [...this.process(data.results)];
        } else {
          this.rows = [...data.results];
        }
        this.temp = [...this.rows];
      });
  }

  updateFilter(event) {
    const val = event.target.value.toLowerCase();

    // filter our data
    const temp = this.temp.filter(function(d) {
      return d.name.toLowerCase().indexOf(val) !== -1 || !val;
    });

    // update the rows
    this.rows = temp;
    // Whenever the filter changes, always go back to the first page
    this.table.offset = 0;
  }
}
