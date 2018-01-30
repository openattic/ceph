import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { ChartsModule } from 'ng2-charts';
import { SparklineComponent } from './sparkline/sparkline.component';

@NgModule({
  imports: [
    CommonModule,
    ChartsModule
  ],
  exports: [SparklineComponent],
  declarations: [SparklineComponent]
})
export class ComponentsModule { }
