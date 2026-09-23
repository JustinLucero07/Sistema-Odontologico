import { DatePipe } from '@angular/common';
import { Component, Input, OnChanges, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import {
  AccessEntry,
  CONSENT_METHOD_LABELS,
  LegalService,
  PrivacyStatus,
} from '../../core/services/legal.service';
import { printPrivacyNotice } from '../print/privacy-print';
import { openRecordConsent } from './record-consent-dialog.component';

const ACTION_LABELS: Record<string, string> = {
  view: 'Abrió la ficha',
  export: 'Exportó sus datos',
  grant: 'Registró una autorización',
  revoke: 'Registró un retiro de autorización',
  update: 'Modificó sus datos',
  create: 'Registró al paciente',
  delete: 'Dio de baja al paciente',
};

/**
 * Protección de datos del paciente, en su ficha: qué se le informó, qué
 * autorizó, quién ha visto su historia, y la copia de sus datos si la pide.
 */
@Component({
  selector: 'app-patient-privacy-card',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatIconModule, MatTooltipModule],
  template: `
    <section class="glass-card privacy">
      <header>
        <span class="icon"><mat-icon>verified_user</mat-icon></span>
        <div>
          <h2>Protección de datos</h2>
          <p>Lo que se informó al paciente y lo que autorizó</p>
        </div>
      </header>

      @if (status(); as s) {
        <div class="rows">
          <div class="row">
            <div class="row-text">
              <strong>Aviso de privacidad</strong>
              @if (s.privacy_notice; as n) {
                <span>
                  Entregado el {{ n.recorded_at | date: 'd MMM y' }} · {{ methodLabel(n.method) }}
                  @if (n.signed_by_name) { · firmó {{ n.signed_by_name }} }
                  @if (n.recorded_by_name) { · registró {{ n.recorded_by_name }} }
                </span>
              } @else {
                <span class="warn-text">Sin constancia: la ley exige informar al paciente.</span>
              }
            </div>
            @if (!s.privacy_notice) {
              <span class="pill warn">Pendiente</span>
            } @else if (s.notice_outdated) {
              <span class="pill warn" matTooltip="El aviso cambió desde que se entregó">Versión anterior</span>
            } @else {
              <span class="pill ok">Entregado</span>
            }
            @if (canWrite && (!s.privacy_notice || s.notice_outdated)) {
              <button mat-stroked-button (click)="recordNotice()">Registrar entrega</button>
            }
          </div>

          <div class="row">
            <div class="row-text">
              <strong>Recordatorios y mensajes</strong>
              @if (s.communications; as c) {
                <span>
                  {{ c.granted ? 'Autorizó' : 'Retiró la autorización' }} el {{ c.recorded_at | date: 'd MMM y' }}
                  · {{ methodLabel(c.method) }}
                </span>
              } @else {
                <span>Sin decisión registrada: solo recibe recordatorios de sus citas.</span>
              }
            </div>
            @if (s.communications?.granted === false) {
              <span class="pill off">No autoriza</span>
            } @else if (s.communications?.granted) {
              <span class="pill ok">Autorizado</span>
            }
            @if (canWrite) {
              @if (s.communications?.granted) {
                <button mat-button color="warn" (click)="setCommunications(false)">Retirar</button>
              } @else {
                <button mat-stroked-button (click)="setCommunications(true)">Autorizar</button>
              }
            }
          </div>
        </div>

        <div class="actions">
          <button mat-button (click)="printNotice()">
            <mat-icon>print</mat-icon>
            Imprimir aviso
          </button>
          @if (canExport) {
            <button mat-button (click)="exportData()" [disabled]="exporting()"
                    matTooltip="Derecho de acceso y portabilidad: copia completa en formato legible">
              <mat-icon>download</mat-icon>
              {{ exporting() ? 'Preparando…' : 'Exportar sus datos' }}
            </button>
          }
          @if (canAudit) {
            <button mat-button (click)="toggleAccess()">
              <mat-icon>visibility</mat-icon>
              {{ accessOpen() ? 'Ocultar accesos' : 'Quién vio esta ficha' }}
            </button>
          }
          @if (s.history.length > 0) {
            <button mat-button (click)="historyOpen.set(!historyOpen())">
              <mat-icon>history</mat-icon>
              Historial ({{ s.history.length }})
            </button>
          }
        </div>

        @if (historyOpen()) {
          <ul class="log">
            @for (h of s.history; track h.id) {
              <li>
                <span class="when">{{ h.recorded_at | date: 'd MMM y, HH:mm' }}</span>
                <span>
                  {{ h.kind === 'aviso_privacidad' ? 'Aviso entregado' : (h.granted ? 'Autorizó mensajes' : 'Retiró mensajes') }}
                  · v{{ h.policy_version }} · {{ methodLabel(h.method) }}
                  @if (h.recorded_by_name) { · {{ h.recorded_by_name }} }
                </span>
              </li>
            }
          </ul>
        }

        @if (accessOpen()) {
          <ul class="log">
            @for (a of access(); track $index) {
              <li>
                <span class="when">{{ a.at | date: 'd MMM y, HH:mm' }}</span>
                <span>{{ a.user_name || 'Sistema' }} · {{ actionLabel(a.action) }}</span>
              </li>
            } @empty {
              <li class="empty">Sin accesos registrados.</li>
            }
          </ul>
        }
      }
    </section>
  `,
  styles: [
    `
      .privacy { padding: 18px 20px; display: grid; gap: 12px; }
      header { display: flex; gap: 12px; align-items: center; }
      header h2 { margin: 0; font-size: 1rem; }
      header p { margin: 0; font-size: 0.8rem; color: var(--color-ink-faint); }
      .icon {
        display: inline-flex; align-items: center; justify-content: center; flex-shrink: 0;
        width: 38px; height: 38px; border-radius: 12px;
        background: var(--color-primary-soft); color: var(--color-primary);
      }
      .rows { display: grid; gap: 2px; }
      .row {
        display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
        padding: 10px 0; border-top: 1px solid var(--color-border);
      }
      .row-text { flex: 1 1 260px; display: grid; min-width: 0; }
      .row-text strong { font-size: 0.88rem; }
      .row-text span { font-size: 0.78rem; color: var(--color-ink-faint); }
      .warn-text { color: var(--color-danger) !important; }
      .pill {
        padding: 3px 10px; border-radius: 999px; font-size: 0.72rem; font-weight: 700; white-space: nowrap;
        &.ok { background: var(--color-success-soft); color: var(--color-success); }
        &.warn { background: var(--color-danger-soft); color: var(--color-danger); }
        &.off { background: var(--color-surface-muted); color: var(--color-ink-soft); }
      }
      .actions { display: flex; flex-wrap: wrap; gap: 4px; margin: 0 -8px; }
      .log {
        list-style: none; margin: 0; padding: 8px 12px; max-height: 240px; overflow-y: auto;
        border-radius: var(--radius-sm); background: var(--color-surface-muted);
        li { display: flex; gap: 12px; padding: 5px 0; font-size: 0.8rem; border-bottom: 1px solid var(--color-border); }
        li:last-child { border-bottom: none; }
        .when { flex-shrink: 0; width: 132px; color: var(--color-ink-faint); font-variant-numeric: tabular-nums; }
        .empty { color: var(--color-ink-faint); }
      }
    `,
  ],
})
export class PatientPrivacyCardComponent implements OnChanges {
  @Input({ required: true }) patientId!: string;
  @Input({ required: true }) patientName!: string;
  @Input() patientAge: number | null = null;

