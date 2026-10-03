import { DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { formatMoney } from '../../core/models/finance.models';
import { SkeletonComponent } from '../../shared/skeleton/skeleton.component';
import { whatsappUrl } from '../../shared/whatsapp';

interface Contact {
  patient_id: string;
  patient_name: string;
  phone: string | null;
  whatsapp: string | null;
  contact_allowed: boolean;
}

interface Opportunities {
  clinic_name: string;
  recall: (Contact & { last_visit: string; months_since: number })[];
  pending_treatments: (Contact & { treatments: string[]; amount: string })[];
  debtors: (Contact & { pending: string; oldest_charge_on: string })[];
  birthdays: (Contact & { birth_date: string; turns: number; days_until: number })[];
  unconfirmed: (Contact & { appointment_id: string; starts_at: string; professional_name: string })[];
}

type Key = 'unconfirmed' | 'birthdays' | 'pending_treatments' | 'recall' | 'debtors';

interface Row {
  contact: Contact;
  detail: string;
  amount?: string;
  message: string;
}

/**
 * Centro de oportunidades: a quién conviene escribir hoy y por qué. Son reglas
 * claras sobre los datos de la clínica (sin estimaciones): citas de mañana sin
 * confirmar, cumpleaños, tratamientos aprobados sin cita, pacientes que no
 * vienen hace meses y saldos pendientes. Cada fila trae el mensaje listo.
 */
@Component({
  selector: 'app-opportunities-page',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatIconModule, MatTooltipModule, RouterLink, SkeletonComponent],
  template: `
    <div class="page">
      <header class="page-header">
        <div>
          <h1>Oportunidades</h1>
          <p class="page-sub">A quién escribir hoy y por qué. El mensaje ya va escrito; usted decide si lo envía.</p>
        </div>
        <button mat-stroked-button (click)="load()"><mat-icon>refresh</mat-icon>Actualizar</button>
      </header>

      @if (loading()) {
        <app-skeleton variant="cards" [rows]="5" />
        <app-skeleton variant="list" [rows]="5" />
      } @else {
      @if (data(); as d) {
        <section class="tiles">
          @for (g of groups; track g.key) {
            <button type="button" class="glass-card tile" [class.on]="active() === g.key" (click)="active.set(g.key)"
                    [style.--tone]="g.color">
              <span class="tile-icon"><mat-icon>{{ g.icon }}</mat-icon></span>
              <strong class="numeric">{{ d[g.key].length }}</strong>
              <span>{{ g.label }}</span>
            </button>
          }
        </section>

        <section class="glass-card list">
          <header>
            <h2>{{ current().label }}</h2>
            <p>{{ current().hint }}</p>
          </header>
          @for (r of rows(); track r.contact.patient_id + r.detail) {
            <div class="row">
              <span class="avatar" [style.--tone]="current().color">{{ initials(r.contact.patient_name) }}</span>
              <div class="info">
                <a [routerLink]="['/patients', r.contact.patient_id]">{{ r.contact.patient_name }}</a>
                <span>{{ r.detail }}</span>
              </div>
              @if (r.amount) {
                <strong class="amount numeric">$ {{ r.amount }}</strong>
              }
              <div class="actions">
                @if (r.contact.phone) {
                  <a mat-icon-button [href]="'tel:' + r.contact.phone" matTooltip="Llamar" aria-label="Llamar">
                    <mat-icon>call</mat-icon>
                  </a>
                }
                @if (!r.contact.contact_allowed) {
                  <span class="blocked" matTooltip="El paciente retiró su autorización de comunicaciones">
                    <mat-icon>block</mat-icon>Sin autorización
                  </span>
                } @else {
                  @if (wa(r); as link) {
                    <a mat-flat-button class="wa" [href]="link" target="_blank" rel="noopener">
                      <mat-icon>chat</mat-icon>WhatsApp
                    </a>
                  }
                }
              </div>
            </div>
          } @empty {
            <div class="empty">
              <mat-icon>task_alt</mat-icon>
              <p>Nada pendiente aquí. ¡Buen trabajo!</p>
            </div>
          }
        </section>
      }
      }
    </div>
  `,
  styles: [
    `
      .page { display: grid; gap: 18px; }
      .tiles {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
        gap: 12px;
      }
      .tile {
        display: grid;
        justify-items: start;
        gap: 4px;
        padding: 16px;
        border: 1px solid var(--glass-card-border);
        cursor: pointer;
        text-align: left;
        font: inherit;
        color: var(--color-ink);
        transition: transform 0.16s var(--ease-spring), box-shadow 0.2s ease;
        strong { font-size: 1.8rem; font-family: var(--font-display); letter-spacing: -0.02em; line-height: 1.1; }
        span:last-child { font-size: 0.82rem; color: var(--color-ink-soft); }
        &:hover { transform: translateY(-2px); }
        &.on { box-shadow: 0 0 0 2px var(--tone), var(--shadow-md); }
      }
      .tile-icon {
        display: inline-flex; align-items: center; justify-content: center;
        width: 38px; height: 38px; border-radius: 12px;
        background: color-mix(in srgb, var(--tone) 15%, transparent);
        color: var(--tone);
      }
      .list { padding: 18px 20px; }
      .list > header { margin-bottom: 8px; }
      .list h2 { margin: 0; font-size: 1.05rem; font-family: var(--font-display); }
      .list header p { margin: 2px 0 0; font-size: 0.8rem; color: var(--color-ink-faint); }
      .row {
        display: flex; align-items: center; gap: 12px;
        padding: 10px 0; border-top: 1px solid var(--color-border);
      }
      .avatar {
        width: 38px; height: 38px; border-radius: 50%; flex-shrink: 0;
        display: inline-flex; align-items: center; justify-content: center;
        font-size: 0.8rem; font-weight: 700;
        background: color-mix(in srgb, var(--tone) 15%, transparent); color: var(--tone);
      }
      .info { flex: 1; min-width: 0; display: grid; line-height: 1.3; }
      .info a { font-weight: 600; color: var(--color-ink); text-decoration: none; }
      .info a:hover { color: var(--color-primary); }
      .info span { font-size: 0.8rem; color: var(--color-ink-soft); }
      .amount { font-size: 0.95rem; }
      .actions { display: flex; align-items: center; gap: 4px; }
      .wa { --mdc-filled-button-container-color: #1fa855; border-radius: 999px; }
      .blocked { display: inline-flex; align-items: center; gap: 4px; font-size: 0.76rem; color: var(--color-ink-faint);
        mat-icon { font-size: 16px; width: 16px; height: 16px; } }
      .empty { display: grid; justify-items: center; padding: 28px; color: var(--color-ink-faint);
        mat-icon { color: var(--color-success); font-size: 34px; width: 34px; height: 34px; } p { margin: 6px 0 0; } }
      @media (max-width: 640px) {
        .row { flex-wrap: wrap; }
        .actions { width: 100%; justify-content: flex-end; }
      }
    `,
  ],
})
export class OpportunitiesPageComponent implements OnInit {
  private readonly http = inject(HttpClient);

