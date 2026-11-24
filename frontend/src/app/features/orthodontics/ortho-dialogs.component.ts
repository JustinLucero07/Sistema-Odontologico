import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatAutocompleteModule } from '@angular/material/autocomplete';
import { firstValueFrom } from 'rxjs';

import { Professional } from '../../core/models/clinic.models';
import { PaymentMethodCode, PaymentMethodOption, formatMoney } from '../../core/models/finance.models';
import {
  OrthoCaseDetail,
  OrthoCaseFields,
  OrthoControl,
  OrthoOptions,
  OrthoStatus,
  OrthoTad,
} from '../../core/models/orthodontics.models';
import { PatientListItem } from '../../core/models/patient.models';
import { ClinicService } from '../../core/services/clinic.service';
import { FinanceService } from '../../core/services/finance.service';
import { OrthodonticsService } from '../../core/services/orthodontics.service';
import { PatientPickerComponent } from '../../shared/patient-picker/patient-picker.component';

export function hoyIso(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

export function mensajeError(e: unknown, porDefecto = 'No se pudo guardar. Intente de nuevo.'): string {
  if (e instanceof HttpErrorResponse) {
    const d = e.error?.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d) && d[0]?.msg) return String(d[0].msg).replace(/^Value error, /, '');
  }
  return porDefecto;
}

const DIALOG_STYLES = `
  .dialog-grid { margin-top: 4px; }
  .paciente { display: flex; align-items: center; gap: 10px; padding: 10px 12px; margin-bottom: 8px;
    border-radius: var(--radius-md); background: var(--color-primary-soft); color: var(--color-primary-dark);
    strong { font-size: .92rem; } button { margin-left: auto; } }
  .switch { display: flex; align-items: center; justify-content: space-between; gap: 12px; padding: 4px 2px;
    span { display: grid; font-size: .86rem; small { color: var(--color-ink-faint); font-size: .74rem; } } }
  .error { color: var(--color-danger); font-size: .84rem; margin: 6px 0 0; }
  .resumen { margin: 4px 0 0; padding: 10px 12px; border-radius: var(--radius-md); background: var(--color-surface-muted);
    font-size: .84rem; color: var(--color-ink-soft); }
`;

export interface OrthoCaseDialogData {
  patient?: { id: string; name: string } | null;
  caso?: OrthoCaseDetail | null;
}

