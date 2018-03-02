import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { TabsModule } from 'ngx-bootstrap/tabs';

import { SharedModule } from '../../../shared/shared.module';
import { RgwBucketDetailsComponent } from './rgw-bucket-details.component';

describe('RgwBucketDetailsComponent', () => {
  let component: RgwBucketDetailsComponent;
  let fixture: ComponentFixture<RgwBucketDetailsComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      imports: [
        SharedModule,
        TabsModule.forRoot()
      ],
      declarations: [ RgwBucketDetailsComponent ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(RgwBucketDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