  readonly data = signal<Opportunities | null>(null);
  readonly loading = signal(true);
  readonly active = signal<Key>('unconfirmed');

  readonly groups: { key: Key; label: string; icon: string; color: string; hint: string }[] = [
    { key: 'unconfirmed', label: 'Citas de mañana sin confirmar', icon: 'event_busy', color: '#2f7fd1',
      hint: 'Confirmarlas hoy reduce las inasistencias.' },
    { key: 'birthdays', label: 'Cumpleaños esta semana', icon: 'cake', color: '#d81b60',
      hint: 'Un saludo a tiempo fideliza más que cualquier promoción.' },
    { key: 'pending_treatments', label: 'Tratamientos aprobados sin cita', icon: 'assignment_late', color: '#c98a1e',
      hint: 'Aceptaron el tratamiento pero todavía no tienen fecha.' },
    { key: 'recall', label: 'Pacientes por recuperar', icon: 'person_search', color: '#7b5bd6',
      hint: 'Su última visita fue hace 6 meses o más y no tienen cita.' },
    { key: 'debtors', label: 'Saldos pendientes', icon: 'account_balance_wallet', color: '#d0453a',
      hint: 'Pacientes con cargos sin pagar, de mayor a menor.' },
  ];

  readonly current = computed(() => this.groups.find((g) => g.key === this.active())!);

