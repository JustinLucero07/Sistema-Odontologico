import { DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnInit, inject, signal } from '@angular/core';
import { MatIconModule } from '@angular/material/icon';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';

interface Cifra {
  codigo: string;
  valor: number;
  etiqueta: string;
  icono: string;
  tono: 'info' | 'alerta' | 'ok' | 'dinero';
  ruta: string | null;
}

interface Especialidad {
  foco: 'ortodoncia' | 'estetica' | 'pediatria';
  titulo: string;
  subtitulo: string;
  cifras: Cifra[];
  accesos: { etiqueta: string; icono: string; ruta: string; query: Record<string, string> }[];
  lista_titulo: string | null;
  lista: { patient_id: string; nombre: string; detalle: string; hora: string | null }[];
  lista_vacia: string | null;
}

export const TEMAS: Record<string, { color: string; icono: string; nombre: string }> = {
  ortodoncia: { color: '#4F46E5', icono: 'sentiment_very_satisfied', nombre: 'Ortodoncia' },
  estetica: { color: '#D0457E', icono: 'auto_awesome', nombre: 'Estética dental' },
  pediatria: { color: '#E0814A', icono: 'child_care', nombre: 'Odontopediatría' },
};

@Component({
  selector: 'app-especialidad',
  standalone: true,
  imports: [DatePipe, MatIconModule, RouterLink],
  template: `
    @if (d(); as e) {
      <section class="esp glass-card" [style.--tema]="tema(e).color" [attr.data-foco]="e.foco">
        <header>
          <span class="sello"><mat-icon>{{ tema(e).icono }}</mat-icon></span>
          <div class="txt">
            <span class="kicker">{{ tema(e).nombre }}</span>
            <h2>{{ e.titulo }}</h2>
            <p>{{ e.subtitulo }}</p>
          </div>
          <nav class="accesos">
            @for (a of e.accesos; track a.etiqueta) {
              <a [routerLink]="a.ruta" [queryParams]="a.query"><mat-icon>{{ a.icono }}</mat-icon>{{ a.etiqueta }}</a>
            }
          </nav>
        </header>

        <div class="cuerpo">
          <div class="cifras">
            @for (c of e.cifras; track c.codigo) {
              @if (c.ruta) {
                <a class="cifra" [routerLink]="c.ruta" [attr.data-tono]="c.tono">
                  <mat-icon>{{ c.icono }}</mat-icon><strong class="numeric">{{ c.valor }}</strong><span>{{ c.etiqueta }}</span>
                </a>
              } @else {
                <div class="cifra" [attr.data-tono]="c.tono">
                  <mat-icon>{{ c.icono }}</mat-icon><strong class="numeric">{{ c.valor }}</strong><span>{{ c.etiqueta }}</span>
                </div>
              }
            }
          </div>

          @if (e.lista_titulo) {
            <div class="lista">
              <h3>{{ e.lista_titulo }}</h3>
              @for (f of e.lista.slice(0, 6); track $index) {
                <a class="fila" [routerLink]="['/patients', f.patient_id]">
                  <span class="hora numeric">{{ f.hora ? (f.hora | date: 'HH:mm') : '' }}</span>
                  <span class="quien"><b>{{ f.nombre }}</b><small>{{ f.detalle }}</small></span>
                  <mat-icon>chevron_right</mat-icon>
                </a>
              } @empty {
                <p class="vacio">{{ e.lista_vacia }}</p>
              }
              @if (e.lista.length > 6) { <a class="mas" routerLink="/agenda">Ver los {{ e.lista.length }} en la agenda</a> }
            </div>
          }
        </div>
      </section>
    }
  `,
  styles: [
    `
      .esp { position: relative; overflow: hidden; padding: 18px 20px; margin: 4px 0 18px;
        border-top: 3px solid var(--tema); }
      .esp::before { content: ''; position: absolute; inset: 0 0 auto 0; height: 120px; pointer-events: none;
        background: linear-gradient(180deg, color-mix(in srgb, var(--tema) 9%, transparent), transparent); }
      header { position: relative; display: flex; align-items: flex-start; gap: 14px; flex-wrap: wrap; }
      .sello { display: grid; place-items: center; width: 46px; height: 46px; border-radius: 14px; flex-shrink: 0;
        background: color-mix(in srgb, var(--tema) 15%, transparent); color: var(--tema);
        mat-icon { font-size: 26px; width: 26px; height: 26px; } }
      .txt { flex: 1 1 260px; min-width: 0;
        .kicker { font-size: .68rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--tema); }
        h2 { margin: 2px 0 0; font-family: var(--font-display); font-size: 1.15rem; letter-spacing: -.01em; }
        p { margin: 2px 0 0; font-size: .82rem; color: var(--color-ink-soft); } }
      .accesos { display: flex; flex-wrap: wrap; gap: 6px;
        a { display: inline-flex; align-items: center; gap: 6px; padding: 7px 12px; border-radius: 999px; font-size: .8rem; font-weight: 600;
          text-decoration: none; color: var(--tema); background: color-mix(in srgb, var(--tema) 10%, transparent);
          transition: background .15s ease, transform .12s ease;
          mat-icon { font-size: 17px; width: 17px; height: 17px; }
          &:hover { background: color-mix(in srgb, var(--tema) 18%, transparent); }
          &:active { transform: scale(.97); } } }
      .cuerpo { position: relative; display: grid; grid-template-columns: 1.3fr 1fr; gap: 16px; margin-top: 16px; }
      .cifras { display: grid; grid-template-columns: repeat(auto-fit, minmax(130px, 1fr)); gap: 10px; align-content: start; }
      .cifra { display: grid; gap: 2px; padding: 12px 14px; border-radius: 14px; text-decoration: none; color: var(--color-ink);
        background: var(--color-surface-muted); border: 1px solid transparent; transition: border-color .15s ease, transform .12s ease;
        mat-icon { font-size: 20px; width: 20px; height: 20px; color: var(--tema); }
        strong { font-family: var(--font-display); font-size: 1.6rem; line-height: 1.1; letter-spacing: -.02em; }
        span { font-size: .76rem; color: var(--color-ink-soft); }
        &[data-tono='alerta'] { mat-icon, strong { color: var(--color-danger); } }
        &[data-tono='dinero'] { mat-icon { color: var(--color-accent); } } }
      a.cifra:hover { border-color: var(--tema); transform: translateY(-1px); }
      .lista { min-width: 0;
        h3 { margin: 0 0 6px; font-size: .82rem; font-weight: 700; color: var(--color-ink-soft); } }
      .fila { display: flex; align-items: center; gap: 10px; padding: 8px 6px; border-radius: 10px; text-decoration: none; color: var(--color-ink);
        &:hover { background: var(--color-surface-muted); }
        .hora { width: 42px; font-size: .82rem; font-weight: 700; color: var(--tema); }
        .quien { flex: 1; min-width: 0; display: grid; line-height: 1.3;
          b { font-weight: 600; font-size: .88rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
          small { font-size: .75rem; color: var(--color-ink-faint); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } }
        mat-icon { color: var(--color-ink-faint); } }
      .vacio { margin: 6px 0; font-size: .82rem; color: var(--color-ink-faint); }
      .mas { display: inline-block; margin-top: 4px; font-size: .78rem; color: var(--tema); font-weight: 600; text-decoration: none; }
      @media (max-width: 900px) { .cuerpo { grid-template-columns: 1fr; } }
      @media (max-width: 640px) {
        .esp { padding: 16px; }
        .txt { flex: 1 1 0; }
        .accesos { flex-basis: 100%; }
        .cifras { grid-template-columns: 1fr 1fr; }
      }
      @media (prefers-reduced-motion: reduce) { .cifra, .accesos a { transition: none; } }
    `,
  ],
})
export class EspecialidadComponent implements OnInit {
  private readonly http = inject(HttpClient);
  readonly d = signal<Especialidad | null>(null);

  async ngOnInit(): Promise<void> {
    try {
      this.d.set(await firstValueFrom(this.http.get<Especialidad | null>(`${environment.apiUrl}/dashboard/specialty`)));
    } catch {
      this.d.set(null);
    }
  }

  tema(e: Especialidad) {
    return TEMAS[e.foco];
  }
}
