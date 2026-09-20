import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  AiStatus,
  AiSuggestion,
  DispatchResult,
  MessageTemplate,
  OutboundMessage,
  PortalLink,
  PortalLinkCreated,
  PortalView,
  ProviderStatus,
} from '../models/communication.models';

@Injectable({ providedIn: 'root' })
export class CommunicationService {
  private readonly http = inject(HttpClient);
  private readonly api = environment.apiUrl;

  // ---- Messaging --------------------------------------------------------

  getProviderStatus(): Observable<ProviderStatus> {
    return this.http.get<ProviderStatus>(`${this.api}/messaging/status`);
  }

  getTemplates(): Observable<MessageTemplate[]> {
    return this.http.get<MessageTemplate[]>(`${this.api}/messaging/templates`);
  }

  saveTemplate(body: Omit<MessageTemplate, 'id'>): Observable<MessageTemplate> {
    return this.http.put<MessageTemplate>(`${this.api}/messaging/templates`, body);
  }

  getMessages(patientId?: string): Observable<OutboundMessage[]> {
    const query = patientId ? `?patient_id=${patientId}` : '';
    return this.http.get<OutboundMessage[]>(`${this.api}/messaging/messages${query}`);
  }

  sendMessage(body: {
    patient_id: string;
    channel: string;
    body?: string | null;
    template_code?: string | null;
  }): Observable<OutboundMessage> {
    return this.http.post<OutboundMessage>(`${this.api}/messaging/messages`, body);
  }

  /** Sends the reminders whose moment has arrived. Driven from a button here
   *  and from cron in a real deployment — same endpoint either way. */
  dispatchReminders(): Observable<DispatchResult> {
    return this.http.post<DispatchResult>(`${this.api}/messaging/dispatch`, {});
  }

  // ---- Assistant --------------------------------------------------------

  getAiStatus(): Observable<AiStatus> {
    return this.http.get<AiStatus>(`${this.api}/ai/status`);
  }

  getAiContext(patientId: string): Observable<{ context: string }> {
    return this.http.get<{ context: string }>(`${this.api}/patients/${patientId}/ai/context`);
  }

  getSuggestions(patientId: string): Observable<AiSuggestion[]> {
    return this.http.get<AiSuggestion[]>(`${this.api}/patients/${patientId}/ai/suggestions`);
  }

  createSuggestion(
    patientId: string,
    body: { kind: string; request?: string | null },
  ): Observable<AiSuggestion> {
    return this.http.post<AiSuggestion>(`${this.api}/patients/${patientId}/ai/suggestions`, body);
  }

  acceptSuggestion(id: string): Observable<AiSuggestion> {
    return this.http.post<AiSuggestion>(`${this.api}/ai/suggestions/${id}/accept`, {});
  }

  discardSuggestion(id: string, reason?: string | null): Observable<AiSuggestion> {
    return this.http.post<AiSuggestion>(`${this.api}/ai/suggestions/${id}/discard`, {
      reason: reason ?? null,
    });
  }

  // ---- Portal -----------------------------------------------------------

  getPortalLinks(patientId: string): Observable<PortalLink[]> {
    return this.http.get<PortalLink[]>(`${this.api}/patients/${patientId}/portal`);
  }

  createPortalLink(patientId: string): Observable<PortalLinkCreated> {
    return this.http.post<PortalLinkCreated>(`${this.api}/patients/${patientId}/portal`, {});
  }

  revokePortalLink(accessId: string, reason?: string | null): Observable<PortalLink> {
    return this.http.post<PortalLink>(`${this.api}/portal/${accessId}/revoke`, {
      reason: reason ?? null,
    });
  }

  /** The public view. No auth header is needed — the token is the credential. */
  getPortalView(token: string): Observable<PortalView> {
    return this.http.get<PortalView>(`${this.api}/portal/view/${token}`);
  }
}