  readonly rows = computed<Row[]>(() => {
    const d = this.data();
    if (!d) return [];
    const clinic = d.clinic_name;
    const first = (n: string) => n.split(' ')[0];
    switch (this.active()) {
      case 'unconfirmed':
        return d.unconfirmed.map((x) => {
          const when = new Date(x.starts_at).toLocaleTimeString('es-EC', { hour: '2-digit', minute: '2-digit' });
          return {
            contact: x,
            detail: `Mañana ${when} · ${x.professional_name}`,
            message: `Hola ${first(x.patient_name)}, le escribimos de ${clinic} para confirmar su cita de mañana a las ${when} con ${x.professional_name}. ¿Nos confirma su asistencia? ¡Gracias!`,
          };
        });
      case 'birthdays':
        return d.birthdays.map((x) => ({
          contact: x,
          detail: x.days_until === 0 ? `¡Hoy cumple ${x.turns} años!` : `Cumple ${x.turns} en ${x.days_until} ${x.days_until === 1 ? 'día' : 'días'}`,
          message: `¡Feliz cumpleaños, ${first(x.patient_name)}! 🎉 Todo el equipo de ${clinic} le desea un excelente día. Gracias por confiarnos su sonrisa.`,
        }));
      case 'pending_treatments':
        return d.pending_treatments.map((x) => ({
          contact: x,
          detail: x.treatments.join(', '),
          amount: formatMoney(x.amount),
          message: `Hola ${first(x.patient_name)}, le escribimos de ${clinic}. Tiene pendiente: ${x.treatments.join(', ')}. ¿Le gustaría que le agendemos una cita esta semana?`,
        }));
      case 'recall':
        return d.recall.map((x) => ({
          contact: x,
          detail: `Última visita hace ${x.months_since} meses`,
          message: `Hola ${first(x.patient_name)}, en ${clinic} le recordamos que ya es momento de su control dental. ¿Le agendamos una cita?`,
        }));
      case 'debtors':
        return d.debtors.map((x) => ({
          contact: x,
          detail: `Desde ${new Date(x.oldest_charge_on + 'T12:00:00').toLocaleDateString('es-EC')}`,
          amount: formatMoney(x.pending),
          message: `Hola ${first(x.patient_name)}, le escribimos de ${clinic}. Le recordamos que tiene un saldo pendiente de $ ${formatMoney(x.pending)}. Puede acercarse a cancelarlo o escribirnos para coordinar. ¡Gracias!`,
        }));
    }
  });

  async ngOnInit(): Promise<void> {
    await this.load();
  }

  async load(): Promise<void> {
    this.loading.set(true);
    try {
      const d = await firstValueFrom(this.http.get<Opportunities>(`${environment.apiUrl}/insights/opportunities`));
      this.data.set(d);
      const firstWithItems = this.groups.find((g) => d[g.key].length > 0);
      if (firstWithItems && d[this.active()].length === 0) this.active.set(firstWithItems.key);
    } finally {
      this.loading.set(false);
    }
  }

  wa(r: Row): string | null {
    return whatsappUrl(r.contact.whatsapp ?? r.contact.phone, r.message);
  }

  initials(name: string): string {
    return name.split(' ').filter(Boolean).slice(0, 2).map((p) => p[0]).join('').toUpperCase();
  }
}
