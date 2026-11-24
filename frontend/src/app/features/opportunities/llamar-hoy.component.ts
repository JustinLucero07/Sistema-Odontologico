import { DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { whatsappUrl } from '../../shared/whatsapp';

interface Hueco {
  professional_id: string;
  professional_name: string;
  starts_at: string;
  ends_at: string;
  minutos: number;
}

interface Sugerencia {
  patient_id: string;
  patient_name: string;
  phone: string | null;
  whatsapp: string | null;
  motivo: 'ortodoncia' | 'reagendar' | 'tratamiento' | 'control';
  detalle: string;
  razones: string[];
  riesgo: 'bajo' | 'medio' | 'alto' | 'nuevo';
  puntaje: number;
  hueco: Hueco | null;
  mensaje: string;
}

interface LlamarHoy {
  huecos: Hueco[];
  minutos_libres: number;
  sugerencias: Sugerencia[];
}

const MOTIVOS: Record<Sugerencia['motivo'], { icono: string; color: string }> = {
  ortodoncia: { icono: 'sentiment_very_satisfied', color: '#0e7c74' },
  reagendar: { icono: 'event_repeat', color: '#d0453a' },
  tratamiento: { icono: 'assignment_late', color: '#c98a1e' },
  control: { icono: 'person_search', color: '#7b5bd6' },
};

@Component({
  selector: 'app-llamar-hoy',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatIconModule, MatTooltipModule, RouterLink],
  template: `
    @if (data(); as d) {
      <section class="glass-card llamar">
        <header>
          <span class="sello"><mat-icon>auto_awesome</mat-icon></span>
          <div>
            <h2>A quién llamar hoy</h2>
            <p>
              @if (d.minutos_libres) {
                Hay <strong>{{ horas(d.minutos_libres) }}</strong> libres entre hoy y el próximo día de atención.
                Estos pacientes son los que más probablemente acepten y asistan.
              } @else {
                La agenda está llena. Estos pacientes conviene contactarlos para los próximos días.
              }
            </p>
          </div>
        </header>

        @if (d.huecos.length) {
          <div class="huecos">
            @for (h of huecosVisibles(); track h.professional_id + h.starts_at) {
              <span class="hueco"><mat-icon>schedule</mat-icon>{{ dia(h.starts_at) }} {{ h.starts_at | date: 'HH:mm' }}–{{ h.ends_at | date: 'HH:mm' }} · {{ h.professional_name }}</span>
            }
            @if (d.huecos.length > huecosVisibles().length) {
              <button type="button" class="mas" (click)="todosHuecos.set(true)">+{{ d.huecos.length - huecosVisibles().length }} más</button>
            }
          </div>
        }

        @for (s of visibles(); track s.patient_id; let i = $index) {
          <article class="fila" [style.--tono]="motivo(s).color">
            <span class="pos numeric">{{ i + 1 }}</span>
            <span class="icono"><mat-icon>{{ motivo(s).icono }}</mat-icon></span>
            <div class="info">
              <div class="nombre">
                <a [routerLink]="['/patients', s.patient_id]">{{ s.patient_name }}</a>
                @if (s.riesgo === 'alto') { <span class="riesgo alto" matTooltip="Suele faltar a sus citas">Suele faltar</span> }
                @if (s.riesgo === 'bajo') { <span class="riesgo bajo" matTooltip="Casi siempre asiste">Cumplido</span> }
              </div>
              <ul>
                @for (r of s.razones; track r) { <li>{{ r }}</li> }
              </ul>
              @if (s.hueco; as h) {
                <span class="propuesta"><mat-icon>event_available</mat-icon>Proponer: {{ dia(h.starts_at) }} {{ h.starts_at | date: 'HH:mm' }} con {{ h.professional_name }}</span>
              }
            </div>
            <div class="acciones">
              @if (s.phone) {
                <a mat-icon-button [href]="'tel:' + s.phone" matTooltip="Llamar" aria-label="Llamar"><mat-icon>call</mat-icon></a>
              }
              @if (wa(s); as link) {
                <a mat-icon-button class="wa" [href]="link" target="_blank" rel="noopener" matTooltip="Enviar WhatsApp con el mensaje listo" aria-label="WhatsApp"><mat-icon>chat</mat-icon></a>
              }
              <a mat-stroked-button [routerLink]="['/agenda']" [queryParams]="agendar(s)"><mat-icon>event</mat-icon>Agendar</a>
            </div>
          </article>
        } @empty {
          <div class="vacio"><mat-icon>task_alt</mat-icon><p>No hay a quién llamar por ahora.</p></div>
        }
        @if (d.sugerencias.length > visibles().length) {
          <button mat-button class="ver-todos" (click)="todos.set(true)">Ver los {{ d.sugerencias.length }}</button>
        }
      </section>
    }
  `,
  styles: [
    `
      .llamar { padding: 18px 20px; }
      header { display: flex; gap: 12px; align-items: flex-start; margin-bottom: 10px;
        h2 { margin: 0; font-size: 1.05rem; font-family: var(--font-display); }
        p { margin: 2px 0 0; font-size: .82rem; color: var(--color-ink-soft); max-width: 70ch; } }
      .sello { display: inline-grid; place-items: center; width: 38px; height: 38px; border-radius: 12px; flex-shrink: 0;
        background: var(--color-primary-soft); color: var(--color-primary); }
      .huecos { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 6px; }
      .hueco { display: inline-flex; align-items: center; gap: 4px; padding: 4px 10px; border-radius: 999px; font-size: .76rem;
        background: var(--color-surface-muted); color: var(--color-ink-soft);
        mat-icon { font-size: 15px; width: 15px; height: 15px; } }
      .mas { border: 0; background: none; font: inherit; font-size: .76rem; color: var(--color-primary); cursor: pointer; }
      .fila { display: flex; align-items: flex-start; gap: 12px; padding: 12px 0; border-top: 1px solid var(--color-border); }
      .pos { width: 18px; padding-top: 9px; font-size: .78rem; font-weight: 700; color: var(--color-ink-faint); text-align: right; }
      .icono { display: inline-grid; place-items: center; width: 36px; height: 36px; border-radius: 50%; flex-shrink: 0;
        background: color-mix(in srgb, var(--tono) 15%, transparent); color: var(--tono);
        mat-icon { font-size: 20px; width: 20px; height: 20px; } }
      .info { flex: 1; min-width: 0; }
      .nombre { display: flex; align-items: center; gap: 8px; flex-wrap: wrap;
        a { font-weight: 600; color: var(--color-ink); text-decoration: none; &:hover { color: var(--color-primary); } } }
      .riesgo { padding: 1px 8px; border-radius: 999px; font-size: .7rem; font-weight: 600;
        &.alto { background: var(--color-danger-soft); color: var(--color-danger); }
        &.bajo { background: var(--color-success-soft); color: var(--color-success); } }
      ul { margin: 3px 0 0; padding: 0; list-style: none; display: grid; gap: 1px;
        li { font-size: .8rem; color: var(--color-ink-soft); }
        li::before { content: '·'; margin-right: 6px; color: var(--color-ink-faint); } }
      .propuesta { display: inline-flex; align-items: center; gap: 4px; margin-top: 5px; font-size: .78rem; font-weight: 600; color: var(--color-primary);
        mat-icon { font-size: 16px; width: 16px; height: 16px; } }
      .acciones { display: flex; align-items: center; gap: 4px; flex-shrink: 0; }
      .wa { color: #1fa855; }
      .vacio { display: grid; justify-items: center; padding: 20px; color: var(--color-ink-faint);
        mat-icon { color: var(--color-success); } p { margin: 4px 0 0; } }
      .ver-todos { margin-top: 6px; }
      @media (max-width: 640px) {
        .fila { flex-wrap: wrap; }
        .pos { display: none; }
        .acciones { width: 100%; justify-content: flex-end; }
      }
    `,
  ],
})
export class LlamarHoyComponent implements OnInit {
  private readonly http = inject(HttpClient);
  readonly data = signal<LlamarHoy | null>(null);
  readonly todos = signal(false);
  readonly todosHuecos = signal(false);
  readonly visibles = computed(() => {
    const s = this.data()?.sugerencias ?? [];
    return this.todos() ? s : s.slice(0, 5);
  });
  readonly huecosVisibles = computed(() => {
    const h = this.data()?.huecos ?? [];
    return this.todosHuecos() ? h : h.slice(0, 4);
  });

