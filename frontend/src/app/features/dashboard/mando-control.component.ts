import { DatePipe } from '@angular/common';
import { HttpClient } from '@angular/common/http';
import { Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/auth/auth.service';
import { formatMoney } from '../../core/models/finance.models';
import { promptText } from '../../shared/confirm-dialog/prompt-dialog.component';
import { abrirComprobantesPendientes } from '../../shared/payment-info/portal-receipts.component';

interface Control {
  today: string;
  monthly_goal: string | null;
  collected_month: string | null;
  collected_previous_same_period: string | null;
  goal_progress: number | null;
  projection_month: string | null;
  workdays_total: number;
  workdays_elapsed: number;
  workdays_left: number;
  needed_per_workday: string | null;
  collected_today: string | null;
  payments_today: number | null;
  appointments_today: number;
  appointments_confirmed: number;
  appointments_attended: number;
  appointments_pending_confirm: number;
  no_shows_today: number;
  no_shows_month: number;
  new_patients_month: number;
  daily_income: { date: string; amount: string }[] | null;
  ortho_overdue: number | null;
  receipts_pending?: number | null;
}

const MESES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];

@Component({
  selector: 'app-mando-control',
  standalone: true,
  imports: [DatePipe, MatButtonModule, MatIconModule, MatTooltipModule, RouterLink],
  template: `
    @if (datos(); as d) {
      <section class="mando" aria-label="Mando de control">
        <!-- Meta del mes -->
        @if (d.collected_month !== null) {
          <article class="glass-card meta">
            <header>
              <div>
                <span class="kicker">Meta de {{ mes() }}</span>
                <p class="cifra numeric">
                  <small>$</small>{{ money(animado()) }}
                  @if (d.monthly_goal) { <span class="de">de $ {{ money(d.monthly_goal) }}</span> }
                </p>
              </div>
              @if (puedeMeta) {
                <button mat-icon-button (click)="definirMeta()" [matTooltip]="d.monthly_goal ? 'Cambiar la meta' : 'Definir la meta'">
                  <mat-icon>{{ d.monthly_goal ? 'edit' : 'flag' }}</mat-icon>
                </button>
              }
            </header>

            @if (d.monthly_goal) {
              <div class="barra" role="progressbar" [attr.aria-valuenow]="pct(d.goal_progress)" aria-valuemin="0" aria-valuemax="100">
                <span class="relleno" [class.lograda]="(d.goal_progress ?? 0) >= 1" [style.width.%]="lleno() ? pct(d.goal_progress) : 0"></span>
                <span class="ritmo" [style.left.%]="ritmo()" [matTooltip]="'Lo esperado a esta altura del mes (' + d.workdays_elapsed + ' de ' + d.workdays_total + ' días hábiles)'"></span>
              </div>
              <div class="pie">
                <strong [class.bien]="diferencia() >= 0" [class.mal]="diferencia() < 0">
                  @if ((d.goal_progress ?? 0) >= 1) {
                    ¡Meta cumplida! {{ pct(d.goal_progress) }} %
                  } @else {
                    {{ pct(d.goal_progress) }} % · {{ diferencia() >= 0 ? 'por encima' : 'por debajo' }} del ritmo ({{ diferenciaTexto() }})
                  }
                </strong>
                @if ((d.goal_progress ?? 0) < 1 && d.needed_per_workday) {
                  <span>Faltan $ {{ money(falta()) }} · <b>$ {{ money(d.needed_per_workday) }}</b> por día hábil ({{ d.workdays_left }} {{ d.workdays_left === 1 ? 'día' : 'días' }})</span>
                }
              </div>
            } @else {
              <p class="sin-meta">
                Ponle una meta al mes y verás aquí si vas al ritmo, cuánto falta y cuánto cobrar por día.
                @if (puedeMeta) { <button mat-stroked-button (click)="definirMeta()"><mat-icon>flag</mat-icon>Definir meta</button> }
              </p>
            }
            <div class="extras">
              @if (d.projection_month) { <span><mat-icon>insights</mat-icon>Proyección al cierre: <b>$ {{ money(d.projection_month) }}</b></span> }
              @if (vsAnterior(); as v) {
                <span [class.bien]="v >= 0" [class.mal]="v < 0"><mat-icon>{{ v >= 0 ? 'trending_up' : 'trending_down' }}</mat-icon>{{ v >= 0 ? '+' : '' }}{{ v }} % vs. el mes pasado a esta fecha</span>
              }
            </div>
          </article>
        }

        <!-- Hoy -->
        <article class="glass-card hoy">
          <span class="kicker">Hoy</span>
          @if (d.collected_today !== null) {
            <p class="cifra numeric"><small>$</small>{{ money(animadoHoy()) }}</p>
            <p class="sub">cobrados en {{ d.payments_today }} {{ d.payments_today === 1 ? 'pago' : 'pagos' }}</p>
          }
          <ul class="citas">
            <li><span class="punto conf"></span><b>{{ d.appointments_confirmed }}</b> confirmadas</li>
            <li><span class="punto pend"></span><b>{{ d.appointments_pending_confirm }}</b> por confirmar</li>
            <li><span class="punto aten"></span><b>{{ d.appointments_attended }}</b> atendidas</li>
            <li><span class="punto falta"></span><b>{{ d.no_shows_today }}</b> no asistieron</li>
          </ul>
          <div class="pila" [attr.aria-label]="d.appointments_today + ' citas hoy'">
            @for (t of tramos(); track t.clase) {
              <span [class]="t.clase" [style.flex-grow]="t.n"></span>
            }
          </div>
        </article>

        <!-- Ingresos 30 días -->
        @if (d.daily_income; as serie) {
          <article class="glass-card serie">
            <header>
              <div>
                <span class="kicker">Cobros · últimos 30 días</span>
                <p class="cifra chica numeric"><small>$</small>{{ money(total30()) }}</p>
              </div>
              <span class="prom">Promedio $ {{ money(promedio()) }}/día</span>
            </header>
            @if (total30() === 0) {
              <p class="vacio-serie">Sin cobros registrados en los últimos 30 días.</p>
            } @else {
            <svg [attr.viewBox]="'0 0 ' + ANCHO + ' ' + ALTO" preserveAspectRatio="none" class="barras" (mouseleave)="foco.set(null)">
              <line class="linea-prom" x1="0" [attr.x2]="ANCHO" [attr.y1]="yProm()" [attr.y2]="yProm()" />
              @for (b of barras(); track b.fecha; let i = $index) {
                <rect
                  class="barra-dia"
                  [class.hoy]="i === barras().length - 1"
                  [class.foco]="foco() === i"
                  [attr.x]="b.x"
                  [attr.y]="lleno() ? b.y : ALTO"
                  [attr.width]="b.w"
                  [attr.height]="lleno() ? b.h : 0"
                  rx="3"
                  (mouseenter)="foco.set(i)"
                />
              }
            </svg>
            <p class="detalle-dia">
              @if (foco() !== null) {
                {{ barras()[foco()!].fecha | date: "EEE d 'de' MMM" }} · <b>$ {{ money(barras()[foco()!].monto) }}</b>
              } @else {
                Pase el cursor sobre una barra para ver el día.
              }
            </p>
            }
          </article>
        }

        <!-- Chips de seguimiento -->
        <div class="chips">
          @if (d.receipts_pending) {
            <button type="button" class="chip alerta" (click)="verComprobantes()">
              <mat-icon>receipt</mat-icon><b>{{ d.receipts_pending }}</b> {{ d.receipts_pending === 1 ? 'comprobante por revisar' : 'comprobantes por revisar' }}
            </button>
          }
          @if (d.ortho_overdue !== null) {
            <a class="chip" [class.alerta]="d.ortho_overdue > 0" routerLink="/orthodontics">
              <mat-icon>sentiment_very_satisfied</mat-icon><b>{{ d.ortho_overdue }}</b> {{ d.ortho_overdue === 1 ? 'ortodoncia con control atrasado' : 'ortodoncias con control atrasado' }}
            </a>
          }
          <span class="chip"><mat-icon>person_add</mat-icon><b>{{ d.new_patients_month }}</b> {{ d.new_patients_month === 1 ? 'paciente nuevo' : 'pacientes nuevos' }} este mes</span>
          <span class="chip" [class.alerta]="d.no_shows_month > 0"><mat-icon>event_busy</mat-icon><b>{{ d.no_shows_month }}</b> no asistieron este mes</span>
        </div>
      </section>
    }
  `,
  styles: [
    `
      .mando { display: grid; grid-template-columns: 1.5fr 1fr 1.4fr; gap: 14px; margin: 4px 0 18px; }
      .glass-card { padding: 16px 18px; min-width: 0; }
      .kicker { font-size: .7rem; font-weight: 700; letter-spacing: .1em; text-transform: uppercase; color: var(--color-ink-faint); }
      .cifra { margin: 4px 0 0; font-size: 2rem; font-weight: 800; letter-spacing: -.03em; line-height: 1.1;
        small { font-size: .55em; margin-right: 3px; color: var(--color-ink-soft); }
        .de { margin-left: 6px; font-size: .45em; font-weight: 600; color: var(--color-ink-faint); letter-spacing: 0; } }
      .cifra.chica { font-size: 1.5rem; }
      .sub { margin: 0; font-size: .78rem; color: var(--color-ink-faint); }
      header { display: flex; align-items: flex-start; justify-content: space-between; gap: 8px; }
      .bien { color: var(--color-success); } .mal { color: var(--color-danger); }

      .barra { position: relative; height: 14px; margin: 14px 0 8px; border-radius: 999px; background: var(--color-surface-muted); overflow: visible; }
      .relleno { position: absolute; inset: 0 auto 0 0; max-width: 100%; border-radius: 999px; background: var(--color-primary);
        transition: width 1.2s cubic-bezier(.22, 1, .36, 1); }
      .relleno.lograda { background: var(--color-success); }
      .ritmo { position: absolute; top: -5px; bottom: -5px; width: 3px; margin-left: -1.5px; border-radius: 2px; background: var(--color-ink); opacity: .55; cursor: help; }
      .pie { display: grid; gap: 2px; font-size: .82rem; span { color: var(--color-ink-soft); } }
      .sin-meta { display: flex; flex-wrap: wrap; align-items: center; gap: 10px; margin: 10px 0 4px; font-size: .84rem; color: var(--color-ink-soft); }
      .extras { display: flex; flex-wrap: wrap; gap: 6px 14px; margin-top: 10px; font-size: .78rem; color: var(--color-ink-soft);
        span { display: inline-flex; align-items: center; gap: 4px; } mat-icon { font-size: 16px; width: 16px; height: 16px; } }

      .citas { list-style: none; margin: 10px 0 8px; padding: 0; display: grid; grid-template-columns: 1fr 1fr; gap: 4px 10px; font-size: .8rem;
        li { display: flex; align-items: center; gap: 6px; } }
      .punto { width: 8px; height: 8px; border-radius: 50%; }
      .conf { background: var(--color-primary); } .pend { background: var(--color-accent); } .aten { background: var(--color-success); } .falta { background: var(--color-danger); }
      .pila { display: flex; gap: 2px; height: 8px; border-radius: 999px; overflow: hidden; background: var(--color-surface-muted);
        span { flex-basis: 0; min-width: 0; transition: flex-grow .8s ease; } }

      .prom { font-size: .74rem; color: var(--color-ink-faint); white-space: nowrap; }
      .barras { display: block; width: 100%; height: 92px; margin-top: 8px; }
      .barra-dia { fill: var(--color-primary); opacity: .45; transition: y .9s cubic-bezier(.22, 1, .36, 1), height .9s cubic-bezier(.22, 1, .36, 1), opacity .15s; }
      .barra-dia.hoy { opacity: .9; }
      .barra-dia.foco { opacity: 1; }
      .linea-prom { stroke: var(--color-ink-faint); stroke-width: 1; stroke-dasharray: 4 4; vector-effect: non-scaling-stroke; }
      .vacio-serie { margin: 22px 0; font-size: .84rem; color: var(--color-ink-faint); }
      .detalle-dia { margin: 6px 0 0; font-size: .76rem; color: var(--color-ink-soft); min-height: 1.2em; }

      .chips { grid-column: 1 / -1; display: flex; flex-wrap: wrap; gap: 8px; }
      .chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 999px; border: 1px solid var(--color-border);
        background: var(--glass-chip-bg, var(--color-surface)); font-size: .8rem; color: var(--color-ink-soft); text-decoration: none;
        mat-icon { font-size: 17px; width: 17px; height: 17px; color: var(--color-primary); } b { color: var(--color-ink); }
        &.alerta { border-color: color-mix(in srgb, var(--color-danger) 35%, transparent); mat-icon, b { color: var(--color-danger); } } }
      a.chip:hover, button.chip:hover { border-color: var(--color-primary); }
      button.chip { font: inherit; font-size: .8rem; cursor: pointer; }
      @media (max-width: 1100px) { .mando { grid-template-columns: 1fr 1fr; } .serie { grid-column: 1 / -1; } }
      @media (max-width: 700px) { .mando { grid-template-columns: 1fr; } }
      @media (prefers-reduced-motion: reduce) { .relleno, .barra-dia, .pila span { transition: none; } }
    `,
  ],
})
export class MandoControlComponent implements OnInit, OnDestroy {
  private readonly http = inject(HttpClient);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);
  readonly puedeMeta = inject(AuthService).hasPermission('settings:manage');
  private readonly puedeCobrar = inject(AuthService).hasPermission('payments:write');

  async verComprobantes(): Promise<void> {
    await abrirComprobantesPendientes(this.dialog, this.puedeCobrar);
    await this.cargar();
  }

  readonly datos = signal<Control | null>(null);
  readonly lleno = signal(false);
  readonly animado = signal(0);
  readonly animadoHoy = signal(0);
  readonly foco = signal<number | null>(null);
  readonly money = formatMoney;
  readonly ANCHO = 300;
  readonly ALTO = 92;
  private cuadro = 0;

  readonly mes = computed(() => {
    const d = this.datos();
    return d ? MESES[new Date(d.today + 'T12:00').getMonth()] : '';
  });
  readonly ritmo = computed(() => {
    const d = this.datos();
    return d && d.workdays_total ? Math.min(100, (d.workdays_elapsed / d.workdays_total) * 100) : 0;
  });
  readonly diferencia = computed(() => this.pct(this.datos()?.goal_progress ?? 0) - Math.round(this.ritmo()));
  readonly falta = computed(() => {
    const d = this.datos();
    return d?.monthly_goal ? Math.max(0, +d.monthly_goal - +(d.collected_month ?? 0)) : 0;
  });
  readonly vsAnterior = computed(() => {
    const d = this.datos();
    if (!d?.collected_previous_same_period || +d.collected_previous_same_period === 0) return null;
    return Math.round(((+(d.collected_month ?? 0) - +d.collected_previous_same_period) / +d.collected_previous_same_period) * 100);
  });
  readonly total30 = computed(() => (this.datos()?.daily_income ?? []).reduce((s, x) => s + +x.amount, 0));
  readonly promedio = computed(() => this.total30() / 30);
  readonly barras = computed(() => {
    const serie = this.datos()?.daily_income ?? [];
    const max = Math.max(1, ...serie.map((x) => +x.amount));
    const paso = this.ANCHO / Math.max(1, serie.length);
    return serie.map((x, i) => {
      const h = Math.max(+x.amount > 0 ? 3 : 1, (+x.amount / max) * (this.ALTO - 6));
      return { fecha: x.date, monto: x.amount, x: i * paso + 1, w: Math.max(2, paso - 2), h, y: this.ALTO - h };
    });
  });
  readonly yProm = computed(() => {
    const serie = this.datos()?.daily_income ?? [];
    const max = Math.max(1, ...serie.map((x) => +x.amount));
    return this.ALTO - (this.promedio() / max) * (this.ALTO - 6);
  });
  readonly tramos = computed(() => {
    const d = this.datos();
    if (!d) return [];
    return [
      { clase: 'aten', n: d.appointments_attended },
      { clase: 'conf', n: d.appointments_confirmed },
      { clase: 'pend', n: d.appointments_pending_confirm },
      { clase: 'falta', n: d.no_shows_today },
    ].filter((t) => t.n > 0);
  });

  async ngOnInit(): Promise<void> {
    await this.cargar();
  }

  ngOnDestroy(): void {
    cancelAnimationFrame(this.cuadro);
  }

  private async cargar(): Promise<void> {
    try {
      this.poner(await firstValueFrom(this.http.get<Control>(`${environment.apiUrl}/dashboard/control`)));
    } catch {
      this.datos.set(null);
    }
  }

  private poner(d: Control): void {
    this.datos.set(d);
    this.lleno.set(false);
    requestAnimationFrame(() => requestAnimationFrame(() => this.lleno.set(true)));
    this.contar(+(d.collected_month ?? 0), +(d.collected_today ?? 0));
  }

  private contar(mes: number, hoy: number): void {
    cancelAnimationFrame(this.cuadro);
    if (window.matchMedia?.('(prefers-reduced-motion: reduce)').matches) {
      this.animado.set(mes);
      this.animadoHoy.set(hoy);
      return;
    }
    const inicio = performance.now();
    const dur = 1100;
    const paso = (t: number) => {
      const k = Math.min(1, (t - inicio) / dur);
      const e = 1 - Math.pow(1 - k, 3);
      this.animado.set(mes * e);
      this.animadoHoy.set(hoy * e);
      if (k < 1) this.cuadro = requestAnimationFrame(paso);
    };
    this.cuadro = requestAnimationFrame(paso);
  }

  pct(v: number | null | undefined): number {
    return Math.round((v ?? 0) * 100);
  }

  diferenciaTexto(): string {
    const d = this.diferencia();
    return `${d >= 0 ? '+' : '−'}${Math.abs(d)} pts`;
  }

  async definirMeta(): Promise<void> {
    const d = this.datos();
    const texto = await promptText(this.dialog, {
      title: `Meta de cobros de ${this.mes()}`,
      message: 'Lo que la consulta quiere cobrar este mes. Déjelo vacío para quitar la meta.',
      label: 'Meta en dólares',
      initial: d?.monthly_goal ? String(+d.monthly_goal) : '',
      confirmLabel: 'Guardar meta',
    });
    if (texto === null) return;
    const limpio = texto.replace(/[^\d.,]/g, '').replace(',', '.');
    const valor = limpio ? Number(limpio) : null;
    if (valor !== null && (isNaN(valor) || valor < 0)) {
      this.snack.open('Escriba un monto válido.', undefined, { duration: 2500 });
      return;
    }
    try {
      this.poner(await firstValueFrom(this.http.put<Control>(`${environment.apiUrl}/dashboard/goal`, { monthly_goal: valor ? valor.toFixed(2) : null })));
      this.snack.open(valor ? 'Meta guardada.' : 'Meta quitada.', undefined, { duration: 2000 });
    } catch {
      this.snack.open('No se pudo guardar la meta.', 'Cerrar', { duration: 4000 });
    }
  }
}
