import { Component, OnInit } from '@angular/core';

import { CellTemplate } from '../../../shared/enum/cell-template.enum';
import { CdTableColumn } from '../../../shared/models/cd-table-column';
import { RgwDaemonService } from '../services/rgw-daemon.service';

@Component({
  selector: 'cd-rgw-daemon-list',
  templateUrl: './rgw-daemon-list.component.html',
  styleUrls: ['./rgw-daemon-list.component.scss']
})
export class RgwDaemonListComponent implements OnInit {

  private columns: Array<CdTableColumn> = [];
  private daemons: Array<object> = [];

  detailsComponent = 'RgwDaemonDetailsComponent';

  constructor(private rgwDaemonService: RgwDaemonService) {
    this.columns = [
      {
        name: 'ID',
        prop: 'id',
        flexGrow: 2
      },
      {
        name: 'Hostname',
        prop: 'server_hostname',
        flexGrow: 2
      },
      {
        name: 'Version',
        prop: 'version',
        flexGrow: 1,
        cellTransformation: CellTemplate.cephShortVersion
      }
    ];
  }

  ngOnInit() {
    this.getDaemonList();
  }

  getDaemonList() {
    this.rgwDaemonService.list()
      .then((resp) => {
        this.daemons = resp;
      });
  }

  beforeShowDetails(selected: Array<object>) {
    return selected.length === 1;
  }
}