  async ngOnInit(): Promise<void> {
    await this.cargar();
  }

  async cargar(): Promise<void> {
    try {
      this.data.set(await firstValueFrom(this.http.get<LlamarHoy>(`${environment.apiUrl}/insights/call-today`)));
    } catch {
      this.data.set(null);
    }
  }

  motivo(s: Sugerencia) {
    return MOTIVOS[s.motivo];
  }

  wa(s: Sugerencia): string | null {
    return whatsappUrl(s.whatsapp, s.mensaje);
  }

  agendar(s: Sugerencia): Record<string, string> {
    const q: Record<string, string> = { nueva: '1', paciente: s.patient_id };
    if (s.hueco) {
      q['inicio'] = s.hueco.starts_at;
      q['profesional'] = s.hueco.professional_id;
    }
    return q;
  }

  dia(iso: string): string {
    const d = new Date(iso);
    const hoy = new Date();
    const manana = new Date();
    manana.setDate(hoy.getDate() + 1);
    if (d.toDateString() === hoy.toDateString()) return 'Hoy';
    if (d.toDateString() === manana.toDateString()) return 'Mañana';
    return d.toLocaleDateString('es-EC', { weekday: 'short', day: 'numeric' });
  }

  horas(min: number): string {
    const h = Math.floor(min / 60);
    const m = min % 60;
    return h ? `${h} h${m ? ` ${m} min` : ''}` : `${m} min`;
  }
}
