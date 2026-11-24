import { HttpErrorResponse } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import {
  ACCOUNT_TYPE_LABEL,
  AccountType,
  PaymentAccount,
  PaymentAccountFields,
  PaymentAccountsService,
} from '../../../core/services/payment-accounts.service';
import { confirmAction } from '../../../shared/confirm-dialog/confirm-dialog.component';
import { openPaymentInfo } from '../../../shared/payment-info/payment-info-dialog.component';

function error(e: unknown): string {
  if (e instanceof HttpErrorResponse) {
    const d = e.error?.detail;
    if (typeof d === 'string') return d;
    if (Array.isArray(d) && d[0]?.msg) return String(d[0].msg).replace(/^Value error, /, '');
  }
  return 'No se pudo guardar. Intente de nuevo.';
}

async function leerQr(file: File): Promise<string> {
  const url = await new Promise<string>((ok, mal) => {
    const r = new FileReader();
    r.onload = () => ok(String(r.result));
    r.onerror = () => mal(r.error);
    r.readAsDataURL(file);
  });
  const img = await new Promise<HTMLImageElement>((ok, mal) => {
    const i = new Image();
    i.onload = () => ok(i);
    i.onerror = () => mal(new Error('imagen'));
    i.src = url;
  });
  const lado = Math.max(img.width, img.height);
  if (lado <= 900 && url.length < 600_000 && /^data:image\/(png|jpeg|webp)/.test(url)) return url;
  const k = Math.min(1, 900 / lado);
  const c = document.createElement('canvas');
  c.width = Math.round(img.width * k);
  c.height = Math.round(img.height * k);
  const ctx = c.getContext('2d')!;
  ctx.fillStyle = '#fff';
  ctx.fillRect(0, 0, c.width, c.height);
  ctx.drawImage(img, 0, 0, c.width, c.height);
  const png = c.toDataURL('image/png');
  return png.length < 880_000 ? png : c.toDataURL('image/jpeg', 0.9);
}

