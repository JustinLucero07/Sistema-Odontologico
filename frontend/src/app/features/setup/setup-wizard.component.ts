import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatCheckboxModule } from '@angular/material/checkbox';
import { MatDialog } from '@angular/material/dialog';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { BRAND_PALETTE, BrandingService, PracticeType } from '../../core/branding/branding.service';
import { ClinicService } from '../../core/services/clinic.service';
import { ToothMarkComponent } from '../../shared/brand/tooth-mark.component';
import { openLegalDoc } from '../../shared/legal/legal-doc-dialog.component';

interface Modulo {
  code: string;
  label: string;
  hint: string;
  icon: string;
}

const MODULOS: Modulo[] = [
  { code: 'opportunities', label: 'Oportunidades', hint: 'A quién escribir hoy por WhatsApp', icon: 'tips_and_updates' },
  { code: 'cash', label: 'Caja del día', hint: 'Apertura, arqueo y cierre de caja', icon: 'point_of_sale' },
  { code: 'credits', label: 'Créditos', hint: 'Tratamientos pagados en cuotas', icon: 'credit_score' },
  { code: 'reports', label: 'Reportes', hint: 'Indicadores y exportación a Excel', icon: 'insights' },
  { code: 'inventory', label: 'Inventario', hint: 'Insumos, stock mínimo y caducidad', icon: 'inventory_2' },
  { code: 'laboratory', label: 'Laboratorio', hint: 'Órdenes de coronas, prótesis…', icon: 'precision_manufacturing' },
  { code: 'consents', label: 'Plantillas de consentimiento', hint: 'Textos de consentimiento informado', icon: 'draw' },
  { code: 'messages', label: 'Plantillas de mensajes', hint: 'Recordatorios por WhatsApp', icon: 'forum' },
];

/** Qué conviene ocultar de inicio según el tamaño de la consulta. */
const OCULTOS_POR_TIPO: Record<PracticeType, string[]> = {
  independiente: ['inventory', 'laboratory', 'cash', 'messages'],
  consultorio: ['inventory'],
  clinica: [],
};

const DIAS = [
  { n: '1', l: 'Lun' },
  { n: '2', l: 'Mar' },
  { n: '3', l: 'Mié' },
  { n: '4', l: 'Jue' },
  { n: '5', l: 'Vie' },
  { n: '6', l: 'Sáb' },
  { n: '7', l: 'Dom' },
];

/**
 * Asistente de bienvenida: la primera vez que entra el administrador elige
 * cómo trabaja (solo, consultorio o clínica), sus datos, su logo, su color,
 * su horario y qué módulos ver. Con `data.edit` es la página de
 * Personalización, para cambiar todo eso después.
 */
