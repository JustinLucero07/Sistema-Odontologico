import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { ActivatedRoute } from '@angular/router';
import { MatIconModule } from '@angular/material/icon';
import { firstValueFrom } from 'rxjs';

import { formatMoney } from '../../core/models/finance.models';
import { PortalCuota, PortalView } from '../../core/models/communication.models';
import { CommunicationService } from '../../core/services/communication.service';
import { ToothMarkComponent } from '../../shared/brand/tooth-mark.component';
import { BeforeAfterSliderComponent } from '../../shared/imaging/before-after';
import { Odontogram3dComponent } from '../../shared/odontogram/odontogram-3d.component';

interface Destino {
  clave: string;
  etiqueta: string;
  pendiente: number | null;
  charge_id?: string;
  ortho_control_id?: string;
}

@Component({
  selector: 'app-portal-page',
  standalone: true,
  imports: [DatePipe, MatIconModule, ToothMarkComponent, BeforeAfterSliderComponent, Odontogram3dComponent],
  templateUrl: './portal-page.component.html',
  styleUrl: './portal-page.component.scss',
})
export class PortalPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly comms = inject(CommunicationService);
  private token = '';

  readonly view = signal<PortalView | null>(null);
  readonly loading = signal(true);
  readonly error = signal<string | null>(null);
  readonly money = formatMoney;

  readonly formAbierto = signal(false);
  readonly enviando = signal(false);
  readonly errorForm = signal<string | null>(null);
  readonly enviado = signal(false);
  readonly destino = signal('cuenta');
  readonly monto = signal('');
  readonly fecha = signal(new Date().toISOString().slice(0, 10));
  readonly referencia = signal('');
  readonly nota = signal('');
  readonly archivo = signal<File | null>(null);
  readonly vistaPrevia = signal<string | null>(null);
  readonly hoy = new Date().toISOString().slice(0, 10);

  readonly destinos = computed<Destino[]>(() => {
    const v = this.view();
    const out: Destino[] = [{ clave: 'cuenta', etiqueta: 'Abono a mi cuenta', pendiente: v ? Math.max(0, Number(v.balance)) || null : null }];
    for (const c of v?.ortodoncia?.cuotas ?? []) {
      if (Number(c.balance) > 0) {
        out.push({
          clave: `cuota:${c.id}`,
          etiqueta: `Ortodoncia · cuota ${String(c.number).padStart(2, '0')}${c.planned_on ? ` (${c.planned_on.slice(8, 10)}/${c.planned_on.slice(5, 7)})` : ''}`,
          pendiente: Number(c.balance),
          ortho_control_id: c.id,
        });
      }
    }
    if (!v?.ortodoncia) {
      for (const c of v?.charges ?? []) {
        if (c.id && Number(c.pending) > 0) {
          out.push({ clave: `cargo:${c.id}`, etiqueta: c.description, pendiente: Number(c.pending), charge_id: c.id });
        }
      }
    }
    return out;
  });

  async ngOnInit(): Promise<void> {
    this.token = this.route.snapshot.paramMap.get('token') ?? '';
    if (!this.token) {
      this.error.set('El enlace está incompleto.');
      this.loading.set(false);
      return;
    }
    await this.cargar();
  }

  private async cargar(): Promise<void> {
    try {
      this.view.set(await firstValueFrom(this.comms.getPortalView(this.token)));
    } catch (err) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(
        typeof detail === 'string' ? detail : 'No se pudo abrir el enlace. Solicite uno nuevo a su clínica.',
      );
    } finally {
      this.loading.set(false);
    }
  }

  imagen(id: string): string {
    return this.comms.portalImageUrl(this.token, id);
  }

  balanceTone(balance: string): 'owed' | 'credit' | 'settled' {
    const n = Number(balance);
    return n > 0 ? 'owed' : n < 0 ? 'credit' : 'settled';
  }

  tipoCuenta(t: string | null): string {
    return t === 'ahorros' ? 'Cuenta de ahorros' : t === 'corriente' ? 'Cuenta corriente' : 'Cuenta';
  }

  estadoCuota(c: PortalCuota): string {
    return (
      { pagada: 'Pagada', parcial: 'Abonada', vencida: 'Vencida', pendiente: 'Pendiente', sin_valor: '—' } as Record<string, string>
    )[c.status] ?? c.status;
  }

  abrirPago(clave = 'cuenta'): void {
    this.enviado.set(false);
    this.errorForm.set(null);
    this.elegirDestino(clave);
    this.formAbierto.set(true);
  }

  cerrarPago(): void {
    this.formAbierto.set(false);
    this.archivo.set(null);
    this.vistaPrevia.set(null);
    this.referencia.set('');
    this.nota.set('');
  }

  elegirDestino(clave: string): void {
    this.destino.set(clave);
    const d = this.destinos().find((x) => x.clave === clave);
    this.monto.set(d?.pendiente ? d.pendiente.toFixed(2) : '');
  }

  elegirArchivo(ev: Event): void {
    const f = (ev.target as HTMLInputElement).files?.[0] ?? null;
    this.errorForm.set(null);
    if (f && f.size > 10 * 1024 * 1024) {
      this.errorForm.set('El archivo supera los 10 MB.');
      return;
    }
    this.archivo.set(f);
    const previa = this.vistaPrevia();
    if (previa) URL.revokeObjectURL(previa);
    this.vistaPrevia.set(f && f.type.startsWith('image/') ? URL.createObjectURL(f) : null);
  }

  async enviar(): Promise<void> {
    const f = this.archivo();
    const monto = Number(this.monto().replace(',', '.'));
    if (!f) return this.errorForm.set('Adjunte la foto o el PDF del comprobante.');
    if (!(monto > 0)) return this.errorForm.set('Escriba el monto que pagó.');
    const d = this.destinos().find((x) => x.clave === this.destino());
    const datos = new FormData();
    datos.append('file', f);
    datos.append('amount', monto.toFixed(2));
    datos.append('paid_on', this.fecha());
    if (this.referencia().trim()) datos.append('reference', this.referencia().trim());
    if (this.nota().trim()) datos.append('note', this.nota().trim());
    if (d?.charge_id) datos.append('charge_id', d.charge_id);
    if (d?.ortho_control_id) datos.append('ortho_control_id', d.ortho_control_id);
    this.enviando.set(true);
    this.errorForm.set(null);
    try {
      await firstValueFrom(this.comms.sendPortalReceipt(this.token, datos));
      this.cerrarPago();
      this.enviado.set(true);
      await this.cargar();
    } catch (err) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.errorForm.set(typeof detail === 'string' ? detail : 'No se pudo enviar. Intente de nuevo.');
    } finally {
      this.enviando.set(false);
    }
  }
}
