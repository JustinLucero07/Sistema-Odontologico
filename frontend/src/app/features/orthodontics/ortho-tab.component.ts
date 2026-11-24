import { DatePipe } from '@angular/common';
import { Component, Input, OnChanges, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatButtonToggleModule } from '@angular/material/button-toggle';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatMenuModule } from '@angular/material/menu';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { formatMoney } from '../../core/models/finance.models';
import {
  ORTHO_CONTROL_LABEL,
  ORTHO_DOC_FIELDS,
  ORTHO_DOC_LABEL,
  ORTHO_STATUS_LABEL,
  ORTHO_TAD_LABEL,
  OrthoCase,
  OrthoCaseDetail,
  OrthoControl,
  OrthoControlFields,
  OrthoDocField,
  OrthoDocStatus,
  OrthoPaymentLine,
  OrthoStatus,
  OrthoTad,
} from '../../core/models/orthodontics.models';
import { FinanceService } from '../../core/services/finance.service';
import { OrthodonticsService } from '../../core/services/orthodontics.service';
import { openPaymentInfo } from '../../shared/payment-info/payment-info-dialog.component';
import { confirmAction } from '../../shared/confirm-dialog/confirm-dialog.component';
import { promptVoidReason } from '../../shared/confirm-dialog/prompt-dialog.component';
import {
  OrthoGenerateDialogComponent,
  OrthoPaymentDialogComponent,
  hoyIso,
  mensajeError,
  openOrthoCaseDialog,
} from './ortho-dialogs.component';

type Filtro = 'todas' | 'pendientes' | 'pagadas';
type CampoTexto = 'planning' | 'arches' | 'elastics' | 'tads';

@Component({
  selector: 'app-ortho-tab',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    MatButtonModule,
    MatButtonToggleModule,
    MatIconModule,
    MatMenuModule,
    MatSelectModule,
    MatTabsModule,
    MatTooltipModule,
  ],
  templateUrl: './ortho-tab.component.html',
  styleUrl: './ortho-tab.component.scss',
})
export class OrthoTabComponent implements OnChanges {
  @Input({ required: true }) patientId!: string;
  @Input() patientName = '';

