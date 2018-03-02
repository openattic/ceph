import { HttpClientModule } from '@angular/common/http';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { SharedModule } from '../../../shared/shared.module';
import { RgwUserService } from '../services/rgw-user.service';
import { RgwUserListComponent } from './rgw-user-list.component';

describe('RgwUserListComponent', () => {
  let component: RgwUserListComponent;
  let fixture: ComponentFixture<RgwUserListComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ RgwUserListComponent ],
      imports: [
        HttpClientTestingModule,
        HttpClientModule,
        SharedModule
      ],
      providers: [ RgwUserService ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(RgwUserListComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
