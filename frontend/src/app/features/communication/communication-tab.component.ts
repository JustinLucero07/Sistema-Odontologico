import { DatePipe } from '@angular/common';
import { Component, Input, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import {
  AiStatus,
  AiSuggestion,
  MESSAGE_STATUS_LABELS,
  MessageTemplate,
  OutboundMessage,
  PortalLink,
  ProviderStatus,
  SUGGESTION_STATUS_LABELS,
} from '../../core/models/communication.models';
import { CommunicationService } from '../../core/services/communication.service';

@Component({
  selector: 'app-communication-tab',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatTooltipModule,
  ],
  templateUrl: './communication-tab.component.html',
  styleUrl: './communication-tab.component.scss',
})
export class CommunicationTabComponent implements OnInit {
  @Input({ required: true }) patientId!: string;

  private readonly comms = inject(CommunicationService);
  private readonly snackBar = inject(MatSnackBar);
  readonly auth = inject(AuthService);

  readonly section = signal<'mensajes' | 'asistente' | 'portal'>('mensajes');
  readonly loading = signal(true);
  readonly busy = signal(false);

  readonly provider = signal<ProviderStatus | null>(null);
  readonly templates = signal<MessageTemplate[]>([]);
  readonly messages = signal<OutboundMessage[]>([]);
  readonly aiStatus = signal<AiStatus | null>(null);
  readonly suggestions = signal<AiSuggestion[]>([]);
  readonly links = signal<PortalLink[]>([]);
  /** Shown once and then forgotten — only its hash exists on the server. */
  readonly freshLink = signal<string | null>(null);
  readonly context = signal<string | null>(null);
  readonly viewing = signal<AiSuggestion | null>(null);

  readonly messageLabels = MESSAGE_STATUS_LABELS;
  readonly suggestionLabels = SUGGESTION_STATUS_LABELS;

  messageBody = '';
  chosenTemplate = '';
  suggestionKind = 'resumen_historia';
  suggestionRequest = '';

  readonly kinds = [
    { code: 'resumen_historia', label: 'Resumen de la historia clínica' },
    { code: 'borrador_mensaje', label: 'Borrador de mensaje al paciente' },
    { code: 'resumen_visita', label: 'Resumen de la visita para el paciente' },
  ];

  get canWrite(): boolean {
    return this.auth.hasPermission('appointments:write');
  }

  get canUseAi(): boolean {
    return this.auth.hasPermission('medical_history:write');
  }

  async ngOnInit(): Promise<void> {
    this.loading.set(true);
    try {
      const [provider, templates, messages, aiStatus, suggestions, links] = await Promise.all([
        firstValueFrom(this.comms.getProviderStatus()),
        firstValueFrom(this.comms.getTemplates()),
        firstValueFrom(this.comms.getMessages(this.patientId)),
        firstValueFrom(this.comms.getAiStatus()),
        firstValueFrom(this.comms.getSuggestions(this.patientId)),
        firstValueFrom(this.comms.getPortalLinks(this.patientId)),
      ]);
      this.provider.set(provider);
      this.templates.set(templates);
      this.messages.set(messages);
      this.aiStatus.set(aiStatus);
      this.suggestions.set(suggestions);
      this.links.set(links);
    } finally {
      this.loading.set(false);
    }
  }

  // ---- Messages ---------------------------------------------------------

  useTemplate(code: string): void {
    this.chosenTemplate = code;
    const template = this.templates().find((t) => t.code === code);
    // The body is copied into the box rather than sent blind, so whoever
    // presses send has read the exact words going out.
    this.messageBody = template?.body ?? '';
  }

  async send(): Promise<void> {
    if (!this.messageBody.trim() || this.busy()) return;
    this.busy.set(true);
    try {
      await firstValueFrom(
        this.comms.sendMessage({
          patient_id: this.patientId,
          channel: 'whatsapp',
          body: this.messageBody,
        }),
      );
      this.messageBody = '';
      this.chosenTemplate = '';
      this.messages.set(await firstValueFrom(this.comms.getMessages(this.patientId)));
      const live = this.provider()?.is_live;
      this.snackBar.open(
        live ? 'Mensaje enviado' : 'Mensaje registrado como simulado: no hay proveedor configurado',
        'Cerrar',
        { duration: live ? 3000 : 6000 },
      );
    } catch (error) {
      this.report(error, 'No se pudo enviar el mensaje');
    } finally {
      this.busy.set(false);
    }
  }

  // ---- Assistant --------------------------------------------------------

  async showContext(): Promise<void> {
    this.context.set(
      (await firstValueFrom(this.comms.getAiContext(this.patientId))).context,
    );
  }

  async generate(): Promise<void> {
    if (this.busy()) return;
    this.busy.set(true);
    try {
      await firstValueFrom(
        this.comms.createSuggestion(this.patientId, {
          kind: this.suggestionKind,
          request: this.suggestionRequest || null,
        }),
      );
      this.suggestionRequest = '';
      this.suggestions.set(await firstValueFrom(this.comms.getSuggestions(this.patientId)));
    } catch (error) {
      this.report(error, 'No se pudo generar el borrador');
    } finally {
      this.busy.set(false);
    }
  }

  async decide(suggestion: AiSuggestion, accept: boolean): Promise<void> {
    this.busy.set(true);
    try {
      await firstValueFrom(
        accept
          ? this.comms.acceptSuggestion(suggestion.id)
          : this.comms.discardSuggestion(suggestion.id),
      );
      this.suggestions.set(await firstValueFrom(this.comms.getSuggestions(this.patientId)));
      this.snackBar.open(
        accept
          ? 'Aceptado. El texto no se guardó en la historia: cópielo donde corresponda.'
          : 'Borrador descartado',
        'Cerrar',
        { duration: accept ? 6000 : 3000 },
      );
    } catch (error) {
      this.report(error, 'No se pudo registrar la decisión');
    } finally {
      this.busy.set(false);
    }
  }

  async copy(text: string): Promise<void> {
    try {
      await navigator.clipboard.writeText(text);
      this.snackBar.open('Copiado al portapapeles', 'Cerrar', { duration: 2500 });
    } catch {
      this.snackBar.open('El navegador no permitió copiar', 'Cerrar', { duration: 4000 });
    }
  }

  // ---- Portal -----------------------------------------------------------

  async createLink(): Promise<void> {
    if (this.busy()) return;
    this.busy.set(true);
    try {
      const created = await firstValueFrom(this.comms.createPortalLink(this.patientId));
      this.freshLink.set(created.url);
      this.links.set(await firstValueFrom(this.comms.getPortalLinks(this.patientId)));
    } catch (error) {
      this.report(error, 'No se pudo generar el enlace');
    } finally {
      this.busy.set(false);
    }
  }

  async revoke(link: PortalLink): Promise<void> {
    this.busy.set(true);
    try {
      await firstValueFrom(this.comms.revokePortalLink(link.id, 'Revocado desde la ficha'));
      this.links.set(await firstValueFrom(this.comms.getPortalLinks(this.patientId)));
      this.snackBar.open('Enlace revocado', 'Cerrar', { duration: 3000 });
    } catch (error) {
      this.report(error, 'No se pudo revocar el enlace');
    } finally {
      this.busy.set(false);
    }
  }

  private report(error: unknown, fallback: string): void {
    const detail = (error as { error?: { detail?: unknown } })?.error?.detail;
    this.snackBar.open(typeof detail === 'string' ? detail : fallback, 'Cerrar', {
      duration: 9000,
    });
  }
}
