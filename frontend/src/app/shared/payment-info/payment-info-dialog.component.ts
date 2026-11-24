import { Component, OnInit, inject, signal } from '@angular/core';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { BrandingService } from '../../core/branding/branding.service';
import { formatMoney } from '../../core/models/finance.models';
import {
  ACCOUNT_TYPE_LABEL,
  PaymentAccount,
  PaymentAccountsService,
  accountText,
} from '../../core/services/payment-accounts.service';
import { whatsappUrl } from '../whatsapp';

export interface PaymentInfoData {
  patientName?: string;
  phone?: string | null;
  /** Lo que se le pide pagar (saldo o cuota). */
  amount?: string | number | null;
  concept?: string | null;
}

@Component({
  selector: 'app-payment-info-dialog',
  standalone: true,
  imports: [MatButtonModule, MatDialogModule, MatIconModule, MatTooltipModule, RouterLink],
  template: `
    <h2 mat-dialog-title>Datos de pago</h2>
    <mat-dialog-content>
      @if (data.amount && +data.amount > 0) {
        <p class="monto">
          {{ data.patientName ? data.patientName + ' · ' : '' }}{{ data.concept || 'Valor a pagar' }}:
          <strong>$ {{ money(data.amount) }}</strong>
        </p>
      }
      @if (cargando()) {
        <p class="vacio">Cargando…</p>
      } @else if (!cuentas().length) {
        <div class="vacio">
          <mat-icon>qr_code_2</mat-icon>
          <strong>Aún no hay datos de pago</strong>
          <span>Agrega el QR de tu banco o los datos de tu cuenta en Configuración › Datos de pago.</span>
          @if (puedeConfigurar) {
            <a mat-flat-button routerLink="/settings/payment-accounts" mat-dialog-close>Configurar ahora</a>
          }
        </div>
      } @else {
        <div class="cuentas">
          @for (a of cuentas(); track a.id) {
            <article class="cuenta">
              <h3>{{ a.label }}</h3>
              @if (a.qr_data) {
                <button type="button" class="qr" (click)="ampliar.set(a.qr_data)" matTooltip="Ampliar">
                  <img [src]="a.qr_data" [alt]="'Código QR de ' + a.label" />
                </button>
                <a mat-button [href]="a.qr_data" [attr.download]="'qr-' + a.label + '.png'">
                  <mat-icon>download</mat-icon>Descargar QR (para adjuntarlo en WhatsApp)
                </a>
              }
              @if (a.account_number || a.holder_name || a.email) {
                <dl>
                  @if (a.account_number) {
                    <div><dt>{{ a.account_type ? tipo[a.account_type] : 'Cuenta' }}</dt><dd>{{ a.account_number }}</dd></div>
                  }
                  @if (a.holder_name) { <div><dt>Titular</dt><dd>{{ a.holder_name }}</dd></div> }
                  @if (a.holder_id) { <div><dt>C.I. / RUC</dt><dd>{{ a.holder_id }}</dd></div> }
                  @if (a.email) { <div><dt>Correo</dt><dd>{{ a.email }}</dd></div> }
                </dl>
                <button mat-stroked-button type="button" (click)="copiar(a)"><mat-icon>content_copy</mat-icon>Copiar datos</button>
              }
              @if (a.note) { <p class="nota">{{ a.note }}</p> }
            </article>
          }
        </div>
      }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Cerrar</button>
      @if (cuentas().length) {
        <a mat-flat-button [attr.href]="wa()" target="_blank" rel="noopener" [class.desactivado]="!wa()"
           [matTooltip]="wa() ? '' : 'El paciente no tiene celular registrado'">
          <mat-icon>chat</mat-icon>Enviar por WhatsApp
        </a>
      }
    </mat-dialog-actions>

    @if (ampliar(); as src) {
      <div class="grande" (click)="ampliar.set(null)">
        <img [src]="src" alt="Código QR ampliado" />
        <span>Toque para cerrar</span>
      </div>
    }
  `,
  styles: [
    `
      .monto { margin: 0 0 12px; padding: 10px 12px; border-radius: var(--radius-md); background: var(--color-primary-soft); font-size: .9rem; }
      .cuentas { display: grid; grid-template-columns: repeat(auto-fit, minmax(230px, 1fr)); gap: 14px; }
      .cuenta { display: grid; gap: 10px; align-content: start; padding: 14px; border: 1px solid var(--color-border); border-radius: var(--radius-lg); background: var(--color-surface); }
      h3 { margin: 0; font-size: 1rem; }
      .qr { padding: 10px; border: 0; border-radius: 14px; background: #fff; cursor: zoom-in; box-shadow: var(--shadow-sm);
        img { display: block; width: 100%; max-width: 260px; margin: 0 auto; image-rendering: pixelated; } }
      dl { display: grid; gap: 6px; margin: 0; div { display: grid; } dt { font-size: .7rem; color: var(--color-ink-faint); } dd { margin: 0; font-weight: 600; font-size: .9rem; } }
      .nota { margin: 0; font-size: .8rem; color: var(--color-ink-soft); }
      .vacio { display: grid; justify-items: center; gap: 6px; padding: 24px 8px; text-align: center; color: var(--color-ink-faint);
        mat-icon { font-size: 40px; width: 40px; height: 40px; color: var(--color-primary); } strong { color: var(--color-ink); } a { margin-top: 8px; } }
      .desactivado { pointer-events: none; opacity: .5; }
      .grande { position: fixed; inset: 0; z-index: 2000; display: grid; place-items: center; align-content: center; gap: 12px;
        background: rgba(0, 0, 0, .82); cursor: zoom-out;
        img { width: min(86vw, 86vh); background: #fff; padding: 18px; border-radius: 18px; image-rendering: pixelated; }
        span { color: #fff; font-size: .85rem; } }
    `,
  ],
})
export class PaymentInfoDialogComponent implements OnInit {
  readonly data = inject<PaymentInfoData>(MAT_DIALOG_DATA);
  private readonly api = inject(PaymentAccountsService);
  private readonly snack = inject(MatSnackBar);
  private readonly branding = inject(BrandingService);
  readonly puedeConfigurar = inject(AuthService).hasPermission('settings:manage');