@Component({
  selector: 'app-ortho-case-dialog',
  standalone: true,
  imports: [
    FormsModule,
    MatAutocompleteModule,
    MatButtonModule,
    MatCheckboxModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    PatientPickerComponent,
  ],
  template: `
    <h2 mat-dialog-title>{{ data.caso ? 'Editar ficha ' + data.caso.code : 'Nueva ficha de ortodoncia' }}</h2>
    <mat-dialog-content>
      @if (!data.caso) {
        @if (paciente(); as p) {
          <div class="paciente">
            <mat-icon>person</mat-icon><strong>{{ p.name }}</strong>
            @if (!data.patient) {
              <button mat-button type="button" (click)="paciente.set(null)">Cambiar</button>
            }
          </div>
        } @else {
          <app-patient-picker hint="Busca al paciente por nombre o cédula." (selected)="elegir($event)" />
        }
      }

      <div class="dialog-grid">
        @if (data.caso) {
          <mat-form-field appearance="outline">
            <mat-label>Estado de ortodoncia</mat-label>
            <mat-select [(ngModel)]="f.status">
              @for (s of opciones()?.statuses ?? []; track s.code) { <mat-option [value]="s.code">{{ s.label }}</mat-option> }
            </mat-select>
          </mat-form-field>
        }
        <mat-form-field appearance="outline" [class.full]="!data.caso">
          <mat-label>Etapa del tratamiento</mat-label>
          <input matInput [(ngModel)]="f.stage" [matAutocomplete]="etapas" maxlength="120" />
          <mat-autocomplete #etapas="matAutocomplete">
            @for (e of opciones()?.stages ?? []; track e) { <mat-option [value]="e">{{ e }}</mat-option> }
          </mat-autocomplete>
          <mat-hint>Ej.: Alineación y nivelación</mat-hint>
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Aparatología</mat-label>
          <input matInput [(ngModel)]="f.appliance" [matAutocomplete]="aparatos" maxlength="60" />
          <mat-autocomplete #aparatos="matAutocomplete">
            @for (a of opciones()?.appliances ?? []; track a) { <mat-option [value]="a">{{ a }}</mat-option> }
          </mat-autocomplete>
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>¿Tiene TAD actualmente?</mat-label>
          <mat-select [(ngModel)]="f.has_tad">
            @for (t of opciones()?.tad ?? []; track t.code) { <mat-option [value]="t.code">{{ t.label }}</mat-option> }
          </mat-select>
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Ortodoncista</mat-label>
          <mat-select [(ngModel)]="f.professional_id">
            <mat-option [value]="null">Sin asignar</mat-option>
            @for (p of profesionales(); track p.id) { <mat-option [value]="p.id">{{ p.first_name }} {{ p.last_name }}</mat-option> }
          </mat-select>
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Fecha de inicio</mat-label>
          <input matInput type="date" [(ngModel)]="f.started_on" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Duración estimada (meses)</mat-label>
          <input matInput type="number" min="1" max="120" [(ngModel)]="f.estimated_months" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Valor del tratamiento</mat-label>
          <span matTextPrefix>$&nbsp;</span>
          <input matInput inputmode="decimal" [(ngModel)]="f.agreed_total" />
          <mat-hint>Se carga a la cuenta del paciente</mat-hint>
        </mat-form-field>

        <div class="full switch">
          <span>Atención especial<small>Paciente que requiere un cuidado o trato particular</small></span>
          <mat-slide-toggle [(ngModel)]="f.special_attention" />
        </div>
        @if (f.special_attention) {
          <mat-form-field appearance="outline" class="full">
            <mat-label>¿Por qué?</mat-label>
            <input matInput [(ngModel)]="f.special_attention_note" maxlength="300" />
          </mat-form-field>
        }
        <div class="full switch">
          <span>Consultar / requiere revisión<small>Aparece marcado en la lista para revisarlo</small></span>
          <mat-slide-toggle [(ngModel)]="f.needs_review" />
        </div>
        <mat-form-field appearance="outline" class="full">
          <mat-label>Notas</mat-label>
          <textarea matInput rows="2" [(ngModel)]="f.notes"></textarea>
        </mat-form-field>
      </div>
      @if (error()) { <p class="error">{{ error() }}</p> }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button type="button" mat-dialog-close>Cancelar</button>
      <button mat-flat-button type="button" (click)="guardar()" [disabled]="guardando() || !paciente()">
        {{ data.caso ? 'Guardar cambios' : 'Crear ficha' }}
      </button>
    </mat-dialog-actions>
  `,
  styles: [DIALOG_STYLES],
})
export class OrthoCaseDialogComponent implements OnInit {
  readonly data = inject<OrthoCaseDialogData>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<OrthoCaseDialogComponent, OrthoCaseDetail>);
  private readonly api = inject(OrthodonticsService);
  private readonly clinic = inject(ClinicService);

  readonly opciones = signal<OrthoOptions | null>(null);
  readonly profesionales = signal<Professional[]>([]);
  readonly paciente = signal<{ id: string; name: string } | null>(
    this.data.patient ??
      (this.data.caso
        ? { id: this.data.caso.patient.id, name: `${this.data.caso.patient.first_name} ${this.data.caso.patient.last_name}` }
        : null),
  );
  readonly guardando = signal(false);
  readonly error = signal<string | null>(null);

  f: {
    status: OrthoStatus;
    stage: string;
    appliance: string;
    has_tad: OrthoTad;
    professional_id: string | null;
    started_on: string;
    estimated_months: number | null;
    agreed_total: string;
    special_attention: boolean;
    special_attention_note: string;
    needs_review: boolean;
    notes: string;
  } = {
    status: this.data.caso?.status ?? 'activo',
    stage: this.data.caso?.stage ?? '',
    appliance: this.data.caso?.appliance ?? '',
    has_tad: this.data.caso?.has_tad ?? 'por_confirmar',
    professional_id: this.data.caso?.professional_id ?? null,
    started_on: this.data.caso?.started_on ?? (this.data.caso ? '' : hoyIso()),
    estimated_months: this.data.caso?.estimated_months ?? null,
    agreed_total: this.data.caso ? String(Number(this.data.caso.agreed_total)) : '',
    special_attention: this.data.caso?.special_attention ?? false,
    special_attention_note: this.data.caso?.special_attention_note ?? '',
    needs_review: this.data.caso?.needs_review ?? false,
    notes: this.data.caso?.notes ?? '',
  };

  async ngOnInit(): Promise<void> {
    this.api.options().subscribe((o) => this.opciones.set(o));
    try {
      const ps = await firstValueFrom(this.clinic.listProfessionals());
      this.profesionales.set(ps.filter((p) => p.is_active || p.id === this.f.professional_id));
    } catch {
      this.profesionales.set([]);
    }
  }

  elegir(p: PatientListItem): void {
    this.paciente.set({ id: p.id, name: `${p.first_name} ${p.last_name}` });
  }

  async guardar(): Promise<void> {
    const p = this.paciente();
    if (!p) return;
    const total = (this.f.agreed_total || '0').replace(',', '.');
    if (isNaN(Number(total)) || Number(total) < 0) {
      this.error.set('El valor del tratamiento no es válido.');
      return;
    }
    const body: OrthoCaseFields = {
      stage: this.f.stage.trim() || null,
      appliance: this.f.appliance.trim() || null,
      has_tad: this.f.has_tad,
      professional_id: this.f.professional_id,
      started_on: this.f.started_on || null,
      estimated_months: this.f.estimated_months || null,
      agreed_total: total,
      special_attention: this.f.special_attention,
      special_attention_note: this.f.special_attention ? this.f.special_attention_note.trim() || null : null,
      needs_review: this.f.needs_review,
      notes: this.f.notes.trim() || null,
    };
    if (this.data.caso) body.status = this.f.status;
    this.guardando.set(true);
    this.error.set(null);
    try {
      const out = this.data.caso
        ? await firstValueFrom(this.api.update(this.data.caso.id, body))
        : await firstValueFrom(this.api.create(p.id, body));
      this.ref.close(out);
    } catch (e) {
      this.error.set(mensajeError(e));
    } finally {
      this.guardando.set(false);
    }
  }
}

