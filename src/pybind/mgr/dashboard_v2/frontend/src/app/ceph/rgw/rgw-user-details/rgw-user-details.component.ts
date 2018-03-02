import { Component, Input, OnInit } from '@angular/core';

import * as _ from 'lodash';

import { RgwUserService } from '../services/rgw-user.service';

@Component({
  selector: 'cd-rgw-user-details',
  templateUrl: './rgw-user-details.component.html',
  styleUrls: ['./rgw-user-details.component.scss']
})
export class RgwUserDetailsComponent implements OnInit {

  user: any;

  @Input() selected?: Array<any> = [];

  constructor(private rgwUserService: RgwUserService) { }

  ngOnInit() {
    if (this.selected.length > 0) {
      this.user = this.selected[0];
      // Sort subusers and capabilities.
      this.user.subusers = _.sortBy(this.user.subusers, 'id');
      this.user.caps = _.sortBy(this.user.caps, 'type');
      // Load the user/bucket quota of the selected user.
      this.rgwUserService.getQuota(this.user.user_id)
        .then((resp) => {
          _.extend(this.user, resp);
        });
    }
  }
}
