import { HttpClientModule } from '@angular/common/http';
import { HttpClientTestingModule } from '@angular/common/http/testing';
import { async, ComponentFixture, TestBed } from '@angular/core/testing';

import { TabsModule } from 'ngx-bootstrap/tabs';

import { SharedModule } from '../../../shared/shared.module';
import { RgwUserService } from '../services/rgw-user.service';
import { RgwUserDetailsComponent } from './rgw-user-details.component';

describe('RgwUserDetailsComponent', () => {
  let component: RgwUserDetailsComponent;
  let fixture: ComponentFixture<RgwUserDetailsComponent>;

  beforeEach(async(() => {
    TestBed.configureTestingModule({
      declarations: [ RgwUserDetailsComponent ],
      imports: [
        HttpClientTestingModule,
        HttpClientModule,
        SharedModule,
        TabsModule.forRoot()
      ],
      providers: [ RgwUserService ]
    })
    .compileComponents();
  }));

  beforeEach(() => {
    fixture = TestBed.createComponent(RgwUserDetailsComponent);
    component = fixture.componentInstance;
    fixture.detectChanges();
  });

  it('should create', () => {
    expect(component).toBeTruthy();
  });
});