  private readonly legal = inject(LegalService);
  private readonly auth = inject(AuthService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);

  readonly status = signal<PrivacyStatus | null>(null);
  readonly access = signal<AccessEntry[]>([]);
  readonly accessOpen = signal(false);
  readonly historyOpen = signal(false);
  readonly exporting = signal(false);

  readonly canWrite = this.auth.hasPermission('patients:write');
  readonly canExport = this.auth.hasPermission('patients:export');
  readonly canAudit = this.auth.hasPermission('audit:read');
  readonly minor = computed(() => this.patientAge !== null && this.patientAge < 18);

  async ngOnChanges(): Promise<void> {
    await this.reload();
  }

  private async reload(): Promise<void> {
    this.status.set(await firstValueFrom(this.legal.getPrivacy(this.patientId)));
    if (this.accessOpen()) this.access.set(await firstValueFrom(this.legal.getAccessLog(this.patientId)));
  }

  methodLabel(method: string): string {
    return CONSENT_METHOD_LABELS[method as keyof typeof CONSENT_METHOD_LABELS] ?? method;
  }

  actionLabel(action: string): string {
    return ACTION_LABELS[action] ?? action;
  }

  async recordNotice(): Promise<void> {
    const result = await openRecordConsent(this.dialog, {
      title: 'Registrar entrega del aviso',
      message: 'Deja constancia de que se informó al paciente cómo se tratan sus datos, con la versión vigente del aviso.',
      confirmLabel: 'Registrar',
      minor: this.patientAge !== null && this.patientAge < 18,
    });
    if (!result) return;
    await this.save({ kind: 'aviso_privacidad', ...result }, 'Entrega del aviso registrada');
  }

  async setCommunications(granted: boolean): Promise<void> {
    const result = await openRecordConsent(this.dialog, {
      title: granted ? 'Autorizar mensajes' : 'Retirar autorización',
      message: granted
        ? 'El paciente autoriza recibir recordatorios y mensajes por WhatsApp o correo.'
        : 'El paciente ya no quiere recibir mensajes. Desde ahora no se le enviará ninguno, ni siquiera recordatorios.',
      confirmLabel: granted ? 'Autorizar' : 'Retirar',
      minor: this.patientAge !== null && this.patientAge < 18,
    });
    if (!result) return;
    await this.save(
      { kind: 'comunicaciones', granted, ...result },
      granted ? 'Autorización registrada' : 'Autorización retirada: no recibirá mensajes',
    );
  }

  private async save(payload: Parameters<LegalService['recordConsent']>[1], message: string): Promise<void> {
    try {
      await firstValueFrom(this.legal.recordConsent(this.patientId, payload));
      this.snackBar.open(message, 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.snackBar.open(typeof detail === 'string' ? detail : 'No se pudo registrar', 'Cerrar', { duration: 4000 });
    }
  }

  async printNotice(): Promise<void> {
    printPrivacyNotice(await firstValueFrom(this.legal.getController()), this.patientName);
  }

  async toggleAccess(): Promise<void> {
    this.accessOpen.set(!this.accessOpen());
    if (this.accessOpen()) this.access.set(await firstValueFrom(this.legal.getAccessLog(this.patientId)));
  }

  async exportData(): Promise<void> {
    this.exporting.set(true);
    try {
      const blob = await firstValueFrom(this.legal.exportPatient(this.patientId));
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      link.download = `datos-${this.patientName.replace(/\s+/g, '-').toLowerCase()}.json`;
      link.click();
      URL.revokeObjectURL(url);
      this.snackBar.open('Copia de datos descargada. La descarga queda registrada.', 'Cerrar', { duration: 4000 });
      if (this.accessOpen()) this.access.set(await firstValueFrom(this.legal.getAccessLog(this.patientId)));
    } catch {
      this.snackBar.open('No se pudo exportar', 'Cerrar', { duration: 4000 });
    } finally {
      this.exporting.set(false);
    }
  }
}
