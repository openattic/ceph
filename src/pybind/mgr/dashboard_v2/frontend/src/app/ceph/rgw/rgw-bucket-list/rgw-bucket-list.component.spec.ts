import { HttpClientModule } from '@angular/common/http';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { DataTableModule } from '../../../shared/datatable/datatable.module';
import { RgwBucketService } from '../services/rgw-bucket.service';
import { RgwBucketListComponent } from './rgw-bucket-list.component';

describe('RgwBucketListComponent', () => {
  let component: RgwBucketListComponent;
  let fixture: ComponentFixture<RgwBucketListComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ RgwBucketListComponent ],
      imports: [
        HttpClientTestingModule,
        HttpClientModule,
        DataTableModule
      ],
      providers: [ RgwBucketService ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(RgwBucketListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
