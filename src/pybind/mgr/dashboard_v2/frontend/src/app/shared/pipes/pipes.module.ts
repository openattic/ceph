import { CommonModule } from '@angular/common';
import { NgModule } from '@angular/core';

import { CephShortVersionPipe } from './ceph-short-version.pipe';
import { DimlessBinaryPipe } from './dimless-binary.pipe';
import { DimlessPipe } from './dimless.pipe';
import { EllipsisPipe } from './ellipsis.pipe';
import { HealthColorPipe } from './health-color.pipe';

@NgModule({
  imports: [CommonModule],
  declarations: [
    DimlessBinaryPipe,
    HealthColorPipe,
    DimlessPipe,
    CephShortVersionPipe,
    EllipsisPipe
  ],
  exports: [
    DimlessBinaryPipe,
    HealthColorPipe,
    DimlessPipe,
    CephShortVersionPipe,
    EllipsisPipe
  ],
  providers: [
    CephShortVersionPipe,
    DimlessBinaryPipe,
    DimlessPipe
  ]
})
export class PipesModule {}