  private readonly api = inject(OrthodonticsService);
  private readonly finance = inject(FinanceService);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);
  private readonly auth = inject(AuthService);

  readonly canWrite = this.auth.hasPermission('orthodontics:write');
  readonly canPay = this.auth.hasPermission('payments:write');

  readonly cargando = signal(true);
  readonly fichas = signal<OrthoCase[]>([]);
  readonly caso = signal<OrthoCaseDetail | null>(null);
  readonly filtro = signal<Filtro>('todas');
  readonly abiertos = signal<Set<string>>(new Set());
  readonly guardandoFila = signal<string | null>(null);
  readonly docs = signal<Record<OrthoDocField, OrthoDocStatus>>({
    doc_xrays: 'por_revisar',
    doc_photos: 'por_revisar',
    doc_models: 'por_revisar',
    doc_folder: 'por_revisar',
  });
  docNotas: Partial<Record<OrthoDocField, string>> = {};
  readonly docsCambiados = signal(false);

  readonly statusLabel = ORTHO_STATUS_LABEL;
  readonly tadLabel = ORTHO_TAD_LABEL;
  readonly docLabel = ORTHO_DOC_LABEL;
  readonly docFields = ORTHO_DOC_FIELDS;
  readonly controlLabel = ORTHO_CONTROL_LABEL;
  readonly statuses = Object.entries(ORTHO_STATUS_LABEL) as [OrthoStatus, string][];
  readonly tads = Object.entries(ORTHO_TAD_LABEL) as [OrthoTad, string][];
  readonly docStatuses = Object.entries(ORTHO_DOC_LABEL) as [OrthoDocStatus, string][];
  readonly money = formatMoney;

  readonly filas = computed(() => {
    const c = this.caso();
    if (!c) return [];
    const f = this.filtro();
    if (f === 'pagadas') return c.controls.filter((x) => x.status === 'pagada');
    if (f === 'pendientes') return c.controls.filter((x) => x.status !== 'pagada');
    return c.controls;
  });
  readonly otrasFichas = computed(() => this.fichas().filter((f) => f.id !== this.caso()?.id));
  readonly diferencia = computed(() => Number(this.caso()?.difference ?? 0));

  ngOnChanges(): void {
    void this.cargar();
  }

  async cargar(id?: string): Promise<void> {
    this.cargando.set(true);
    try {
      const lista = await firstValueFrom(this.api.forPatient(this.patientId));
      this.fichas.set(lista);
      const elegido =
        (id && lista.find((f) => f.id === id)) ||
        lista.find((f) => ['activo', 'retencion', 'pausa'].includes(f.status)) ||
        lista[lista.length - 1];
      if (elegido) this.poner(await firstValueFrom(this.api.get(elegido.id)));
      else this.caso.set(null);
    } catch {
      this.caso.set(null);
    } finally {
      this.cargando.set(false);
    }
  }

  private poner(c: OrthoCaseDetail): void {
    this.caso.set(c);
    this.docs.set({ doc_xrays: c.doc_xrays, doc_photos: c.doc_photos, doc_models: c.doc_models, doc_folder: c.doc_folder });
    this.docNotas = { ...c.doc_notes };
    this.docsCambiados.set(false);
    this.fichas.update((l) => l.map((f) => (f.id === c.id ? c : f)));
  }

  async nueva(): Promise<void> {
    const out = await openOrthoCaseDialog(this.dialog, {
      patient: { id: this.patientId, name: this.patientName || 'Paciente' },
    });
    if (out) {
      this.snack.open(`Ficha ${out.code} creada.`, 'Cerrar', { duration: 3000 });
      await this.cargar(out.id);
    }
  }

  async editar(): Promise<void> {
    const c = this.caso();
    if (!c) return;
    const out = await openOrthoCaseDialog(this.dialog, { caso: c });
    if (out) this.poner(out);
  }

  async cambiar(campo: 'status' | 'has_tad' | 'needs_review', valor: OrthoStatus | OrthoTad | boolean): Promise<void> {
    const c = this.caso();
    if (!c) return;
    try {
      this.poner(await firstValueFrom(this.api.update(c.id, { [campo]: valor })));
      this.snack.open('Guardado.', undefined, { duration: 1400 });
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 5000 });
      this.poner(c);
    }
  }

  async eliminar(): Promise<void> {
    const c = this.caso();
    if (!c) return;
    const ok = await confirmAction(this.dialog, {
      title: `¿Eliminar la ficha ${c.code}?`,
      message:
        'Se borran la ficha, su plan de cuotas y la documentación. Si ya tiene abonos no se puede: márquela como «Finalizado».',
      confirmLabel: 'Eliminar',
      danger: true,
    });
    if (!ok) return;
    try {
      await firstValueFrom(this.api.remove(c.id));
      this.snack.open('Ficha eliminada.', 'Cerrar', { duration: 3000 });
      await this.cargar();
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 6000 });
    }
  }

  async abrirFicha(id: string): Promise<void> {
    this.poner(await firstValueFrom(this.api.get(id)));
  }

  async exportar(tipo: 'pdf' | 'csv'): Promise<void> {
    const c = this.caso();
    if (!c) return;
    try {
      const blob = await firstValueFrom(this.api.download(c.id, tipo));
      const url = URL.createObjectURL(blob);
      if (tipo === 'pdf') {
        window.open(url, '_blank');
      } else {
        const a = document.createElement('a');
        a.href = url;
        a.download = `ortodoncia-${c.code}.csv`;
        a.click();
      }
      setTimeout(() => URL.revokeObjectURL(url), 60_000);
    } catch {
      this.snack.open('No se pudo generar el archivo.', 'Cerrar', { duration: 4000 });
    }
  }

  async agregarCuotas(): Promise<void> {
    const c = this.caso();
    if (!c) return;
    const ref = this.dialog.open(OrthoGenerateDialogComponent, {
      data: c,
      width: '560px',
      maxWidth: '96vw',
      panelClass: 'app-dialog',
    });
    const out = await firstValueFrom(ref.afterClosed());
    if (out) this.poner(out);
  }

  async guardarFila(ctrl: OrthoControl, cambios: OrthoControlFields): Promise<void> {
    this.guardandoFila.set(ctrl.id);
    try {
      this.poner(await firstValueFrom(this.api.updateControl(ctrl.id, cambios)));
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 5000 });
      const c = this.caso();
      if (c) this.caso.set({ ...c });
    } finally {
      this.guardandoFila.set(null);
    }
  }

  textoCambio(ctrl: OrthoControl, campo: CampoTexto, valor: string): void {
    const limpio = valor.trim() || null;
    if (limpio === (ctrl[campo] ?? null)) return;
    void this.guardarFila(ctrl, { [campo]: limpio });
  }

  fechaCambio(ctrl: OrthoControl, campo: 'planned_on' | 'due_on' | 'attended_on', valor: string): void {
    const v = valor || null;
    if (v === ctrl[campo]) return;
    void this.guardarFila(ctrl, { [campo]: v });
  }

  valorCambio(ctrl: OrthoControl, valor: string): void {
    const n = Number(String(valor).replace(',', '.'));
    if (isNaN(n) || n < 0) {
      this.snack.open('Valor no válido.', undefined, { duration: 2000 });
      return;
    }
    if (n === Number(ctrl.amount)) return;
    void this.guardarFila(ctrl, { amount: n.toFixed(2) });
  }

  marcarAsistencia(ctrl: OrthoControl): void {
    void this.guardarFila(ctrl, { attended_on: ctrl.attended_on ? null : ctrl.planned_on && ctrl.planned_on <= hoyIso() ? ctrl.planned_on : hoyIso() });
  }

  async abonar(ctrl: OrthoControl): Promise<void> {
    const c = this.caso();
    if (!c) return;
    const ref = this.dialog.open(OrthoPaymentDialogComponent, {
      data: { caso: c, control: ctrl },
      width: '520px',
      maxWidth: '96vw',
      panelClass: 'app-dialog',
    });
    const out = await firstValueFrom(ref.afterClosed());
    if (out) {
      this.poner(out);
      this.snack.open('Abono registrado.', 'Cerrar', { duration: 2500 });
    }
  }

  async anularAbono(p: OrthoPaymentLine): Promise<void> {
    const motivo = await promptVoidReason(this.dialog, `el abono de $ ${formatMoney(p.amount)}`);
    if (!motivo) return;
    try {
      await firstValueFrom(this.finance.voidPayment(p.id, motivo));
      const c = this.caso();
      if (c) this.poner(await firstValueFrom(this.api.get(c.id)));
      this.snack.open('Abono anulado.', 'Cerrar', { duration: 2500 });
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 5000 });
    }
  }

  async eliminarCuota(ctrl: OrthoControl): Promise<void> {
    const ok = await confirmAction(this.dialog, {
      title: `¿Eliminar la cuota ${this.pad(ctrl.number)}?`,
      message: 'Las demás se renumeran. Una cuota con abonos no se puede eliminar.',
      confirmLabel: 'Eliminar',
      danger: true,
    });
    if (!ok) return;
    try {
      this.poner(await firstValueFrom(this.api.removeControl(ctrl.id)));
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 5000 });
    }
  }

  alternarAbonos(id: string): void {
    const s = new Set(this.abiertos());
    if (s.has(id)) s.delete(id);
    else s.add(id);
    this.abiertos.set(s);
  }

  cambiarDoc(campo: OrthoDocField, valor: OrthoDocStatus): void {
    this.docs.update((d) => ({ ...d, [campo]: valor }));
    this.docsCambiados.set(true);
  }

  async guardarDocs(): Promise<void> {
    const c = this.caso();
    if (!c) return;
    const notas: Record<string, string> = {};
    for (const [k, v] of Object.entries(this.docNotas)) if (v?.trim()) notas[k] = v.trim();
    try {
      this.poner(await firstValueFrom(this.api.update(c.id, { ...this.docs(), doc_notes: notas })));
      this.snack.open('Documentación guardada.', undefined, { duration: 2000 });
    } catch (e) {
      this.snack.open(mensajeError(e), 'Cerrar', { duration: 5000 });
    }
  }

  datosPago(): void {
    const c = this.caso();
    if (!c) return;
    const cuota = c.controls.find((x) => +x.balance > 0);
    openPaymentInfo(this.dialog, {
      patientName: `${c.patient.first_name} ${c.patient.last_name}`,
      phone: c.patient.whatsapp || c.patient.phone,
      amount: cuota ? cuota.balance : null,
      concept: cuota ? `cuota ${this.pad(cuota.number)} de ortodoncia` : null,
    });
  }

  pad(n: number): string {
    return String(n).padStart(2, '0');
  }

  vivos(c: OrthoControl): number {
    return c.payments.filter((p) => !p.voided_at).length;
  }

  abs(n: number): number {
    return Math.abs(n);
  }
}
