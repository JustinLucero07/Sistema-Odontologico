import { DatePipe } from '@angular/common';
import { Component, Input, OnInit, ViewChild, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import {
  Periodontogram,
  PeriodontogramSummary,
} from '../../core/models/periodontogram.models';
import { PeriodontogramService } from '../../core/services/periodontogram.service';
import { PeriodontogramChartComponent } from '../../shared/periodontogram/periodontogram-chart.component';

@Component({
  selector: 'app-periodontogram-tab',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    PeriodontogramChartComponent,
  ],
  templateUrl: './periodontogram-tab.component.html',
  styleUrl: './periodontogram-tab.component.scss',
})
export class PeriodontogramTabComponent implements OnInit {
  @Input({ required: true }) patientId!: string;
  @ViewChild(PeriodontogramChartComponent) chart?: PeriodontogramChartComponent;

  private readonly service = inject(PeriodontogramService);
  private readonly snackBar = inject(MatSnackBar);
  readonly auth = inject(AuthService);

  readonly current = signal<Periodontogram | null>(null);
  readonly versions = signal<PeriodontogramSummary[]>([]);
  readonly selectedVersionId = signal<string | null>(null);
  readonly loading = signal(true);
  readonly saving = signal(false);
  readonly editing = signal(false);
  notes = '';

  get canEdit(): boolean {
    return this.auth.hasPermission('periodontogram:write');
  }

  /** Viewing an old exam is read-only. Editing always starts a NEW snapshot,
   *  which is what keeps the history honest. */
  get isHistorical(): boolean {
    const latest = this.versions()[0];
    return !!latest && this.selectedVersionId() !== latest.id && this.selectedVersionId() !== null;
  }

  async ngOnInit(): Promise<void> {
    await this.reload();
  }

  private async reload(): Promise<void> {
    this.loading.set(true);
    try {
      const [latest, versions] = await Promise.all([
        firstValueFrom(this.service.getLatest(this.patientId)),
        firstValueFrom(this.service.getVersions(this.patientId)),
      ]);
      this.current.set(latest);
      this.versions.set(versions);
      this.selectedVersionId.set(latest?.id ?? null);
      this.editing.set(false);
      this.notes = '';
    } finally {
      this.loading.set(false);
    }
  }

  async selectVersion(id: string): Promise<void> {
    this.selectedVersionId.set(id);
    this.current.set(await firstValueFrom(this.service.getVersion(this.patientId, id)));
    this.editing.set(false);
  }

  startNew(): void {
    // The new exam opens pre-filled with the last one: a follow-up re-probes
    // the same mouth, and retyping 168 numbers is how sites get skipped.
    this.editing.set(true);
    this.notes = '';
  }

  startBlank(): void {
    this.current.set(null);
    this.editing.set(true);
    this.notes = '';
  }

  cancel(): void {
    this.editing.set(false);
    void this.reload();
  }

  async save(): Promise<void> {
    if (!this.chart || this.saving()) return;
    const payload = this.chart.buildPayload();
    if (payload.measurements.length === 0) {
      this.snackBar.open('Registre al menos una medición antes de guardar', 'Cerrar', {
        duration: 4000,
      });
      return;
    }

    this.saving.set(true);
    try {
      await firstValueFrom(
        this.service.create(this.patientId, { ...payload, notes: this.notes || null }),
      );
      this.snackBar.open('Periodontograma guardado', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch {
      this.snackBar.open('No se pudo guardar el periodontograma', 'Cerrar', { duration: 5000 });
    } finally {
      this.saving.set(false);
    }
  }
}