  readonly cuentas = signal<PaymentAccount[]>([]);
  readonly cargando = signal(true);
  readonly ampliar = signal<string | null>(null);
  readonly tipo = ACCOUNT_TYPE_LABEL;
  readonly money = formatMoney;

  async ngOnInit(): Promise<void> {
    try {
      this.cuentas.set(await firstValueFrom(this.api.list()));
    } catch {
      this.cuentas.set([]);
    } finally {
      this.cargando.set(false);
    }
  }

  private mensaje(): string {
    const d = this.data;
    const saludo = d.patientName ? `Hola ${d.patientName.split(' ')[0]}, ` : 'Hola, ';
    const monto =
      d.amount && +d.amount > 0 ? `el valor a pagar${d.concept ? ` (${d.concept})` : ''} es *$ ${formatMoney(d.amount)}*. ` : '';
    const cuerpo = this.cuentas()
      .map((a) => accountText(a) + (a.qr_data && !a.account_number ? '\n(Pago con código QR: le enviamos la imagen a continuación)' : ''))
      .join('\n\n');
    const cierre = this.cuentas().some((a) => /comprobante/i.test(a.note ?? ''))
      ? 'Gracias.'
      : 'Por favor envíenos el comprobante por este medio. Gracias.';
    return `${saludo}${monto}${monto ? 'Estos' : 'estos'} son nuestros datos de pago:\n\n${cuerpo}\n\n${cierre}\n${this.branding.name()}`;
  }

  wa(): string | null {
    return whatsappUrl(this.data.phone, this.mensaje());
  }

  async copiar(a: PaymentAccount): Promise<void> {
    try {
      await navigator.clipboard.writeText(accountText(a).replace(/\*/g, ''));
      this.snack.open('Datos copiados.', undefined, { duration: 1800 });
    } catch {
      this.snack.open('No se pudo copiar.', undefined, { duration: 1800 });
    }
  }
}

export function openPaymentInfo(dialog: MatDialog, data: PaymentInfoData = {}): void {
  dialog.open(PaymentInfoDialogComponent, { data, width: '760px', maxWidth: '96vw', panelClass: 'app-dialog', autoFocus: false });
}
