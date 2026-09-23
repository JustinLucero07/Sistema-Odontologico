import { Component, computed, inject, signal } from '@angular/core';
import { toSignal } from '@angular/core/rxjs-interop';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';

import { AuthService } from '../../core/auth/auth.service';
import { LegalService } from '../../core/services/legal.service';
import { confidentialityAgreement, privacyNotice } from '../../shared/legal/legal-texts';
import { printConfidentialityAgreement, printPrivacyNotice } from '../../shared/print/privacy-print';

type Doc = 'privacidad' | 'confidencialidad';

@Component({
  selector: 'app-legal-page',
  standalone: true,
  imports: [MatButtonModule, MatIconModule],
  template: `
    <div class="page">
      <header class="page-header">
        <div>
          <h1>Privacidad y legal</h1>
          <p class="page-sub">Los textos que la clínica entrega a pacientes y personal</p>
        </div>
      </header>

      <div class="segmented" role="tablist">
        <button role="tab" [class.on]="doc() === 'privacidad'" [attr.aria-selected]="doc() === 'privacidad'"
                (click)="doc.set('privacidad')">
          <mat-icon>policy</mat-icon> Aviso de privacidad
        </button>
        <button role="tab" [class.on]="doc() === 'confidencialidad'" [attr.aria-selected]="doc() === 'confidencialidad'"
                (click)="doc.set('confidencialidad')">
          <mat-icon>shield_person</mat-icon> Acuerdo de confidencialidad
        </button>
      </div>

      <div class="layout">
        <article class="glass-card document">
          @if (controller(); as c) {
            <div class="doc-head">
              <div>
                <h2>{{ doc() === 'privacidad' ? 'Aviso de privacidad' : 'Acuerdo de confidencialidad' }}</h2>
                <span class="version">
                  Versión {{ doc() === 'privacidad' ? c.privacy_policy_version : c.confidentiality_version }}
                </span>
              </div>
              <button mat-stroked-button (click)="print()">
                <mat-icon>print</mat-icon>
                Imprimir
              </button>
            </div>
            @for (section of sections(); track section.title) {
              <section>
                <h3>{{ section.title }}</h3>
                @for (p of section.paragraphs; track $index) {
                  <p>{{ p }}</p>
                }
              </section>
            }
          } @else {
            <p class="muted">Cargando…</p>
          }
        </article>

        <aside class="glass-card notes">
          <h3><mat-icon>gavel</mat-icon> Cómo se cumple en el sistema</h3>
          <ul>
            <li><b>Informar:</b> al registrar un paciente se deja constancia de que recibió el aviso, con la versión y el método.</li>
            <li><b>Mensajes:</b> solo se envían si el paciente no los rechazó; puede retirar la autorización cuando quiera.</li>
            <li><b>Acceso y portabilidad:</b> desde la ficha se exporta una copia completa de sus datos.</li>
            <li><b>Confidencialidad:</b> cada apertura de una historia clínica queda registrada con usuario y hora.</li>
            <li><b>Conservación:</b> los registros clínicos no se borran; los errores se anulan con motivo.</li>
            <li><b>Menores:</b> se exige el nombre del representante legal.</li>
          </ul>
          <p class="disclaimer">
            <mat-icon>info</mat-icon>
            Estos textos siguen la Ley Orgánica de Protección de Datos Personales del Ecuador. Antes de usarlos,
            revíselos con su asesor legal y complete los datos de la clínica en Configuración.
          </p>
        </aside>
      </div>
    </div>
  `,
  styles: [
    `
      .page { display: grid; gap: 16px; }
      .segmented {
        display: inline-flex; gap: 4px; padding: 4px; width: fit-content; max-width: 100%;
        border-radius: 999px; background: var(--glass-card-bg);
        backdrop-filter: var(--glass-card-blur); -webkit-backdrop-filter: var(--glass-card-blur);
        border: 1px solid var(--glass-card-border); box-shadow: var(--shadow-sm);
        button {
          display: inline-flex; align-items: center; gap: 6px; padding: 8px 16px;
          border: none; border-radius: 999px; background: transparent; cursor: pointer;
          font: inherit; font-size: 0.86rem; font-weight: 600; color: var(--color-ink-soft);
          transition: background 0.18s ease, color 0.18s ease;
          mat-icon { font-size: 18px; width: 18px; height: 18px; }
          &.on { background: var(--color-primary); color: var(--color-on-primary); box-shadow: var(--shadow-sm); }
        }
      }
      .layout { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 16px; align-items: start; }
      @media (max-width: 980px) { .layout { grid-template-columns: 1fr; } }
      .document { padding: 26px 30px; max-width: 820px; }
      .doc-head { display: flex; justify-content: space-between; align-items: flex-start; gap: 12px; margin-bottom: 8px; }
      .doc-head h2 { margin: 0; font-size: 1.3rem; }
      .version { font-size: 0.78rem; color: var(--color-ink-faint); }
      section h3 { margin: 18px 0 4px; font-size: 0.95rem; color: var(--color-primary); }
      section p { margin: 0 0 8px; line-height: 1.65; color: var(--color-ink); }
      .notes { padding: 20px 22px; position: sticky; top: 84px; }
      .notes h3 { display: flex; align-items: center; gap: 8px; margin: 0 0 10px; font-size: 0.95rem; }
      .notes ul { margin: 0; padding-left: 18px; display: grid; gap: 8px; font-size: 0.84rem; line-height: 1.5; }
      .disclaimer {
        display: flex; gap: 8px; margin: 16px 0 0; padding: 10px 12px; border-radius: var(--radius-sm);
        background: var(--color-accent-soft); color: var(--color-ink); font-size: 0.8rem; line-height: 1.5;
        mat-icon { color: var(--color-accent); flex-shrink: 0; font-size: 18px; width: 18px; height: 18px; }
      }
      .muted { color: var(--color-ink-faint); }
    `,
  ],
})
export class LegalPageComponent {
  private readonly legal = inject(LegalService);
  private readonly auth = inject(AuthService);
  private readonly snackBar = inject(MatSnackBar);

  readonly doc = signal<Doc>('privacidad');
  readonly controller = toSignal(this.legal.getController());

  readonly sections = computed(() => {
    const c = this.controller();
    if (!c) return [];
    return this.doc() === 'privacidad' ? privacyNotice(c) : confidentialityAgreement(c);
  });

  print(): void {
    const c = this.controller();
    if (!c) return;
    const user = this.auth.currentUser();
    const opened =
      this.doc() === 'privacidad'
        ? printPrivacyNotice(c, null)
        : printConfidentialityAgreement(c, user ? `${user.first_name} ${user.last_name}` : '');
    if (!opened) this.snackBar.open('El navegador bloqueó la ventana de impresión', 'Cerrar', { duration: 4000 });
  }
}