@Component({
  selector: 'app-setup-wizard',
  standalone: true,
  imports: [FormsModule, MatButtonModule, MatCheckboxModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSlideToggleModule, ToothMarkComponent],
  templateUrl: './setup-wizard.component.html',
  styleUrl: './setup-wizard.component.scss',
})
export class SetupWizardComponent implements OnInit, OnDestroy {
  private readonly clinics = inject(ClinicService);
  private readonly branding = inject(BrandingService);
  private readonly router = inject(Router);
  private readonly snack = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);
  readonly auth = inject(AuthService);
  readonly edit = !!inject(ActivatedRoute).snapshot.data['edit'];

  readonly palette = BRAND_PALETTE;
  readonly modulos = MODULOS;
  readonly dias = DIAS;
  readonly pasos = ['Tu consulta', 'Datos', 'Tu marca', 'Horario', 'Módulos'];

  readonly paso = signal(0);
  readonly guardando = signal(false);
  readonly error = signal<string | null>(null);

  // Respuestas
  readonly tipo = signal<PracticeType>('independiente');
  nombre = '';
  razonSocial = '';
  ruc = '';
  telefono = '';
  correo = '';
  direccion = '';
  eslogan = '';
  pie = '';
  atiendo = true;
  registro = '';
  especialidad = 'Odontología general';
  readonly color = signal('#0D7F76');
  readonly logo = signal<string | null>(null);
  aceptaTerminos = false;
  abre = '08:00';
  cierra = '18:00';
  readonly diasSel = signal(new Set(['1', '2', '3', '4', '5', '6']));
  readonly ocultos = signal(new Set<string>(OCULTOS_POR_TIPO.independiente));

  readonly usuario = computed(() => this.auth.currentUser());
  readonly tipoTexto = computed(
    () => ({ independiente: 'Consultorio', consultorio: 'Consultorio', clinica: 'Clínica' })[this.tipo()],
  );

  async ngOnInit(): Promise<void> {
    const u = this.auth.currentUser();
    if (u) this.correo = u.email;
    try {
      const c = await firstValueFrom(this.clinics.getMyClinic());
      // Se configura una sola vez: si ya se hizo (en el celular o en otra
      // pestaña), no se repite; lo demás se cambia en Personalización.
      if (!this.edit && c.setup_completed_at) {
        await this.branding.load();
        this.snack.open('Tu consulta ya está configurada.', 'Cerrar', { duration: 3500 });
        await this.router.navigate(['/dashboard']);
        return;
      }
      // Un nombre de fábrica no se propone: que el cliente escriba el suyo.
      this.nombre = this.edit || c.setup_completed_at ? c.name : c.name === 'Clínica Demo' ? '' : c.name;
      this.razonSocial = c.legal_name ?? '';
      this.ruc = c.tax_id ?? '';
      this.telefono = c.phone ?? '';
      this.correo = c.email ?? this.correo;
      this.direccion = c.address ?? '';
      this.eslogan = c.slogan ?? '';
      this.pie = c.document_footer ?? '';
      this.abre = c.opens_at ?? this.abre;
      this.cierra = c.closes_at ?? this.cierra;
      this.diasSel.set(new Set((c.work_days ?? '123456').split('')));
      if (c.logo_data) this.logo.set(c.logo_data);
      if (c.primary_color) this.color.set(c.primary_color.toUpperCase());
      if (this.edit || c.setup_completed_at) {
        this.tipo.set(c.practice_type ?? 'clinica');
        this.ocultos.set(new Set(c.hidden_modules ?? []));
      }
    } catch {
      // Sin datos previos se empieza en blanco.
    }
    this.branding.preview(this.color());
  }

  ngOnDestroy(): void {
    this.branding.restore();
  }

  verDocumento(ev: Event, code: 'terminos' | 'encargo'): void {
    ev.preventDefault();
    ev.stopPropagation();
    openLegalDoc(this.dialog, code);
  }

  elegirTipo(t: PracticeType): void {
    this.tipo.set(t);
    if (!this.edit) this.ocultos.set(new Set(OCULTOS_POR_TIPO[t]));
    this.atiendo = t !== 'clinica';
  }

  elegirColor(hex: string): void {
    this.color.set(hex.toUpperCase());
    this.branding.preview(hex);
  }

  alternarDia(n: string): void {
    const s = new Set(this.diasSel());
    s.has(n) ? s.delete(n) : s.add(n);
    this.diasSel.set(s);
  }

  alternarModulo(code: string, visible: boolean): void {
    const s = new Set(this.ocultos());
    visible ? s.delete(code) : s.add(code);
    this.ocultos.set(s);
  }

  /** El logo se reduce en el navegador a 512 px antes de guardarlo: una foto
   *  del celular pesa varios MB y aquí basta con unos KB. */
  async subirLogo(ev: Event): Promise<void> {
    const file = (ev.target as HTMLInputElement).files?.[0];
    (ev.target as HTMLInputElement).value = '';
    if (!file) return;
    if (!file.type.startsWith('image/')) {
      this.error.set('El logo debe ser una imagen (PNG, JPG, WebP o SVG).');
      return;
    }
    if (file.type === 'image/svg+xml') {
      if (file.size > 400_000) return this.error.set('El SVG es demasiado grande (máx. 400 KB).');
      this.logo.set(await leer(file));
      return;
    }
    const url = await leer(file);
    const img = new Image();
    img.src = url;
    await img.decode();
    const lado = 512;
    const k = Math.min(1, lado / Math.max(img.width, img.height));
    const canvas = document.createElement('canvas');
    canvas.width = Math.round(img.width * k);
    canvas.height = Math.round(img.height * k);
    canvas.getContext('2d')!.drawImage(img, 0, 0, canvas.width, canvas.height);
    this.logo.set(canvas.toDataURL('image/png'));
    this.error.set(null);
  }

  puedeSeguir(): boolean {
    if (this.paso() === 1) return this.nombre.trim().length >= 2;
    if (this.paso() === 3) return this.diasSel().size > 0 && this.abre < this.cierra;
    if (this.paso() === this.pasos.length - 1 && !this.edit) return this.aceptaTerminos;
    return true;
  }

  siguiente(): void {
    if (!this.puedeSeguir()) return;
    if (this.paso() < this.pasos.length - 1) this.paso.update((p) => p + 1);
    else void this.terminar();
  }

  atras(): void {
    this.paso.update((p) => Math.max(0, p - 1));
  }

  async terminar(): Promise<void> {
    this.guardando.set(true);
    this.error.set(null);
    const datos = {
      name: this.nombre.trim(),
      legal_name: this.razonSocial.trim() || null,
      tax_id: this.ruc.trim() || null,
      phone: this.telefono.trim() || null,
      email: this.correo.trim() || null,
      address: this.direccion.trim() || null,
      slogan: this.eslogan.trim() || null,
      document_footer: this.pie.trim() || null,
      practice_type: this.tipo(),
      primary_color: this.color(),
      logo_data: this.logo(),
      opens_at: this.abre,
      closes_at: this.cierra,
      work_days: [...this.diasSel()].sort().join(''),
      hidden_modules: [...this.ocultos()],
    };
    try {
      if (this.edit) {
        await firstValueFrom(this.clinics.updateMyClinic(datos as never));
      } else {
        await firstValueFrom(
          this.clinics.completeSetup({
            ...datos,
            i_am_dentist: this.atiendo,
            accept_terms: this.aceptaTerminos,
            license_number: this.registro.trim() || null,
            specialty: this.especialidad.trim() || null,
          }),
        );
      }
      await this.branding.load();
      this.snack.open(this.edit ? 'Personalización guardada' : '¡Todo listo! Bienvenido a tu nuevo sistema.', 'Cerrar', {
        duration: 4000,
      });
      if (!this.edit) await this.router.navigate(['/dashboard']);
    } catch (e: unknown) {
      const det = (e as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(
        typeof det === 'string'
          ? det
          : Array.isArray(det)
            ? String((det[0] as { msg?: string })?.msg ?? 'Revise los datos').replace('Value error, ', '')
            : 'No se pudo guardar. Revise la conexión.',
      );
    } finally {
      this.guardando.set(false);
    }
  }
}

function leer(file: File): Promise<string> {
  return new Promise((ok, mal) => {
    const r = new FileReader();
    r.onload = () => ok(String(r.result));
    r.onerror = mal;
    r.readAsDataURL(file);
  });
}
