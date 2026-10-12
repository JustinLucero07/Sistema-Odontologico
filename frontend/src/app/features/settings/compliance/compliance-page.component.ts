import { DatePipe } from '@angular/common';
import { Component, OnInit, TemplateRef, ViewChild, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, debounceTime, firstValueFrom } from 'rxjs';

import { BrandingService } from '../../../core/branding/branding.service';
import { Clinic } from '../../../core/models/clinic.models';
import { PatientListItem } from '../../../core/models/patient.models';
import { ClinicService } from '../../../core/services/clinic.service';
import { LegalCatalogs, LegalService, RightsRequest, RightsRequestInput } from '../../../core/services/legal.service';
import { PatientsService } from '../../../core/services/patients.service';
import { confirmAction } from '../../../shared/confirm-dialog/confirm-dialog.component';
import { openLegalDoc } from '../../../shared/legal/legal-doc-dialog.component';

type Tab = 'resumen' | 'responsable' | 'tributario' | 'datos' | 'seguridad' | 'terminos' | 'solicitudes';

const CAMPOS = [
  'legal_name', 'tax_id', 'address', 'email', 'phone',
  'legal_rep_name', 'legal_rep_id', 'dpo_name', 'dpo_email', 'health_permit_number', 'health_permit_expires_on',
  'tax_regime', 'keeps_accounting', 'special_taxpayer', 'sri_establishment', 'sri_emission_point', 'vat_rate',
  'record_retention_years', 'privacy_extra', 'session_timeout_minutes',
] as const;
type Form = Partial<Pick<Clinic, (typeof CAMPOS)[number]>>;

/**
 * Configuración › Legal y cumplimiento: lo que una consulta necesita tener en
 * regla (responsable y representante, SRI, permiso de funcionamiento,
 * protección de datos, seguridad de sesión, términos aceptados y solicitudes
 * de los pacientes sobre sus datos). Se guarda en el servidor: la web y el
 * celular ven lo mismo.
 */