@Component({
  selector: 'app-payment-account-dialog',
  standalone: true,
  imports: [FormsModule, MatButtonModule, MatDialogModule, MatFormFieldModule, MatIconModule, MatInputModule, MatSelectModule, MatSlideToggleModule],
  template: `
    <h2 mat-dialog-title>{{ data ? 'Editar ' + data.label : 'Agregar datos de pago' }}</h2>
    <mat-dialog-content>
      <div class="cuerpo">
        <div class="qr">
          <span class="titulo">Código QR (opcional)</span>
          @if (f.qr_data) {
            <img [src]="f.qr_data" alt="Código QR" />
            <div class="botones">
              <label mat-stroked-button class="boton-archivo"><mat-icon>image</mat-icon>Cambiar
                <input type="file" accept="image/png,image/jpeg,image/webp" (change)="elegir($event)" hidden />
              </label>
              <button mat-button type="button" class="peligro" (click)="f.qr_data = null">Quitar</button>
            </div>
          } @else {
            <label class="zona">
              <mat-icon>qr_code_2</mat-icon>
              <strong>{{ leyendo() ? 'Leyendo…' : 'Subir la foto del QR' }}</strong>
              <span>La imagen que te da tu banco, DeUna, PayPhone u otro (PNG o JPG).</span>
              <input type="file" accept="image/png,image/jpeg,image/webp" (change)="elegir($event)" hidden />
            </label>
          }
        </div>
        <div class="dialog-grid">
          <mat-form-field appearance="outline" class="full">
            <mat-label>Banco o medio de pago</mat-label>
            <input matInput [(ngModel)]="f.label" maxlength="80" placeholder="Ej.: Banco Pichincha, DeUna" cdkFocusInitial />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Tipo de cuenta</mat-label>
            <mat-select [(ngModel)]="f.account_type">
              <mat-option [value]="null">—</mat-option>
              @for (t of tipos; track t[0]) { <mat-option [value]="t[0]">{{ t[1] }}</mat-option> }
            </mat-select>
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Número de cuenta</mat-label>
            <input matInput [(ngModel)]="f.account_number" maxlength="40" inputmode="numeric" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Titular</mat-label>
            <input matInput [(ngModel)]="f.holder_name" maxlength="150" />
          </mat-form-field>
          <mat-form-field appearance="outline">
            <mat-label>Cédula o RUC del titular</mat-label>
            <input matInput [(ngModel)]="f.holder_id" maxlength="20" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Correo (opcional)</mat-label>
            <input matInput type="email" [(ngModel)]="f.email" maxlength="200" />
          </mat-form-field>
          <mat-form-field appearance="outline" class="full">
            <mat-label>Nota para el paciente (opcional)</mat-label>
            <input matInput [(ngModel)]="f.note" maxlength="300" placeholder="Ej.: Envíe el comprobante por WhatsApp" />
          </mat-form-field>
          <div class="full activa">
            <span>Mostrar a pacientes y al cobrar</span>
            <mat-slide-toggle [(ngModel)]="f.is_active" />
          </div>
        </div>
      </div>
      @if (err()) { <p class="err">{{ err() }}</p> }
    </mat-dialog-content>
    <mat-dialog-actions align="end">
      <button mat-button mat-dialog-close>Cancelar</button>
      <button mat-flat-button (click)="guardar()" [disabled]="guardando() || !f.label?.trim()">Guardar</button>
    </mat-dialog-actions>
  `,
  styles: [
    `
      .cuerpo { display: grid; grid-template-columns: 240px 1fr; gap: 18px; align-items: start; }
      .qr { display: grid; gap: 8px; justify-items: center;
        .titulo { justify-self: start; font-size: .74rem; font-weight: 600; color: var(--color-ink-soft); }
        img { width: 100%; padding: 8px; background: #fff; border-radius: 14px; box-shadow: var(--shadow-sm); image-rendering: pixelated; } }
      .botones { display: flex; gap: 6px; }
      .boton-archivo { display: inline-flex; align-items: center; gap: 4px; cursor: pointer; }
      .zona { display: grid; justify-items: center; gap: 6px; width: 100%; padding: 26px 12px; text-align: center; cursor: pointer; box-sizing: border-box;
        border: 2px dashed var(--color-border-strong); border-radius: var(--radius-lg);
        mat-icon { font-size: 44px; width: 44px; height: 44px; color: var(--color-primary); }
        span { font-size: .76rem; color: var(--color-ink-faint); }
        &:hover { border-color: var(--color-primary); background: var(--color-primary-soft); } }
      .activa { display: flex; align-items: center; justify-content: space-between; font-size: .86rem; }
      .peligro { color: var(--color-danger); }
      .err { color: var(--color-danger); font-size: .84rem; margin: 8px 0 0; }
      @media (max-width: 640px) { .cuerpo { grid-template-columns: 1fr; } .qr img { max-width: 240px; } }
    `,
  ],
})
export class PaymentAccountDialogComponent {
  readonly data = inject<PaymentAccount | null>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<PaymentAccountDialogComponent, PaymentAccount>);
  private readonly api = inject(PaymentAccountsService);
  readonly tipos = Object.entries(ACCOUNT_TYPE_LABEL) as [AccountType, string][];
  readonly leyendo = signal(false);
  readonly guardando = signal(false);
  readonly err = signal<string | null>(null);

  f: PaymentAccountFields = {
    label: this.data?.label ?? '',
    qr_data: this.data?.qr_data ?? null,
    holder_name: this.data?.holder_name ?? '',
    holder_id: this.data?.holder_id ?? '',
    account_type: this.data?.account_type ?? null,
    account_number: this.data?.account_number ?? '',
    email: this.data?.email ?? '',
    note: this.data?.note ?? '',
    is_active: this.data?.is_active ?? true,
  };

  async elegir(ev: Event): Promise<void> {
    const input = ev.target as HTMLInputElement;
    const file = input.files?.[0];
    input.value = '';
    if (!file) return;
    this.leyendo.set(true);
    this.err.set(null);
    try {
      this.f.qr_data = await leerQr(file);
    } catch {
      this.err.set('No se pudo leer la imagen. Use una foto PNG o JPG.');
    } finally {
      this.leyendo.set(false);
    }
  }

  async guardar(): Promise<void> {
    const t = (v?: string | null) => (v ?? '').trim() || null;
    const body: PaymentAccountFields = {
      label: (this.f.label ?? '').trim(),
      qr_data: this.f.qr_data ?? null,
      holder_name: t(this.f.holder_name),
      holder_id: t(this.f.holder_id),
      account_type: this.f.account_type ?? null,
      account_number: t(this.f.account_number),
      email: t(this.f.email),
      note: t(this.f.note),
      is_active: this.f.is_active ?? true,
    };
    if (!body.qr_data && !body.account_number && !body.email) {
      this.err.set('Sube el código QR o escribe los datos de la cuenta.');
      return;
    }
    this.guardando.set(true);
    this.err.set(null);
    try {
      this.ref.close(await firstValueFrom(this.data ? this.api.update(this.data.id, body) : this.api.create(body)));
    } catch (e) {
      this.err.set(error(e));
    } finally {
      this.guardando.set(false);
    }
  }
}

