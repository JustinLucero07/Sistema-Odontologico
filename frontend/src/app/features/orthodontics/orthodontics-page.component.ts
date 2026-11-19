import { DatePipe } from '@angular/common';
import { Component, OnInit, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatSelectModule } from '@angular/material/select';
import { MatTooltipModule } from '@angular/material/tooltip';
import { Subject, debounceTime, firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { formatMoney } from '../../core/models/finance.models';
import {
  ORTHO_DOC_LABEL,
  ORTHO_STATUS_LABEL,
  ORTHO_TAD_LABEL,
  OrthoCase,
  OrthoCaseList,
  OrthoFilters,
} from '../../core/models/orthodontics.models';
import { OrthodonticsService } from '../../core/services/orthodontics.service';
import { whatsappUrl } from '../../shared/whatsapp';
import { openOrthoCaseDialog } from './ortho-dialogs.component';

@Component({
  selector: 'app-orthodontics-page',
  standalone: true,
  imports: [DatePipe, FormsModule, MatButtonModule, MatIconModule, MatSelectModule, MatTooltipModule],
  template: `
    <div class="page">
      <header class="page-header">
        <div>
          <h1>Pacientes de ortodoncia</h1>
          <p class="page-sub">Fichas, próximos controles, documentación y seguimiento de TAD.</p>
        </div>
        @if (canWrite) {
          <button mat-flat-button (click)="nueva()"><mat-icon>add</mat-icon>Nueva ficha</button>
        }
      </header>

      <section class="filtros glass-card">
        <label class="buscar">
          <span>Nombre, cédula o ficha</span>
          <input [(ngModel)]="f.q" (ngModelChange)="buscar$.next()" placeholder="Ej.: Zumba u ORT-0117" />
        </label>
        <label>
          <span>Estado</span>
          <mat-select [(ngModel)]="f.status" (selectionChange)="cargar()">
            <mat-option value="">Todos</mat-option>
            <mat-option value="abiertos">En tratamiento</mat-option>
            <mat-option value="cerrados">Cerrados</mat-option>
            @for (s of estados; track s[0]) { <mat-option [value]="s[0]">{{ s[1] }}</mat-option> }
          </mat-select>
        </label>
        <label>
          <span>Próximo control</span>
          <mat-select [(ngModel)]="f.next_control" (selectionChange)="cargar()">
            <mat-option value="">Todos</mat-option>
            <mat-option value="vencido">Atrasado (no vino)</mat-option>
            <mat-option value="semana">Esta semana</mat-option>
            <mat-option value="mes">Este mes</mat-option>
            <mat-option value="sin_fecha">Sin fecha</mat-option>
            <mat-option value="con_saldo">Con saldo pendiente</mat-option>
          </mat-select>
        </label>
        <label>
          <span>TADs / anclaje</span>
          <mat-select [(ngModel)]="f.has_tad" (selectionChange)="cargar()">
            <mat-option value="">Todos</mat-option>
            @for (t of tads; track t[0]) { <mat-option [value]="t[0]">{{ t[1] }}</mat-option> }
          </mat-select>
        </label>
        <label>
          <span>Documentación</span>
          <mat-select [(ngModel)]="f.docs" (selectionChange)="cargar()">
            <mat-option value="">Todas</mat-option>
            <mat-option value="pendiente">Con pendientes</mat-option>
            <mat-option value="completa">Completa</mat-option>
          </mat-select>
        </label>
        <label>
          <span>Atención especial</span>
          <mat-select [(ngModel)]="f.special_attention" (selectionChange)="cargar()">
            <mat-option value="">Todos</mat-option>
            <mat-option value="true">Sí</mat-option>
            <mat-option value="false">No</mat-option>
          </mat-select>
        </label>
        <label>
          <span>Revisión</span>
          <mat-select [(ngModel)]="f.needs_review" (selectionChange)="cargar()">
            <mat-option value="">Todos</mat-option>
            <mat-option value="true">Requieren revisión</mat-option>
          </mat-select>
        </label>
        <button mat-button class="limpiar" (click)="limpiar()"><mat-icon>filter_alt_off</mat-icon>Limpiar</button>
      </section>

      @if (datos(); as d) {
        <div class="cuentas">
          <span><strong>{{ d.active }}</strong> en tratamiento</span>
          <span><strong>{{ d.inactive }}</strong> cerrados</span>
          <span><strong>{{ d.total }}</strong> total</span>
          <span><strong>{{ d.items.length }}</strong> coincidencias</span>
        </div>
      }

      <section class="tabla glass-card">
        @if (cargando() && !datos()) {
          <p class="vacio">Cargando…</p>
        } @else if (!datos()?.items?.length) {
          <div class="vacio">
            <mat-icon>sentiment_very_satisfied</mat-icon>
            <strong>{{ datos()?.total ? 'Ningún paciente coincide con los filtros' : 'Aún no hay fichas de ortodoncia' }}</strong>
            @if (!datos()?.total && canWrite) {
              <button mat-flat-button (click)="nueva()"><mat-icon>add</mat-icon>Crear la primera ficha</button>
            }
          </div>
        } @else {
          <div class="scroll">
            <table>
              <thead>
                <tr>
                  <th>Paciente / ficha</th>
                  <th>WhatsApp</th>
                  <th>Estado</th>
                  <th>Inicio</th>
                  <th>Fotos</th>
                  <th>Modelos</th>
                  <th>RX</th>
                  <th>Carpeta</th>
                  <th>TADs</th>
                  <th>Último</th>
                  <th>Próximo</th>
                  <th class="der">Saldo</th>
                </tr>
              </thead>
              <tbody>
                @for (c of datos()!.items; track c.id) {
                  <tr (click)="abrir(c)" tabindex="0" (keydown.enter)="abrir(c)">
                    <td>
                      <strong class="nombre">{{ c.patient.first_name }} {{ c.patient.last_name }}</strong>
                      <span class="sub">
                        {{ c.code }}
                        @if (c.special_attention) { <mat-icon class="mini peligro" [matTooltip]="c.special_attention_note || 'Atención especial'">priority_high</mat-icon> }
                        @if (c.needs_review) { <mat-icon class="mini aviso" matTooltip="Requiere revisión">flag</mat-icon> }
                      </span>
                    </td>
                    <td>
                      @if (wa(c); as url) {
                        <a class="wa" [href]="url" target="_blank" rel="noopener" (click)="$event.stopPropagation()">WhatsApp ↗</a>
                      } @else { <span class="muted">—</span> }
                    </td>
                    <td>
                      <span class="estado" [attr.data-status]="c.status">{{ estadoLabel[c.status] }}</span>
                      <span class="sub">{{ c.stage || 'Etapa por confirmar' }}</span>
                    </td>
                    <td>{{ c.started_on ? (c.started_on | date: 'dd MMM yyyy') : '—' }}</td>
                    <td [attr.data-doc]="c.doc_photos">{{ docLabel[c.doc_photos] }}</td>
                    <td [attr.data-doc]="c.doc_models">{{ docLabel[c.doc_models] }}</td>
                    <td [attr.data-doc]="c.doc_xrays">{{ docLabel[c.doc_xrays] }}</td>
                    <td [attr.data-doc]="c.doc_folder">{{ docLabel[c.doc_folder] }}</td>
                    <td><span class="tad" [attr.data-tad]="c.has_tad">{{ tadLabel[c.has_tad] }}</span></td>
                    <td>{{ c.last_control_on ? (c.last_control_on | date: 'dd/MM/yyyy') : 'Sin registrar' }}</td>
                    <td>
                      @if (c.next_control_on) {
                        <span class="proximo" [class.atrasado]="c.next_control_overdue">
                          {{ c.next_control_on | date: 'dd/MM/yyyy' }}
                        </span>
                        @if (c.next_control_overdue) { <span class="sub peligro">Atrasado</span> }
                      } @else {
                        <span class="proximo sin">Sin fecha</span>
                      }
                    </td>
                    <td class="der numeric" [class.peligro]="+c.balance > 0">$ {{ money(c.balance) }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </div>
        }
      </section>
    </div>
  `,
  styles: [
    `
      .page { display: grid; gap: 14px; }
      .glass-card { padding: 14px 16px; }
      .filtros {
        display: grid; grid-template-columns: minmax(200px, 1.6fr) repeat(6, minmax(120px, 1fr)) auto; gap: 10px 12px; align-items: end;
        label { display: grid; gap: 4px; min-width: 0; }
        span { font-size: .72rem; font-weight: 600; color: var(--color-ink-soft); }
        input, mat-select {
          box-sizing: border-box; width: 100%; height: 40px; padding: 0 12px; display: flex; align-items: center;
          border: 1px solid var(--color-border-strong); border-radius: var(--radius-sm);
          background: var(--color-surface); font: inherit; font-size: .84rem; color: var(--color-ink); min-width: 0;
        }
        mat-select ::ng-deep .mat-mdc-select-trigger { width: 100%; }
        span { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
        input:focus { outline: none; border-color: var(--color-primary); }
      }
      .cuentas { display: flex; flex-wrap: wrap; gap: 8px;
        span { padding: 6px 12px; border-radius: 999px; background: var(--glass-chip-bg); border: 1px solid var(--color-border);
          font-size: .8rem; color: var(--color-ink-soft); } strong { color: var(--color-ink); } }
      .scroll { overflow-x: auto; }
      table { width: 100%; min-width: 980px; border-collapse: collapse; font-size: .8rem; }
      th { padding: 9px 6px; text-align: left; font-size: .68rem; font-weight: 700; letter-spacing: .04em; text-transform: uppercase;
        color: var(--color-ink-faint); border-bottom: 1px solid var(--color-border-strong); white-space: nowrap; }
      td { padding: 10px 6px; border-bottom: 1px solid var(--color-border); vertical-align: top; }
      tbody tr { cursor: pointer; transition: background .15s; }
      tbody tr:hover, tbody tr:focus-visible { background: var(--nav-hover, var(--color-primary-soft)); outline: none; }
      .nombre { display: block; color: var(--color-primary); text-transform: uppercase; font-size: .8rem; }
      .sub { display: flex; align-items: center; gap: 4px; font-size: .72rem; color: var(--color-ink-faint); margin-top: 2px; }
      .mini { font-size: 15px; width: 15px; height: 15px; }
      .peligro { color: var(--color-danger); }
      .aviso { color: var(--color-accent); }
      .muted { color: var(--color-ink-faint); }
      .der { text-align: right; }
      .wa { display: inline-block; padding: 4px 10px; border-radius: 999px; border: 1px solid color-mix(in srgb, #25d366 45%, transparent);
        color: #128c4a; font-weight: 600; font-size: .74rem; text-decoration: none; white-space: nowrap; }
      .estado { display: inline-block; padding: 2px 9px; border-radius: 999px; font-size: .7rem; font-weight: 700;
        background: var(--color-success-soft); color: var(--color-success);
        &[data-status='retencion'], &[data-status='pausa'] { background: var(--color-accent-soft); color: var(--color-accent); }
        &[data-status='finalizado'] { background: color-mix(in srgb, var(--color-ink) 7%, transparent); color: var(--color-ink-soft); }
        &[data-status='abandono'] { background: var(--color-danger-soft); color: var(--color-danger); } }
      td[data-doc='listo'], td[data-doc='no_requiere'] { color: var(--color-success); }
      td[data-doc='pendiente'] { color: var(--color-accent); font-weight: 600; }
      .tad { padding: 2px 8px; border-radius: 6px; font-size: .72rem; font-weight: 600; background: var(--color-surface-muted);
        &[data-tad='si'] { background: var(--color-primary-soft); color: var(--color-primary); } }
      .proximo { display: inline-block; padding: 2px 8px; border-radius: 6px; font-weight: 600;
        &.atrasado { background: var(--color-danger-soft); color: var(--color-danger); }
        &.sin { background: var(--color-accent-soft); color: var(--color-accent); font-size: .74rem; } }
      .vacio { display: grid; justify-items: center; gap: 8px; padding: 36px 12px; color: var(--color-ink-faint); text-align: center;
        mat-icon { font-size: 34px; width: 34px; height: 34px; color: var(--color-primary); } strong { color: var(--color-ink); } }
      @media (max-width: 1350px) { .filtros { grid-template-columns: repeat(4, minmax(0, 1fr)); } .buscar { grid-column: span 2; } }
      @media (max-width: 900px) { .filtros { grid-template-columns: repeat(2, minmax(0, 1fr)); } .buscar { grid-column: 1 / -1; } }
    `,
  ],
})
export class OrthodonticsPageComponent implements OnInit {
  private readonly api = inject(OrthodonticsService);
  private readonly router = inject(Router);
  private readonly dialog = inject(MatDialog);
  private readonly auth = inject(AuthService);

  readonly canWrite = this.auth.hasPermission('orthodontics:write');
  readonly datos = signal<OrthoCaseList | null>(null);
  readonly cargando = signal(false);
  readonly buscar$ = new Subject<void>();
  readonly estados = Object.entries(ORTHO_STATUS_LABEL);
  readonly tads = Object.entries(ORTHO_TAD_LABEL);
  readonly estadoLabel = ORTHO_STATUS_LABEL;
  readonly tadLabel = ORTHO_TAD_LABEL;
  readonly docLabel = ORTHO_DOC_LABEL;
  readonly money = formatMoney;

  f: Required<Pick<OrthoFilters, 'q' | 'status' | 'has_tad' | 'docs' | 'next_control' | 'special_attention' | 'needs_review'>> = {
    q: '',
    status: 'abiertos',
    has_tad: '',
    docs: '',
    next_control: '',
    special_attention: '',
    needs_review: '',
  };

  ngOnInit(): void {
    this.buscar$.pipe(debounceTime(300)).subscribe(() => this.cargar());
    void this.cargar();
  }

  async cargar(): Promise<void> {
    this.cargando.set(true);
    try {
      this.datos.set(await firstValueFrom(this.api.list(this.f)));
    } finally {
      this.cargando.set(false);
    }
  }

  limpiar(): void {
    this.f = { q: '', status: '', has_tad: '', docs: '', next_control: '', special_attention: '', needs_review: '' };
    void this.cargar();
  }

  wa(c: OrthoCase): string | null {
    return whatsappUrl(c.patient.whatsapp || c.patient.phone);
  }

  abrir(c: OrthoCase): void {
    void this.router.navigate(['/patients', c.patient.id], { queryParams: { tab: 'ortodoncia' } });
  }

  async nueva(): Promise<void> {
    const out = await openOrthoCaseDialog(this.dialog, {});
    if (out) void this.router.navigate(['/patients', out.patient.id], { queryParams: { tab: 'ortodoncia' } });
  }
}