@Component({
  selector: 'app-compliance-page',
  standalone: true,
  imports: [
    DatePipe, FormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatInputModule,
    MatSelectModule, MatSlideToggleModule, MatTooltipModule,
  ],
  templateUrl: './compliance-page.component.html',
  styleUrl: './compliance-page.component.scss',
})
export class CompliancePageComponent implements OnInit {
  private readonly clinics = inject(ClinicService);
  private readonly legal = inject(LegalService);
  private readonly patients = inject(PatientsService);
  private readonly branding = inject(BrandingService);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);

  readonly tabs: { id: Tab; label: string; icon: string }[] = [
    { id: 'resumen', label: 'Resumen', icon: 'fact_check' },
    { id: 'responsable', label: 'Responsable', icon: 'badge' },
    { id: 'tributario', label: 'Tributario (SRI)', icon: 'receipt_long' },
    { id: 'datos', label: 'Protección de datos', icon: 'shield' },
    { id: 'seguridad', label: 'Seguridad', icon: 'lock_clock' },
    { id: 'terminos', label: 'Términos', icon: 'gavel' },
    { id: 'solicitudes', label: 'Solicitudes', icon: 'inbox' },
  ];
  readonly tab = signal<Tab>('resumen');
  readonly clinic = signal<Clinic | null>(null);
  readonly catalogs = signal<LegalCatalogs | null>(null);
  readonly requests = signal<RightsRequest[]>([]);
  readonly guardando = signal(false);
  form: Form = {};

  readonly timeouts = [
    { v: 0, l: 'Nunca (no recomendado)' },
    { v: 10, l: '10 minutos' },
    { v: 15, l: '15 minutos' },
    { v: 30, l: '30 minutos' },
    { v: 60, l: '1 hora' },
    { v: 120, l: '2 horas' },
    { v: 480, l: '8 horas' },
  ];

  readonly abiertas = computed(() => this.requests().filter((r) => r.status === 'pendiente' || r.status === 'en_proceso'));
  readonly vencidas = computed(() => this.requests().filter((r) => r.overdue));

  /** Lista de verificación: qué está en regla y qué falta. */
  readonly checklist = computed(() => {
    const c = this.clinic();
    if (!c) return [];
    const dias = c.health_permit_expires_on
      ? Math.round((new Date(c.health_permit_expires_on + 'T12:00').getTime() - Date.now()) / 86_400_000)
      : null;
    return [
      { ok: !!(c.legal_name && c.tax_id && c.address), tab: 'responsable' as Tab,
        label: 'Razón social, RUC y dirección', hint: 'Salen en recibos, recetas y en el aviso de privacidad.' },
      { ok: !!c.legal_rep_name, tab: 'responsable' as Tab,
        label: 'Representante legal', hint: 'Quién firma por la consulta.' },
      { ok: dias !== null && dias >= 0, tab: 'responsable' as Tab,
        label: 'Permiso de funcionamiento vigente',
        hint: dias === null ? 'Registra el número y la fecha de vencimiento.' : dias < 0 ? `Venció hace ${-dias} días.` : `Vence en ${dias} días.` },
      { ok: !!c.tax_regime && !!c.sri_establishment, tab: 'tributario' as Tab,
        label: 'Datos tributarios', hint: 'Régimen, establecimiento y punto de emisión.' },
      { ok: !!(c.dpo_name && c.dpo_email), tab: 'datos' as Tab,
        label: 'Delegado de protección de datos', hint: 'A quién escriben los pacientes sobre sus datos.' },
      { ok: c.session_timeout_minutes > 0, tab: 'seguridad' as Tab,
        label: 'Cierre de sesión por inactividad', hint: 'Evita que una pantalla abierta exponga historias clínicas.' },
      { ok: c.terms_version === c.terms_current_version, tab: 'terminos' as Tab,
        label: 'Términos de uso y contrato de encargo aceptados', hint: `Versión vigente ${c.terms_current_version}.` },
      { ok: this.vencidas().length === 0, tab: 'solicitudes' as Tab,
        label: 'Solicitudes de pacientes al día',
        hint: this.vencidas().length ? `${this.vencidas().length} fuera de plazo.` : 'Ninguna fuera de plazo.' },
    ];
  });
  readonly cumplidos = computed(() => this.checklist().filter((i) => i.ok).length);

  // ---- Diálogo de solicitud ----
  @ViewChild('requestDialog') requestDialog!: TemplateRef<unknown>;
  private requestRef: MatDialogRef<unknown> | null = null;
  editando: RightsRequest | null = null;
  solicitud: RightsRequestInput = this.vacia();
  pacienteTexto = '';
  readonly pacientes = signal<PatientListItem[]>([]);
  private readonly buscar$ = new Subject<string>();

  async ngOnInit(): Promise<void> {
    this.buscar$.pipe(debounceTime(250)).subscribe(async (t) =>
      this.pacientes.set(t.trim().length < 2 ? [] : await firstValueFrom(this.patients.listPatients(t))),
    );
    const [c, cat] = await Promise.all([
      firstValueFrom(this.clinics.getMyClinic()),
      firstValueFrom(this.legal.getCatalogs()),
    ]);
    this.setClinic(c);
    this.catalogs.set(cat);
    await this.cargarSolicitudes();
  }

  private setClinic(c: Clinic): void {
    this.clinic.set(c);
    this.form = Object.fromEntries(CAMPOS.map((k) => [k, c[k]])) as Form;
  }

  private async cargarSolicitudes(): Promise<void> {
    this.requests.set(await firstValueFrom(this.legal.listRequests()));
  }

  async guardar(): Promise<void> {
    this.guardando.set(true);
    const datos: Record<string, unknown> = {};
    for (const k of CAMPOS) {
      const v = this.form[k];
      datos[k] = typeof v === 'string' ? v.trim() || null : v;
    }
    try {
      const c = await firstValueFrom(this.clinics.updateMyClinic(datos as Partial<Clinic>));
      this.setClinic(c);
      this.legal.refreshController();
      await this.branding.load();
      this.snack.open('Configuración legal guardada', 'Cerrar', { duration: 3000 });
    } catch (e) {
      this.snack.open(this.error(e), 'Cerrar', { duration: 6000 });
    } finally {
      this.guardando.set(false);
    }
  }

  verDocumento(code: 'terminos' | 'encargo'): void {
    const c = this.clinic();
    const aceptado =
      c?.terms_accepted_at && c.terms_version
        ? `versión ${c.terms_version}, por ${c.terms_accepted_by ?? '—'}, el ${new Date(c.terms_accepted_at).toLocaleString('es-EC')}`
        : null;
    openLegalDoc(this.dialog, code, aceptado);
  }

  async aceptarTerminos(): Promise<void> {
    const ok = await confirmAction(this.dialog, {
      title: 'Aceptar Términos de uso y contrato de encargo',
      message: 'Quedará registrado con tu nombre, la versión y la fecha. ¿Leíste ambos documentos?',
      confirmLabel: 'Acepto',
    });
    if (!ok) return;
    this.setClinic(await firstValueFrom(this.clinics.acceptTerms()));
    await this.branding.load();
    this.snack.open('Términos aceptados', 'Cerrar', { duration: 3000 });
  }

  // ---- Solicitudes ----
  private vacia(): RightsRequestInput {
    return {
      patient_id: null, requester_name: '', requester_id_number: null, contact: null, kind: 'acceso', details: null,
      received_on: new Date().toISOString().slice(0, 10), status: 'pendiente', response: null,
    };
  }

  abrirSolicitud(r: RightsRequest | null): void {
    this.editando = r;
    this.solicitud = r
      ? {
          patient_id: r.patient_id, requester_name: r.requester_name, requester_id_number: r.requester_id_number,
          contact: r.contact, kind: r.kind, details: r.details, received_on: r.received_on, status: r.status,
          response: r.response,
        }
      : this.vacia();
    this.pacienteTexto = r?.patient_name ?? '';
    this.pacientes.set([]);
    this.requestRef = this.dialog.open(this.requestDialog, { width: '620px', maxWidth: '96vw', panelClass: 'app-dialog' });
  }

  buscarPaciente(t: string): void {
    this.pacienteTexto = t;
    if (!t) this.solicitud.patient_id = null;
    this.buscar$.next(t);
  }

  elegirPaciente(p: PatientListItem): void {
    this.solicitud.patient_id = p.id;
    this.pacienteTexto = `${p.first_name} ${p.last_name}`;
    if (!this.solicitud.requester_name) this.solicitud.requester_name = this.pacienteTexto;
    if (!this.solicitud.requester_id_number) this.solicitud.requester_id_number = p.national_id;
    if (!this.solicitud.contact) this.solicitud.contact = p.whatsapp ?? p.phone;
    this.pacientes.set([]);
  }

  async guardarSolicitud(): Promise<void> {
    try {
      await firstValueFrom(this.legal.saveRequest(this.solicitud, this.editando?.id));
      this.requestRef?.close();
      await this.cargarSolicitudes();
      this.snack.open(this.editando ? 'Solicitud actualizada' : 'Solicitud registrada', 'Cerrar', { duration: 3000 });
    } catch (e) {
      this.snack.open(this.error(e), 'Cerrar', { duration: 6000 });
    }
  }

  async eliminarSolicitud(r: RightsRequest): Promise<void> {
    const ok = await confirmAction(this.dialog, {
      title: 'Eliminar solicitud',
      message: `Se eliminará la solicitud de ${r.requester_name}. Queda constancia en la auditoría.`,
      confirmLabel: 'Eliminar',
      danger: true,
    });
    if (!ok) return;
    await firstValueFrom(this.legal.deleteRequest(r.id));
    await this.cargarSolicitudes();
  }

  private error(e: unknown): string {
    const d = (e as { error?: { detail?: unknown } })?.error?.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d)) return String((d[0] as { msg?: string })?.msg ?? 'Revise los datos').replace('Value error, ', '');
    return 'No se pudo guardar. Revise la conexión.';
  }
}