export function openOrthoCaseDialog(dialog: MatDialog, data: OrthoCaseDialogData): Promise<OrthoCaseDetail | undefined> {
  const ref = dialog.open(OrthoCaseDialogComponent, { data, width: '640px', maxWidth: '96vw', panelClass: 'app-dialog' });
  return firstValueFrom(ref.afterClosed());
}

@Component({
  selector: 'app-ortho-generate-dialog',
  standalone: true,
  imports: [FormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule],
  template: `
    <h2 mat-dialog-title>Agregar cuotas</h2>
    <mat-dialog-content>
      <div class="dialog-grid">
        <mat-form-field appearance="outline">
          <mat-label>Número de cuotas</mat-label>
          <input matInput type="number" min="1" max="120" [(ngModel)]="cuotas" (ngModelChange)="tocado || sugerir()" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Valor de cada cuota</mat-label>
          <span matTextPrefix>$&nbsp;</span>
          <input matInput inputmode="decimal" [(ngModel)]="valor" (ngModelChange)="tocado = true" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Primera fecha</mat-label>
          <input matInput type="date" [(ngModel)]="desde" />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Frecuencia</mat-label>
          <mat-select [(ngModel)]="cada">
            <mat-option [value]="0">Mensual (mismo día)</mat-option>
            <mat-option [value]="14">Cada 2 semanas</mat-option>
            <mat-option [value]="21">Cada 3 semanas</mat-option>
            <mat-option [value]="28">Cada 4 semanas</mat-option>
            <mat-option [value]="42">Cada 6 semanas</mat-option>
          </mat-select>
        </mat-form-field>
      </div>
      <p class="resumen">
        {{ cuotas || 0 }} cuotas de $ {{ money(valorNum()) }} = <strong>$ {{ money(valorNum() * (cuotas || 0)) }}</strong>.
        @if (restante() > 0) { Falta por planificar: $ {{ money(restante()) }} del valor acordado. }
        Cada fila queda con su fecha de control y su vencimiento, y luego se edita en la tabla.
      </p>
      @if (error()) { <p class="error">{{ error() }}</p> }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button type="button" mat-dialog-close>Cancelar</button>
      <button mat-flat-button type="button" (click)="guardar()" [disabled]="guardando() || !cuotas || !desde">Agregar</button>
    </mat-dialog-actions>
  `,
  styles: [DIALOG_STYLES],
})
export class OrthoGenerateDialogComponent {
  readonly caso = inject<OrthoCaseDetail>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<OrthoGenerateDialogComponent, OrthoCaseDetail>);
  private readonly api = inject(OrthodonticsService);

  readonly restante = computed(() => Math.max(0, Number(this.caso.agreed_total) - Number(this.caso.controls_total)));
  cuotas = this.caso.estimated_months ?? 12;
  valor = '';
  desde = this.siguienteFecha();
  cada = 0;
  tocado = false;
  readonly guardando = signal(false);
  readonly error = signal<string | null>(null);
  readonly money = formatMoney;

  constructor() {
    this.sugerir();
  }

  valorNum(): number {
    const v = Number(String(this.valor || '0').replace(',', '.'));
    return isNaN(v) ? 0 : v;
  }

  sugerir(): void {
    const r = this.restante();
    this.valor = r > 0 && this.cuotas > 0 ? (Math.round((r / this.cuotas) * 100) / 100).toFixed(2) : this.valor || '0';
  }

  private siguienteFecha(): string {
    const fechas = this.caso.controls.map((c) => c.planned_on || c.due_on).filter((x): x is string => !!x).sort();
    if (!fechas.length) return this.caso.started_on || hoyIso();
    const d = new Date(fechas[fechas.length - 1] + 'T12:00');
    d.setMonth(d.getMonth() + 1);
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
  }

  async guardar(): Promise<void> {
    this.guardando.set(true);
    this.error.set(null);
    try {
      const out = await firstValueFrom(
        this.api.generate(this.caso.id, {
          count: Number(this.cuotas),
          first_on: this.desde,
          amount: this.valorNum().toFixed(2),
          every_days: this.cada || null,
        }),
      );
      this.ref.close(out);
    } catch (e) {
      this.error.set(mensajeError(e));
    } finally {
      this.guardando.set(false);
    }
  }
}

