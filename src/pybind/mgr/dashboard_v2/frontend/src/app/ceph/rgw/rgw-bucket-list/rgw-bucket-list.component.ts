import { Component } from '@angular/core';

import { CdTableColumn } from '../../../shared/models/cd-table-column';
import { RgwBucketService } from '../services/rgw-bucket.service';

@Component({
  selector: 'cd-rgw-bucket-list',
  templateUrl: './rgw-bucket-list.component.html',
  styleUrls: ['./rgw-bucket-list.component.scss']
})
export class RgwBucketListComponent {

  columns: Array<CdTableColumn> = [];
  buckets: Array<object> = [];

  detailsComponent = 'RgwBucketDetailsComponent';

  constructor(private rgwBucketService: RgwBucketService) {
    this.columns = [
      {
        name: 'Name',
        prop: 'bucket',
        flexGrow: 1
      },
      {
        name: 'Owner',
        prop: 'owner',
        flexGrow: 1
      }
    ];
  }

  getBucketList() {
    this.rgwBucketService.list().then((resp) => {
      this.buckets = resp;
    });
  }

  beforeShowDetails(selected: Array<object>) {
    return selected.length === 1;
  }
}
