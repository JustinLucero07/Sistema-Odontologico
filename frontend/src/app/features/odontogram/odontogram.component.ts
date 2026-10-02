import { DatePipe } from '@angular/common';
import { Component, HostListener, Input, OnChanges, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { Odontogram, OdontogramSummary, ToothCondition, ToothSurface } from '../../core/models/odontogram.models';
import { OdontogramService } from '../../core/services/odontogram.service';
import { OdontogramChartComponent } from '../../shared/odontogram/odontogram-chart.component';
import {
  SURFACE_LABELS,
  TOOTH_CONDITIONS,
  TOOTH_CONDITION_BY_CODE,
  ToothConditionDef,
} from '../../shared/odontogram/tooth-conditions';

interface Finding {
  def: ToothConditionDef;
  teeth: string[];
  count: number;
}

@Component({
  selector: 'app-odontogram',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatButtonToggleModule, MatIconModule, MatTooltipModule, OdontogramChartComponent],
  templateUrl: './odontogram.component.html',
  styleUrl: './odontogram.component.scss',
})
export class OdontogramComponent implements OnChanges {
  @Input({ required: true }) patientId!: string;

  private readonly odontogramService = inject(OdontogramService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly auth = inject(AuthService);

  readonly canWrite = this.auth.hasPermission('odontogram:write');
  readonly denture = signal<'permanent' | 'temporary'>('permanent');
  readonly latest = signal<Odontogram | null>(null);
  readonly draftConditions = signal<ToothCondition[]>([]);
  readonly saving = signal(false);

  /** Estados anteriores del borrador, para deshacer paso a paso. */
  private readonly history = signal<ToothCondition[][]>([]);
  readonly canUndo = computed(() => this.history().length > 0);
  readonly dirty = computed(() => this.history().length > 0);

  readonly versions = signal<OdontogramSummary[]>([]);
  readonly showVersions = signal(false);
  readonly viewingVersion = signal<Odontogram | null>(null);

  /** Pincel: la condición elegida se aplica a cada superficie que se toca.
   *  null = modo "elegir al tocar", que pregunta en cada pieza. */
  readonly tool = signal<string | null>('caries');
  readonly selectedFdi = signal<string | null>(null);

  readonly picker = signal<{ fdi: string; surface: ToothSurface } | null>(null);
  readonly pickerOptions = signal<ToothConditionDef[]>([]);
  readonly surfaceLabels = SURFACE_LABELS;
  readonly surfaceTools = TOOTH_CONDITIONS.filter((c) => !c.wholeToothOnly && c.code !== 'sano');
  readonly toothTools = TOOTH_CONDITIONS.filter((c) => c.wholeToothOnly);
  readonly byCode = TOOTH_CONDITION_BY_CODE;

  readonly shown = computed(() => this.viewingVersion()?.conditions ?? this.draftConditions());

  /** Resumen de hallazgos: qué hay y en qué piezas, para leer la boca de un vistazo. */
  readonly findings = computed<Finding[]>(() => {
    const groups = new Map<string, Set<string>>();
    const counts = new Map<string, number>();
    for (const c of this.shown()) {
      (groups.get(c.condition) ?? groups.set(c.condition, new Set()).get(c.condition)!).add(c.fdi_number);
      counts.set(c.condition, (counts.get(c.condition) ?? 0) + 1);
    }
    return [...groups.entries()]
      .map(([code, teeth]) => ({
        def: TOOTH_CONDITION_BY_CODE[code] ?? { code, label: code, color: '#bdbdbd' },
        teeth: [...teeth].sort(),
        count: counts.get(code) ?? 0,
      }))
      .sort((a, b) => b.teeth.length - a.teeth.length);
  });

  readonly affectedTeeth = computed(() => new Set(this.shown().map((c) => c.fdi_number)).size);

  ngOnChanges(): void {
    if (this.patientId) void this.load();
  }

  private async load(): Promise<void> {
    const latest = await firstValueFrom(this.odontogramService.getLatest(this.patientId));
    this.latest.set(latest);
    this.draftConditions.set(latest?.conditions.map((c) => ({ ...c })) ?? []);
    this.history.set([]);
    this.viewingVersion.set(null);
    this.showVersions.set(false);
  }

  selectTool(code: string | null): void {
    this.tool.set(this.tool() === code ? null : code);
  }

  onSurfaceClicked(event: { fdi: string; surface: ToothSurface }): void {
    this.selectedFdi.set(event.fdi);
    const tool = this.tool();
    if (tool === null) {
      this.picker.set(event);
      this.pickerOptions.set(
        event.surface === 'whole' ? TOOTH_CONDITIONS : TOOTH_CONDITIONS.filter((c) => !c.wholeToothOnly),
      );
      return;
    }
    // Una condición de pieza completa se aplica a toda la pieza aunque se toque una cara.
    const surface = TOOTH_CONDITION_BY_CODE[tool]?.wholeToothOnly ? 'whole' : event.surface;
    this.apply({ fdi: event.fdi, surface }, tool);
  }

  onToothClicked(event: { fdi: string }): void {
    this.onSurfaceClicked({ fdi: event.fdi, surface: 'whole' });
  }

  closePicker(): void {
    this.picker.set(null);
  }

  chooseCondition(conditionCode: string): void {
    const target = this.picker();
    if (target) this.apply(target, conditionCode);
    this.picker.set(null);
  }

  private apply(target: { fdi: string; surface: ToothSurface }, code: string): void {
    const current = this.draftConditions();
    const same = current.some(
      (c) => c.fdi_number === target.fdi && c.surface === target.surface && c.condition === code,
    );
    const rest = current.filter((c) => {
      if (c.fdi_number !== target.fdi) return true;
      if (target.surface === 'whole') return false; // la pieza completa reemplaza todo lo de esa pieza
      return c.surface !== 'whole' && c.surface !== target.surface;
    });
    // Tocar otra vez con el mismo pincel lo quita: corregir un toque de más es un toque.
    if (code !== 'sano' && !same) {
      rest.push({ fdi_number: target.fdi, surface: target.surface, condition: code });
    }
    if (JSON.stringify(rest) === JSON.stringify(current)) return;
    this.history.set([...this.history(), current]);
    this.draftConditions.set(rest);
  }

  @HostListener('document:keydown', ['$event'])
  onKey(event: KeyboardEvent): void {
    if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'z' && this.canUndo() && !this.viewingVersion()) {
      event.preventDefault();
      this.undo();
    }
    if (event.key === 'Escape') this.picker.set(null);
  }

  undo(): void {
    const stack = this.history();
    if (stack.length === 0) return;
    this.draftConditions.set(stack[stack.length - 1]);
    this.history.set(stack.slice(0, -1));
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
      this.history.set([]);
      this.snackBar.open('Odontograma guardado — nueva versión creada', 'Cerrar', { duration: 3000 });
      if (this.showVersions()) await this.loadVersions();
    } finally {
      this.saving.set(false);
    }
  }

  discardChanges(): void {
    this.draftConditions.set(this.latest()?.conditions.map((c) => ({ ...c })) ?? []);
    this.history.set([]);
  }

  async loadVersions(): Promise<void> {
    if (this.showVersions()) {
      this.showVersions.set(false);
      return;
    }
    this.versions.set(await firstValueFrom(this.odontogramService.listVersions(this.patientId)));
    this.showVersions.set(true);
  }

  async viewVersion(odontogramId: string): Promise<void> {
    this.viewingVersion.set(await firstValueFrom(this.odontogramService.getVersion(this.patientId, odontogramId)));
  }

  backToCurrent(): void {
    this.viewingVersion.set(null);
  }

  print(): void {
    window.print();
  }
}