export interface OrthoPaymentData {
  caso: OrthoCaseDetail;
  control: OrthoControl;
}

@Component({
  selector: 'app-ortho-payment-dialog',
  standalone: true,
  imports: [FormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule],
  template: `
    <h2 mat-dialog-title>Abono a la cuota {{ pad(data.control.number) }}</h2>
    <mat-dialog-content>
      <p class="resumen">
        {{ data.caso.patient.first_name }} {{ data.caso.patient.last_name }} · {{ data.caso.code }}<br />
        Valor de la cuota: $ {{ money(data.control.amount) }} · Abonado: $ {{ money(data.control.paid) }} ·
        <strong>Saldo: $ {{ money(data.control.balance) }}</strong>
      </p>
      <div class="dialog-grid">
        <mat-form-field appearance="outline">
          <mat-label>Monto</mat-label>
          <span matTextPrefix>$&nbsp;</span>
          <input matInput inputmode="decimal" [(ngModel)]="monto" cdkFocusInitial />
        </mat-form-field>
        <mat-form-field appearance="outline">
          <mat-label>Medio de pago</mat-label>
          <mat-select [(ngModel)]="medio">
            @for (m of medios(); track m.code) { <mat-option [value]="m.code">{{ m.label }}</mat-option> }
          </mat-select>
        </mat-form-field>
        @if (pideReferencia()) {
          <mat-form-field appearance="outline">
            <mat-label>Número de referencia</mat-label>
            <input matInput [(ngModel)]="referencia" maxlength="120" />
          </mat-form-field>
        }
        <mat-form-field appearance="outline">
          <mat-label>Fecha</mat-label>
          <input matInput type="date" [(ngModel)]="fecha" />
        </mat-form-field>
        <mat-form-field appearance="outline" class="full">
          <mat-label>Nota (opcional)</mat-label>
          <input matInput [(ngModel)]="nota" />
        </mat-form-field>
      </div>
      @if (error()) { <p class="error">{{ error() }}</p> }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button type="button" mat-dialog-close>Cancelar</button>
      <button mat-flat-button type="button" (click)="guardar()" [disabled]="guardando()">Registrar abono</button>
    </mat-dialog-actions>
  `,
  styles: [DIALOG_STYLES],
})
export class OrthoPaymentDialogComponent implements OnInit {
  readonly data = inject<OrthoPaymentData>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<OrthoPaymentDialogComponent, OrthoCaseDetail>);
  private readonly api = inject(OrthodonticsService);
  private readonly finance = inject(FinanceService);

  readonly medios = signal<PaymentMethodOption[]>([]);
  monto = Number(this.data.control.balance) > 0 ? Number(this.data.control.balance).toFixed(2) : '';
  medio: PaymentMethodCode = 'efectivo';
  referencia = '';
  fecha = hoyIso();
  nota = '';
  readonly guardando = signal(false);
  readonly error = signal<string | null>(null);
  readonly money = formatMoney;

  async ngOnInit(): Promise<void> {
    try {
      this.medios.set(await firstValueFrom(this.finance.getMethods()));
    } catch {
      this.medios.set([{ code: 'efectivo', label: 'Efectivo', requires_reference: false }]);
    }
  }

  pideReferencia(): boolean {
    return !!this.medios().find((m) => m.code === this.medio)?.requires_reference;
  }

  pad(n: number): string {
    return String(n).padStart(2, '0');
  }

  async guardar(): Promise<void> {
    const v = Number(String(this.monto).replace(',', '.'));
    if (!v || v <= 0) {
      this.error.set('Escriba un monto mayor a cero.');
      return;
    }
    if (this.pideReferencia() && !this.referencia.trim()) {
      this.error.set('Este medio de pago requiere número de referencia.');
      return;
    }
    this.guardando.set(true);
    this.error.set(null);
    try {
      const out = await firstValueFrom(
        this.api.pay(this.data.control.id, {
          amount: v.toFixed(2),
          method: this.medio,
          reference: this.pideReferencia() ? this.referencia.trim() : null,
          received_on: this.fecha || null,
          notes: this.nota.trim() || null,
        }),
      );
      this.ref.close(out);
    } catch (e) {
      this.error.set(mensajeError(e));
    } finally {
      this.guardando.set(false);
    }
  }
}
