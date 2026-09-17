import { DatePipe } from '@angular/common';
import { Component, Input, OnChanges, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { HasPermissionDirective } from '../../core/auth/has-permission.directive';
import { Odontogram, OdontogramSummary, ToothCondition, ToothSurface } from '../../core/models/odontogram.models';
import { OdontogramService } from '../../core/services/odontogram.service';
import { OdontogramChartComponent } from '../../shared/odontogram/odontogram-chart.component';
import {
  SURFACE_LABELS,
  TOOTH_CONDITIONS,
  TOOTH_CONDITION_BY_CODE,
  ToothConditionDef,
} from '../../shared/odontogram/tooth-conditions';

@Component({
  selector: 'app-odontogram',
  standalone: true,
  imports: [
    DatePipe,
    MatButtonModule,
    MatButtonToggleModule,
    MatIconModule,
    HasPermissionDirective,
    OdontogramChartComponent,
  ],
  templateUrl: './odontogram.component.html',
  styleUrl: './odontogram.component.scss',
})
export class OdontogramComponent implements OnChanges {
  @Input({ required: true }) patientId!: string;

  private readonly odontogramService = inject(OdontogramService);
  private readonly snackBar = inject(MatSnackBar);

  readonly denture = signal<'permanent' | 'temporary'>('permanent');
  readonly latest = signal<Odontogram | null>(null);
  readonly draftConditions = signal<ToothCondition[]>([]);
  readonly dirty = signal(false);
  readonly saving = signal(false);

  readonly versions = signal<OdontogramSummary[]>([]);
  readonly showVersions = signal(false);
  readonly viewingVersion = signal<Odontogram | null>(null);

  readonly picker = signal<{ fdi: string; surface: ToothSurface } | null>(null);
  readonly pickerOptions = signal<ToothConditionDef[]>([]);
  readonly surfaceLabels = SURFACE_LABELS;
  readonly legendItems = ['sano', 'caries', 'restauracion', 'corona', 'ausente', 'endodoncia', 'sellante', 'implante'].map(
    (code) => TOOTH_CONDITION_BY_CODE[code],
  );

  ngOnChanges(): void {
    if (this.patientId) void this.load();
  }

  private async load(): Promise<void> {
    const latest = await firstValueFrom(this.odontogramService.getLatest(this.patientId));
    this.latest.set(latest);
    this.draftConditions.set(latest?.conditions.map((c) => ({ ...c })) ?? []);
    this.dirty.set(false);
    this.viewingVersion.set(null);
    this.showVersions.set(false);
  }

  onSurfaceClicked(event: { fdi: string; surface: ToothSurface }): void {
    this.picker.set(event);
    this.pickerOptions.set(
      event.surface === 'whole' ? TOOTH_CONDITIONS : TOOTH_CONDITIONS.filter((c) => !c.wholeToothOnly),
    );
  }

  onToothClicked(event: { fdi: string }): void {
    this.onSurfaceClicked({ fdi: event.fdi, surface: 'whole' });
  }

  closePicker(): void {
    this.picker.set(null);
  }

  chooseCondition(conditionCode: string): void {
    const target = this.picker();
    if (!target) return;

    const conditions = this.draftConditions().filter((c) => {
      if (c.fdi_number !== target.fdi) return true;
      if (target.surface === 'whole') return false; // whole-tooth replaces everything on this tooth
      return c.surface !== 'whole' && c.surface !== target.surface;
    });

    if (conditionCode !== 'sano') {
      conditions.push({ fdi_number: target.fdi, surface: target.surface, condition: conditionCode });
    }

    this.draftConditions.set(conditions);
    this.dirty.set(true);
    this.picker.set(null);
  }

  async save(): Promise<void> {
    if (this.saving()) return;
    this.saving.set(true);
    try {
      const created = await firstValueFrom(
        this.odontogramService.createSnapshot(this.patientId, { conditions: this.draftConditions() }),
      );
      this.latest.set(created);
      this.draftConditions.set(created.conditions.map((c) => ({ ...c })));
      this.dirty.set(false);
      this.snackBar.open('Odontograma guardado — nueva versión creada', 'Cerrar', { duration: 3000 });
      if (this.showVersions()) await this.loadVersions();
    } finally {
      this.saving.set(false);
    }
  }

  discardChanges(): void {
    this.draftConditions.set(this.latest()?.conditions.map((c) => ({ ...c })) ?? []);
    this.dirty.set(false);
  }

  async loadVersions(): Promise<void> {
    const versions = await firstValueFrom(this.odontogramService.listVersions(this.patientId));
    this.versions.set(versions);
    this.showVersions.set(true);
  }

  async viewVersion(odontogramId: string): Promise<void> {
    const version = await firstValueFrom(this.odontogramService.getVersion(this.patientId, odontogramId));
    this.viewingVersion.set(version);
  }

  backToCurrent(): void {
    this.viewingVersion.set(null);
  }

  print(): void {
    window.print();
  }
}
