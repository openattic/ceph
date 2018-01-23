import { NgModule } from '@angular/core';
import { CommonModule } from '@angular/common';
import { TableComponent } from './table/table.component';
import { NgxDatatableModule } from '@swimlane/ngx-datatable';
import { HttpClientModule, HttpClient } from '@angular/common/http';

@NgModule({
  imports: [CommonModule, NgxDatatableModule, HttpClientModule],
  declarations: [TableComponent],
  exports: [TableComponent, NgxDatatableModule]
})
export class ComponentsModule {}
