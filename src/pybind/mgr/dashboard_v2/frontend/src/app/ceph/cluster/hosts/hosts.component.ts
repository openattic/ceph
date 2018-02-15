import { Component, OnInit } from '@angular/core';

import { CellTemplate } from '../../../shared/enum/cell-template.enum';
import { CdTableColumn } from '../../../shared/models/cd-table-column';
import { HostService } from '../../../shared/services/host.service';
import { ServiceListPipe } from '../service-list.pipe';

@Component({
  selector: 'cd-hosts',
  templateUrl: './hosts.component.html',
  styleUrls: ['./hosts.component.scss']
})
export class HostsComponent implements OnInit {

  columns: Array<CdTableColumn> = [];
  hosts: Array<object> = [];

  constructor(private hostService: HostService,
              serviceListPipe: ServiceListPipe) {
    this.columns = [
      {
        name: 'Hostname',
        prop: 'hostname',
        flexGrow: 1
      },
      {
        name: 'Services',
        prop: 'services',
        flexGrow: 3,
        pipe: serviceListPipe
      },
      {
        name: 'Version',
        prop: 'ceph_version',
        flexGrow: 1,
        cellTransformation: CellTemplate.cephShortVersion
      }
    ];
  }

  ngOnInit() {
    this.hostService.list().then((resp) => {
      this.hosts = resp;
    });
  }

}
