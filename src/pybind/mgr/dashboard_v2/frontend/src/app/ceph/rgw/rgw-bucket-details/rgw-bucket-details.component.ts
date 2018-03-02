import { Component, Input, OnInit } from '@angular/core';

@Component({
  selector: 'cd-rgw-bucket-details',
  templateUrl: './rgw-bucket-details.component.html',
  styleUrls: ['./rgw-bucket-details.component.scss']
})
export class RgwBucketDetailsComponent implements OnInit {

  bucket: any;

  @Input() selected?: Array<any> = [];

  constructor() { }

  ngOnInit() {
    if (this.selected.length > 0) {
      this.bucket = this.selected[0];
    }
  }
}