@Component({
  selector: 'app-payment-accounts',
  standalone: true,
  imports: [MatButtonModule, MatIconModule, MatSlideToggleModule, MatTooltipModule],
  template: `
    <div class="page">
      <header class="page-header">
        <div>
          <h1>Datos de pago</h1>
          <p class="page-sub">Tus bancos con su código QR y los datos para transferir. Se muestran al cobrar, en el portal del paciente y se envían por WhatsApp.</p>
        </div>
        <div class="acciones">
          @if (cuentas().length) {
            <button mat-stroked-button (click)="vistaPrevia()"><mat-icon>visibility</mat-icon>Ver como el paciente</button>
          }
          <button mat-flat-button (click)="abrir()"><mat-icon>add</mat-icon>Agregar banco o QR</button>
        </div>
      </header>

      @if (cargando()) {
        <p class="muted">Cargando…</p>
      } @else if (!cuentas().length) {
        <div class="vacio glass-card">
          <mat-icon>qr_code_2</mat-icon>
          <strong>Aún no tienes datos de pago</strong>
          <span>Sube la foto del QR de tu banco (Pichincha, Guayaquil, DeUna, PayPhone…) y/o escribe tu número de cuenta. Así el paciente te paga desde su celular.</span>
          <button mat-flat-button (click)="abrir()"><mat-icon>add</mat-icon>Agregar el primero</button>
        </div>
      } @else {
        <div class="lista">
          @for (a of cuentas(); track a.id; let i = $index; let ultimo = $last) {
            <article class="glass-card cuenta" [class.oculta]="!a.is_active">
              <div class="qr">
                @if (a.qr_data) { <img [src]="a.qr_data" alt="QR" /> } @else { <mat-icon>account_balance</mat-icon> }
              </div>
              <div class="datos">
                <h3>{{ a.label }} @if (!a.is_active) { <span class="tag">Oculta</span> }</h3>
                @if (a.account_number) { <p>{{ a.account_type ? tipo[a.account_type] : 'Cuenta' }} · {{ a.account_number }}</p> }
                @if (a.holder_name) { <p>{{ a.holder_name }}{{ a.holder_id ? ' · ' + a.holder_id : '' }}</p> }
                @if (a.email) { <p>{{ a.email }}</p> }
                @if (a.note) { <p class="nota">{{ a.note }}</p> }
                @if (!a.qr_data) { <p class="muted">Sin código QR</p> }
              </div>
              <div class="botones">
                <button mat-icon-button (click)="mover(i, -1)" [disabled]="i === 0" matTooltip="Subir"><mat-icon>arrow_upward</mat-icon></button>
                <button mat-icon-button (click)="mover(i, 1)" [disabled]="ultimo" matTooltip="Bajar"><mat-icon>arrow_downward</mat-icon></button>
                <mat-slide-toggle [checked]="a.is_active" (change)="activar(a, $event.checked)" matTooltip="Mostrar u ocultar" />
                <button mat-icon-button (click)="abrir(a)" matTooltip="Editar"><mat-icon>edit</mat-icon></button>
                <button mat-icon-button class="peligro" (click)="eliminar(a)" matTooltip="Eliminar"><mat-icon>delete</mat-icon></button>
              </div>
            </article>
          }
        </div>
      }
    </div>
  `,
  styles: [
    `
      .page { display: grid; gap: 16px; }
      .acciones { display: flex; flex-wrap: wrap; gap: 8px; }
      .lista { display: grid; gap: 12px; }
      .cuenta { display: grid; grid-template-columns: 110px 1fr auto; gap: 16px; align-items: center; padding: 14px 16px; }
      .cuenta.oculta { opacity: .6; }
      .qr { display: grid; place-items: center; width: 110px; height: 110px; border-radius: 14px; background: #fff; box-shadow: var(--shadow-sm); overflow: hidden;
        img { width: 100%; height: 100%; object-fit: contain; padding: 6px; box-sizing: border-box; image-rendering: pixelated; }
        mat-icon { font-size: 40px; width: 40px; height: 40px; color: var(--color-ink-faint); } }
      h3 { display: flex; align-items: center; gap: 8px; margin: 0 0 4px; font-size: 1rem; }
      p { margin: 2px 0; font-size: .86rem; }
      .nota { color: var(--color-ink-soft); font-style: italic; }
      .muted { color: var(--color-ink-faint); }
      .tag { padding: 1px 8px; border-radius: 999px; font-size: .66rem; background: var(--color-surface-muted); color: var(--color-ink-soft); }
      .botones { display: flex; align-items: center; gap: 2px; }
      .peligro { color: var(--color-danger); }
      .vacio { display: grid; justify-items: center; gap: 8px; padding: 40px 18px; text-align: center;
        mat-icon { font-size: 46px; width: 46px; height: 46px; color: var(--color-primary); }
        span { max-width: 480px; font-size: .86rem; color: var(--color-ink-faint); } }
      @media (max-width: 720px) { .cuenta { grid-template-columns: 80px 1fr; } .qr { width: 80px; height: 80px; } .botones { grid-column: 1 / -1; justify-content: flex-end; } }
    `,
  ],
})
export class PaymentAccountsComponent implements OnInit {
  private readonly api = inject(PaymentAccountsService);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);
  readonly cuentas = signal<PaymentAccount[]>([]);
  readonly cargando = signal(true);
  readonly tipo = ACCOUNT_TYPE_LABEL;

  async ngOnInit(): Promise<void> {
    await this.cargar();
  }

  private async cargar(): Promise<void> {
    try {
      this.cuentas.set(await firstValueFrom(this.api.list(true)));
    } finally {
      this.cargando.set(false);
    }
  }

  async abrir(a?: PaymentAccount): Promise<void> {
    const ref = this.dialog.open(PaymentAccountDialogComponent, {
      data: a ?? null,
      width: '760px',
      maxWidth: '96vw',
      panelClass: 'app-dialog',
    });
    if (await firstValueFrom(ref.afterClosed())) {
      this.snack.open(a ? 'Datos de pago actualizados.' : 'Datos de pago agregados.', undefined, { duration: 2200 });
      await this.cargar();
    }
  }

  async activar(a: PaymentAccount, activa: boolean): Promise<void> {
    try {
      await firstValueFrom(this.api.update(a.id, { is_active: activa }));
      await this.cargar();
    } catch (e) {
      this.snack.open(error(e), 'Cerrar', { duration: 4000 });
    }
  }

  async mover(i: number, d: number): Promise<void> {
    const l = [...this.cuentas()];
    [l[i], l[i + d]] = [l[i + d], l[i]];
    this.cuentas.set(l);
    try {
      this.cuentas.set(await firstValueFrom(this.api.reorder(l.map((x) => x.id))));
    } catch {
      await this.cargar();
    }
  }

  async eliminar(a: PaymentAccount): Promise<void> {
    const ok = await confirmAction(this.dialog, {
      title: `¿Eliminar ${a.label}?`,
      message: 'Dejará de mostrarse al cobrar y en el portal. Si solo quieres dejar de mostrarla un tiempo, ocúltala.',
      confirmLabel: 'Eliminar',
      danger: true,
    });
    if (!ok) return;
    await firstValueFrom(this.api.remove(a.id));
    await this.cargar();
  }

  vistaPrevia(): void {
    openPaymentInfo(this.dialog, { patientName: 'Paciente de ejemplo', amount: 30, concept: 'cuota' });
  }
}
