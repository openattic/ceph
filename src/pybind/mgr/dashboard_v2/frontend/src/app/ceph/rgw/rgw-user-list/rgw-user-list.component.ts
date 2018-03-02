import { Component } from '@angular/core';

import { CellTemplate } from '../../../shared/enum/cell-template.enum';
import { CdTableColumn } from '../../../shared/models/cd-table-column';
import { RgwUserService } from '../services/rgw-user.service';

@Component({
  selector: 'cd-rgw-user-list',
  templateUrl: './rgw-user-list.component.html',
  styleUrls: ['./rgw-user-list.component.scss']
})
export class RgwUserListComponent {

  columns: Array<CdTableColumn> = [];
  users: Array<object> = [];

  detailsComponent = 'RgwUserDetailsComponent';

  constructor(private rgwUserService: RgwUserService) {
    this.columns = [
      {
        name: 'Username',
        prop: 'user_id',
        flexGrow: 1
      },
      {
        name: 'Full name',
        prop: 'display_name',
        flexGrow: 1
      },
      {
        name: 'Email address',
        prop: 'email',
        flexGrow: 1
      },
      {
        name: 'Suspended',
        prop: 'suspended',
        flexGrow: 1,
        cellTransformation: CellTemplate.checkIcon
      },
      {
        name: 'Max. buckets',
        prop: 'max_buckets',
        flexGrow: 1
      }
    ];
  }

  getUserList() {
    this.rgwUserService.list().then((resp) => {
      this.users = resp;
    });
  }

  beforeShowDetails(selected: Array<object>) {
    return selected.length === 1;
  }
}
