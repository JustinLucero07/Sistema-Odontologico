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
import { Odontogram3dComponent } from '../../shared/odontogram/odontogram-3d.component';
import { OdontogramTimelineComponent } from '../../shared/odontogram/odontogram-timeline.component';
import { HallazgoDictado, OdontogramDictationComponent } from '../../shared/odontogram/odontogram-dictation.component';
import { TimelineFinding } from '../../core/models/odontogram.models';
import {
  SURFACE_LABELS,
  TOOTH_CONDITIONS,
  TOOTH_CONDITION_BY_CODE,
  ToothConditionDef,
} from '../../shared/odontogram/tooth-conditions';
import { BrandingService } from '../../core/branding/branding.service';

interface Finding {
  def: ToothConditionDef;
  teeth: string[];
  count: number;
}

@Component({
  selector: 'app-odontogram',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatButtonToggleModule, MatIconModule, MatTooltipModule, OdontogramChartComponent, Odontogram3dComponent, OdontogramTimelineComponent, OdontogramDictationComponent],
  templateUrl: './odontogram.component.html',
  styleUrl: './odontogram.component.scss',
})
export class OdontogramComponent implements OnChanges {
  @Input({ required: true }) patientId!: string;
  @Input() birthDate: string | null = null;
  private readonly marca = inject(BrandingService);

  private readonly odontogramService = inject(OdontogramService);
  private readonly snackBar = inject(MatSnackBar);
  private readonly auth = inject(AuthService);

  readonly canWrite = this.auth.hasPermission('odontogram:write');
  readonly denture = signal<'permanent' | 'temporary'>('permanent');
  /** 2D para registrar; 3D para ver la boca y enseñársela al paciente. */
  readonly modo = signal<'2d' | '3d'>('2d');
  /** Línea de tiempo abierta: recorre las versiones guardadas. */
  readonly linea = signal(false);
  readonly dictando = signal(false);
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

  readonly tool = signal<string | null>('caries');
  readonly pincel3d = computed(() => {
    const t = this.tool();
    const c = t ? TOOTH_CONDITION_BY_CODE[t] : null;
    return c ? { label: c.label, color: c.color === 'transparent' ? '#2b9a5b' : c.color } : null;
  });
  readonly selectedFdi = signal<string | null>(null);

  readonly picker = signal<{ fdi: string; surface: ToothSurface } | null>(null);
  readonly pickerOptions = signal<ToothConditionDef[]>([]);
  readonly surfaceLabels = SURFACE_LABELS;
  readonly surfaceTools = TOOTH_CONDITIONS.filter((c) => !c.wholeToothOnly && c.code !== 'sano');
  readonly toothTools = TOOTH_CONDITIONS.filter((c) => c.wholeToothOnly);
  readonly byCode = TOOTH_CONDITION_BY_CODE;

  readonly shown = computed(() => this.viewingVersion()?.conditions ?? this.draftConditions());

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

  readonly stats = computed(() => {
    const teethWith = (codes: string[]) =>
      new Set(this.shown().filter((c) => codes.includes(c.condition)).map((c) => c.fdi_number)).size;
    return {
      affected: this.affectedTeeth(),
      caries: teethWith(['caries']),
      toTreat: teethWith([
        'caries',
        'restauracion_defectuosa',
        'tratamiento_pendiente',
        'extraccion_indicada',
        'fractura',
      ]),
      absent: teethWith(['ausente', 'extraccion_realizada']),
    };
  });

  readonly selectedDetail = computed(() => {
    const fdi = this.selectedFdi();
    if (!fdi) return null;
    const items = this.shown()
      .filter((c) => c.fdi_number === fdi)
      .map((c) => ({
        condition: c,
        def: TOOTH_CONDITION_BY_CODE[c.condition] ?? { code: c.condition, label: c.condition, color: '#bdbdbd' },
      }));
    return { fdi, items };
  });

  readonly editable = computed(() => this.canWrite && !this.viewingVersion());

  private edadAnios(): number | null {
    if (!this.birthDate) return null;
    const n = new Date(this.birthDate);
    const hoy = new Date();
    return hoy.getFullYear() - n.getFullYear() - (hoy < new Date(hoy.getFullYear(), n.getMonth(), n.getDate()) ? 1 : 0);
  }

  ngOnChanges(): void {
    const edad = this.edadAnios();
    if (this.marca.specialty() === 'pediatria' && edad !== null && edad < 10) this.denture.set('temporary');
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
    const isTarget = (c: ToothCondition) => c.fdi_number === target.fdi && c.surface === target.surface;
    let rest: ToothCondition[];
    if (code === 'sano') {
      rest = current.filter((c) => c.fdi_number !== target.fdi || (target.surface !== 'whole' && c.surface !== target.surface));
    } else if (current.some((c) => isTarget(c) && c.condition === code)) {
      rest = current.filter((c) => !(isTarget(c) && c.condition === code));
    } else {
      rest = [...current, { fdi_number: target.fdi, surface: target.surface, condition: code }];
    }
    if (rest.length === current.length && rest.every((c, i) => c === current[i])) return;
    this.history.set([...this.history(), current]);
    this.draftConditions.set(rest);
  }

  aplicarDictado(hallazgos: HallazgoDictado[]): void {
    const current = this.draftConditions();
    let rest = [...current];
    for (const h of hallazgos) {
      const surface = h.surface as ToothSurface;
      if (h.condition === 'sano') {
        rest = rest.filter((c) => c.fdi_number !== h.fdi_number || (surface !== 'whole' && c.surface !== surface));
      } else if (!rest.some((c) => c.fdi_number === h.fdi_number && c.surface === surface && c.condition === h.condition)) {
        rest.push({ fdi_number: h.fdi_number, surface, condition: h.condition });
      }
    }
    if (rest.length === current.length && rest.every((c, i) => c === current[i])) return;
    this.history.set([...this.history(), current]);
    this.draftConditions.set(rest);
    if (hallazgos.length) this.selectedFdi.set(hallazgos[hallazgos.length - 1].fdi_number);
    this.snackBar.open(`${hallazgos.length} hallazgo(s) aplicados. Revise y guarde.`, undefined, { duration: 2500 });
  }

  removeCondition(target: ToothCondition): void {
    const current = this.draftConditions();
    const rest = current.filter(
      (c) =>
        !(c.fdi_number === target.fdi_number && c.surface === target.surface && c.condition === target.condition),
    );
    if (rest.length === current.length) return;
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

  /** La línea de tiempo eligió una versión (null = la vigente). */
  verEnLinea(v: { id: string; created_at: string; conditions: TimelineFinding[] } | null): void {
    this.viewingVersion.set(v ? ({ ...v, conditions: v.conditions } as unknown as Odontogram) : null);
  }

  print(): void {
    window.print();
  }
}
