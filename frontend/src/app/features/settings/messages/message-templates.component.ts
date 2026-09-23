import { Component, OnInit, TemplateRef, ViewChild, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { MessageChannel, MessageTemplate } from '../../../core/models/communication.models';
import { CommunicationService } from '../../../core/services/communication.service';

/** Variables que el servidor sabe rellenar (ver _placeholders en messaging). */
const PLACEHOLDERS = [
  { key: '{paciente}', label: 'Nombre del paciente' },
  { key: '{nombre_completo}', label: 'Nombre y apellido' },
  { key: '{clinica}', label: 'Nombre de la clínica' },
  { key: '{fecha}', label: 'Fecha de la cita' },
  { key: '{hora}', label: 'Hora de la cita' },
];

const EXAMPLE: Record<string, string> = {
  '{paciente}': 'Lucía',
  '{nombre_completo}': 'Lucía Arce',
  '{clinica}': 'su clínica',
  '{fecha}': '27/09/2026',
  '{hora}': '11:00',
};

@Component({
  selector: 'app-message-templates',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
  ],
  template: `
    <div class="page">
      <header class="page-header">
        <div>
          <h1>Plantillas de mensajes</h1>
          <p class="page-sub">Los textos de recordatorios y avisos que reciben los pacientes</p>
        </div>
        <button mat-flat-button (click)="open()">
          <mat-icon>add</mat-icon>
          Nueva plantilla
        </button>
      </header>

      <div class="grid">
        @for (t of templates(); track t.id) {
          <article class="glass-card template" [class.off]="!t.is_active">
            <div class="head">
              <div>
                <h2>{{ t.name }}</h2>
                <span class="meta">{{ t.channel === 'email' ? 'Correo' : 'WhatsApp' }} · {{ t.code }}</span>
              </div>
              <span class="status-pill" [class.off]="!t.is_active">{{ t.is_active ? 'Activa' : 'Inactiva' }}</span>
            </div>
            <p class="bubble">{{ preview(t.body) }}</p>
            <div class="actions">
              <button mat-button (click)="open(t)">
                <mat-icon>edit</mat-icon>
                Editar
              </button>
              <button mat-button [color]="t.is_active ? 'warn' : 'primary'" (click)="toggle(t)">
                {{ t.is_active ? 'Desactivar' : 'Activar' }}
              </button>
            </div>
          </article>
        } @empty {
          <p class="muted">No hay plantillas todavía.</p>
        }
      </div>
    </div>

    <ng-template #formDialog>
      <h2 mat-dialog-title>{{ editing() ? 'Editar plantilla' : 'Nueva plantilla' }}</h2>
      <form [formGroup]="form" (ngSubmit)="save()">
        <mat-dialog-content>
          <div class="dialog-grid">
            <mat-form-field appearance="outline">
              <mat-label>Nombre</mat-label>
              <input matInput formControlName="name" />
              <mat-error>Obligatorio</mat-error>
            </mat-form-field>
            <mat-form-field appearance="outline">
              <mat-label>Canal</mat-label>
              <mat-select formControlName="channel">
                <mat-option value="whatsapp">WhatsApp</mat-option>
                <mat-option value="email">Correo</mat-option>
              </mat-select>
            </mat-form-field>
            <mat-form-field appearance="outline" class="full">
              <mat-label>Texto</mat-label>
              <textarea matInput formControlName="body" rows="5" #bodyInput></textarea>
              <mat-error>Escriba el mensaje</mat-error>
            </mat-form-field>
          </div>
          <p class="hint">Toque una variable para insertarla donde está el cursor:</p>
          <div class="chips">
            @for (p of placeholders; track p.key) {
              <button type="button" class="chip" (click)="insert(bodyInput, p.key)" [title]="p.label">{{ p.key }}</button>
            }
          </div>
          <p class="hint">Así lo verá el paciente:</p>
          <p class="bubble">{{ preview(form.controls.body.value) }}</p>
        </mat-dialog-content>
        <mat-dialog-actions align="end">
          <button mat-button type="button" mat-dialog-close>Cancelar</button>
          <button mat-flat-button type="submit" [disabled]="saving()">
            {{ saving() ? 'Guardando…' : 'Guardar' }}
          </button>
        </mat-dialog-actions>
      </form>
    </ng-template>
  `,
  styles: [
    `
      .page { display: grid; gap: 16px; }
      .grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }
      .template { padding: 18px 20px 10px; display: flex; flex-direction: column; gap: 10px; }
      .template.off { opacity: 0.6; }
      .head { display: flex; justify-content: space-between; align-items: flex-start; gap: 10px; }
      .head h2 { margin: 0; font-size: 1rem; }
      .meta { font-size: 0.76rem; color: var(--color-ink-faint); }
      .bubble {
        margin: 0; padding: 10px 14px; border-radius: 16px 16px 16px 4px; white-space: pre-line;
        background: color-mix(in srgb, #25d366 14%, var(--color-surface)); font-size: 0.86rem; line-height: 1.5;
      }
      .actions { display: flex; justify-content: flex-end; border-top: 1px solid var(--color-border); padding-top: 4px; }
      .hint { margin: 8px 0 6px; font-size: 0.78rem; color: var(--color-ink-faint); }
      .chips { display: flex; flex-wrap: wrap; gap: 6px; }
      .chip {
        padding: 4px 10px; border-radius: 999px; border: 1px solid var(--color-border-strong);
        background: var(--glass-field-bg); font: inherit; font-size: 0.78rem; cursor: pointer; color: var(--color-primary);
      }
      .chip:hover { background: var(--color-primary-soft); }
      .muted { color: var(--color-ink-faint); }
    `,
  ],
})
export class MessageTemplatesComponent implements OnInit {
  private readonly comms = inject(CommunicationService);
  private readonly fb = inject(FormBuilder);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);

  @ViewChild('formDialog') formDialog!: TemplateRef<unknown>;
  private ref: MatDialogRef<unknown> | null = null;

  readonly templates = signal<MessageTemplate[]>([]);
  readonly editing = signal<MessageTemplate | null>(null);
  readonly saving = signal(false);
  readonly placeholders = PLACEHOLDERS;

  readonly form = this.fb.nonNullable.group({
    name: ['', Validators.required],
    channel: ['whatsapp' as MessageChannel],
    body: ['', Validators.required],
  });

  readonly codes = computed(() => new Set(this.templates().map((t) => t.code)));

  async ngOnInit(): Promise<void> {
    await this.reload();
  }

  private async reload(): Promise<void> {
    this.templates.set(await firstValueFrom(this.comms.getTemplates()));
  }

  preview(body: string): string {
    return Object.entries(EXAMPLE).reduce((text, [key, value]) => text.split(key).join(value), body || '');
  }

  insert(textarea: HTMLTextAreaElement, key: string): void {
    const control = this.form.controls.body;
    const start = textarea.selectionStart ?? control.value.length;
    const end = textarea.selectionEnd ?? start;
    control.setValue(control.value.slice(0, start) + key + control.value.slice(end));
    queueMicrotask(() => {
      textarea.focus();
      textarea.setSelectionRange(start + key.length, start + key.length);
    });
  }

  open(template: MessageTemplate | null = null): void {
    this.editing.set(template);
    this.form.reset({
      name: template?.name ?? '',
      channel: template?.channel ?? 'whatsapp',
      body: template?.body ?? '',
    });
    this.ref = this.dialog.open(this.formDialog, { width: '640px', maxWidth: '96vw', panelClass: 'app-dialog' });
  }

  /** El código identifica la plantilla (el servidor la guarda por código). */
  private codeFor(name: string): string {
    const base =
      name
        .normalize('NFD')
        .replace(/[\u0300-\u036f]/g, '')
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '_')
        .replace(/^_|_$/g, '') || 'plantilla';
    let code = base;
    let n = 2;
    while (this.codes().has(code)) code = `${base}_${n++}`;
    return code;
  }

  async save(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    const v = this.form.getRawValue();
    const editing = this.editing();
    try {
      await firstValueFrom(
        this.comms.saveTemplate({
          code: editing?.code ?? this.codeFor(v.name),
          name: v.name.trim(),
          channel: v.channel,
          body: v.body,
          is_active: editing?.is_active ?? true,
        }),
      );
      this.ref?.close();
      this.snackBar.open('Plantilla guardada', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch {
      this.snackBar.open('No se pudo guardar la plantilla', 'Cerrar', { duration: 4000 });
    } finally {
      this.saving.set(false);
    }
  }

  async toggle(t: MessageTemplate): Promise<void> {
    const { id, ...rest } = t;
    await firstValueFrom(this.comms.saveTemplate({ ...rest, is_active: !t.is_active }));
    await this.reload();
  }
}
