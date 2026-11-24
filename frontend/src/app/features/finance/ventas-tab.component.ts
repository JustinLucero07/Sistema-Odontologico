import { DatePipe } from '@angular/common';
import { HttpClient, HttpParams } from '@angular/common/http';
import { Component, Input, OnChanges, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatIconModule } from '@angular/material/icon';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { RouterLink } from '@angular/router';
import { Subject, debounceTime, firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';
import { AuthService } from '../../core/auth/auth.service';
import { formatMoney } from '../../core/models/finance.models';
import { openInvoiceCreate } from '../../shared/invoicing/invoice-create-dialog.component';
import { openInvoiceDetail } from '../../shared/invoicing/invoice-detail-dialog.component';
import { SkeletonComponent } from '../../shared/skeleton/skeleton.component';

interface Pago {
  id: string;
  fecha: string;
  monto: string;
  medio: string;
  medio_codigo: string;
  referencia: string | null;
  comprobante_id: string | null;
}

interface Venta {
  id: string;
  fecha: string;
  patient_id: string;
  paciente: string;
  cedula: string | null;
  descripcion: string;
  origen: 'ortodoncia' | 'credito' | 'presupuesto' | 'manual';
  monto: string;
  pagado: string;
  pendiente: string;
  estado_pago: 'pendiente' | 'parcial' | 'pagada' | 'anulada';
  anulada: boolean;
  pagos: Pago[];
  factura: { id: string; numero: string; estado: string; fecha: string; total: string; acreditado: string } | null;
  facturable: boolean;
  motivo: string | null;
}

interface Ventas {
  resumen: {
    ventas: number;
    vendido: string;
    cobrado: string;
    pendiente: string;
    facturado: string;
    sin_facturar: string;
    abonos_sin_asignar: string;
    pacientes: number;
  };
  items: Venta[];
  facturacion_lista: boolean;
  faltantes: string[];
}

interface Grupo {
  patient_id: string;
  paciente: string;
  cedula: string | null;
  ventas: Venta[];
  total: number;
  cobrado: number;
  pendiente: number;
  facturables: Venta[];
}

const ORIGEN: Record<Venta['origen'], string> = {
  ortodoncia: 'Ortodoncia',
  credito: 'Crédito',
  presupuesto: 'Presupuesto',
  manual: 'Cargo',
};
const ESTADO_FACTURA: Record<string, string> = { autorizada: 'Autorizada', pendiente: 'Enviando', recibida: 'En el SRI' };

@Component({
  selector: 'app-ventas-tab',
  standalone: true,
  imports: [DatePipe, FormsModule, MatButtonModule, MatIconModule, MatTooltipModule, RouterLink, SkeletonComponent],
  template: `
    @if (datos(); as d) {
      <section class="kpis">
        <article class="glass-card kpi"><span>Vendido</span><strong class="numeric">$ {{ money(d.resumen.vendido) }}</strong><small>{{ d.resumen.ventas }} ventas · {{ d.resumen.pacientes }} pacientes</small></article>
        <article class="glass-card kpi"><span>Cobrado</span><strong class="numeric ok">$ {{ money(d.resumen.cobrado) }}</strong><small>De estas ventas</small></article>
        <article class="glass-card kpi"><span>Por cobrar</span><strong class="numeric alerta">$ {{ money(d.resumen.pendiente) }}</strong><small>Saldo de estas ventas</small></article>
        <article class="glass-card kpi"><span>Facturado</span><strong class="numeric">$ {{ money(d.resumen.facturado) }}</strong><small>Con factura vigente</small></article>
        <article class="glass-card kpi"><span>Sin facturar</span><strong class="numeric dinero">$ {{ money(d.resumen.sin_facturar) }}</strong><small>Se puede facturar</small></article>
      </section>
      @if (+d.resumen.abonos_sin_asignar > 0) {
        <p class="nota"><mat-icon>info</mat-icon>Además hay $ {{ money(d.resumen.abonos_sin_asignar) }} en abonos a cuenta sin asignar a una venta en este periodo.</p>
      }
      @if (puedeFacturar && !d.facturacion_lista) {
        <div class="aviso">
          <mat-icon>receipt_long</mat-icon>
          <div><strong>Para emitir facturas electrónicas falta:</strong> {{ d.faltantes.join(' ') }}</div>
          <a mat-stroked-button routerLink="/invoices">Configurar</a>
        </div>
      }
    }

    <div class="filtros glass-card">
      <label class="buscar">
        <mat-icon>search</mat-icon>
        <input [ngModel]="texto()" (ngModelChange)="buscar($event)" placeholder="Paciente, cédula o concepto" aria-label="Buscar ventas" />
      </label>
      <div class="chips" role="group" aria-label="Estado de pago">
        @for (o of opcionesPago; track o[0]) {
          <button type="button" [class.on]="pago() === o[0]" (click)="pago.set(o[0]); cargar()">{{ o[1] }}</button>
        }
      </div>
      <div class="chips" role="group" aria-label="Factura">
        @for (o of opcionesFactura; track o[0]) {
          <button type="button" [class.on]="factura() === o[0]" (click)="factura.set(o[0]); cargar()">{{ o[1] }}</button>
        }
      </div>
      <span class="espacio"></span>
      <button mat-button (click)="agrupar.set(!agrupar())"><mat-icon>{{ agrupar() ? 'view_list' : 'groups' }}</mat-icon>{{ agrupar() ? 'Ver lista' : 'Agrupar por paciente' }}</button>
      <button mat-stroked-button (click)="exportar()"><mat-icon>download</mat-icon>Excel (CSV)</button>
    </div>

    @if (cargando()) {
      <app-skeleton variant="list" [rows]="6" />
    } @else {
      @for (g of grupos(); track g.patient_id) {
        <section class="grupo glass-card">
          @if (agrupar()) {
            <header>
              <div class="quien">
                <a [routerLink]="['/patients', g.patient_id]">{{ g.paciente }}</a>
                <span>{{ g.cedula || 'Sin cédula' }} · {{ g.ventas.length }} {{ g.ventas.length === 1 ? 'venta' : 'ventas' }}</span>
              </div>
              <div class="cifras numeric">
                <span>Total <b>$ {{ money(g.total) }}</b></span>
                <span>Cobrado <b class="ok">$ {{ money(g.cobrado) }}</b></span>
                @if (g.pendiente > 0) { <span>Pendiente <b class="alerta">$ {{ money(g.pendiente) }}</b></span> }
              </div>
              @if (puedeFacturar && g.facturables.length) {
                <button mat-stroked-button (click)="facturarGrupo(g)" [disabled]="!datos()?.facturacion_lista"
                        [matTooltip]="datos()?.facturacion_lista ? 'Facturar todo lo pendiente de facturar de este paciente' : 'Configure la facturación electrónica primero'">
                  <mat-icon>request_quote</mat-icon>Facturar {{ g.facturables.length }}
                </button>
              }
            </header>
          }
          <div class="tabla">
            @for (v of g.ventas; track v.id) {
              <div class="venta" [class.anulada]="v.anulada" [class.abierta]="abierta() === v.id">
                <div class="fila">
                  @if (puedeFacturar) {
                    <input type="checkbox" class="sel" [disabled]="!v.facturable || !datos()?.facturacion_lista" [checked]="seleccion().has(v.id)"
                           (change)="alternar(v)" [attr.aria-label]="'Seleccionar ' + v.descripcion" />
                  }
                  <button type="button" class="abrir" (click)="abierta.set(abierta() === v.id ? null : v.id)" [attr.aria-expanded]="abierta() === v.id">
                    <span class="fecha">{{ v.fecha | date: 'dd/MM/yy' }}</span>
                    <span class="concepto">
                      <b>{{ v.descripcion }}</b>
                      @if (!agrupar()) { <small>{{ v.paciente }}</small> }
                    </span>
                    <span class="origen">{{ origen(v) }}</span>
                    <span class="monto numeric">$ {{ money(v.monto) }}</span>
                    <span class="estado" [attr.data-e]="v.estado_pago">{{ estadoPago(v) }}</span>
                    <span class="fact">
                      @if (v.factura) {
                        <span class="chip-fact ok"><mat-icon>verified</mat-icon>{{ v.factura.numero }}</span>
                      } @else if (v.facturable) {
                        <span class="chip-fact libre">Sin facturar</span>
                      } @else {
                        <span class="chip-fact no" [matTooltip]="v.motivo ?? ''">No facturable</span>
                      }
                    </span>
                    <mat-icon class="flecha">expand_more</mat-icon>
                  </button>
                </div>
                @if (abierta() === v.id) {
                  <div class="detalle">
                    <div class="col">
                      <h4>Pagos</h4>
                      @for (p of v.pagos; track p.id) {
                        <div class="pago">
                          <span class="numeric">{{ p.fecha | date: 'dd/MM/yyyy' }}</span>
                          <span>{{ p.medio }}</span>
                          <span class="ref">{{ p.referencia || 'Sin referencia' }}</span>
                          <b class="numeric">$ {{ money(p.monto) }}</b>
                          @if (p.comprobante_id) {
                            <button mat-button class="mini" (click)="verComprobante(p.comprobante_id)"><mat-icon>image</mat-icon>Comprobante</button>
                          }
                        </div>
                      } @empty {
                        <p class="vacio">Sin pagos registrados.</p>
                      }
                      <p class="saldo numeric">Cobrado $ {{ money(v.pagado) }} · Pendiente $ {{ money(v.pendiente) }}</p>
                    </div>
                    <div class="col">
                      <h4>Factura electrónica</h4>
                      @if (v.factura; as f) {
                        <p><b>{{ f.numero }}</b> · {{ estadoFactura(f.estado) }} · {{ f.fecha | date: 'dd/MM/yyyy' }}</p>
                        <p class="numeric">Total $ {{ money(f.total) }}@if (+f.acreditado > 0) { · Nota de crédito $ {{ money(f.acreditado) }} }</p>
                        <button mat-stroked-button class="mini" (click)="verFactura(f.id)"><mat-icon>open_in_new</mat-icon>Ver factura</button>
                      } @else if (v.facturable) {
                        <p class="vacio">Todavía no tiene factura.</p>
                        @if (puedeFacturar) {
                          <button mat-flat-button class="mini" [disabled]="!datos()?.facturacion_lista" (click)="facturar([v])"><mat-icon>request_quote</mat-icon>Facturar esta venta</button>
                        }
                      } @else {
                        <p class="vacio">{{ v.motivo }}</p>
                      }
                      <a mat-button class="mini" [routerLink]="['/patients', v.patient_id]" [queryParams]="{ tab: 'pagos' }"><mat-icon>account_balance_wallet</mat-icon>Cuenta del paciente</a>
                    </div>
                  </div>
                }
              </div>
            }
          </div>
        </section>
      } @empty {
        <div class="vacio-total glass-card"><mat-icon>receipt_long</mat-icon><p>No hay ventas con estos filtros en el periodo.</p></div>
      }
    }

    @if (seleccion().size) {
      <div class="barra-sel">
        <span><b>{{ seleccion().size }}</b> {{ seleccion().size === 1 ? 'venta' : 'ventas' }} de {{ pacienteSel() }} · $ {{ money(totalSel()) }}</span>
        <button mat-button (click)="limpiarSeleccion()">Quitar selección</button>
        <button mat-flat-button (click)="facturarSeleccion()"><mat-icon>request_quote</mat-icon>Facturar selección</button>
      </div>
    }
  `,
  styles: [
    `
      :host { display: grid; gap: 14px; }
      .kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(160px, 1fr)); gap: 12px; }
      .kpi { display: grid; gap: 2px; padding: 14px 16px;
        span { font-size: .74rem; font-weight: 600; color: var(--color-ink-faint); }
        strong { font-family: var(--font-display); font-size: 1.45rem; letter-spacing: -.02em; }
        small { font-size: .74rem; color: var(--color-ink-soft); }
        .ok { color: var(--color-success); } .alerta { color: var(--color-danger); } .dinero { color: var(--color-accent); } }
      .nota { display: flex; align-items: center; gap: 6px; margin: -4px 0 0; font-size: .8rem; color: var(--color-ink-soft);
        mat-icon { font-size: 17px; width: 17px; height: 17px; color: var(--color-primary); } }
      .aviso { display: flex; align-items: center; gap: 12px; padding: 12px 16px; border-radius: var(--radius-md);
        background: color-mix(in srgb, var(--color-accent) 12%, transparent); font-size: .84rem;
        > mat-icon { color: var(--color-accent); } div { flex: 1; } }
      .filtros { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 12px; padding: 10px 14px; }
      .buscar { display: flex; align-items: center; gap: 6px; flex: 1 1 240px; padding: 6px 12px; border-radius: 999px;
        background: var(--color-surface); border: 1px solid var(--color-border);
        input { flex: 1; border: 0; background: transparent; font: inherit; font-size: .88rem; color: var(--color-ink); outline: none; min-width: 0; }
        mat-icon { color: var(--color-ink-faint); font-size: 19px; width: 19px; height: 19px; } }
      .chips { display: flex; gap: 2px; padding: 2px; border-radius: 999px; background: var(--color-surface-muted);
        button { border: 0; background: transparent; border-radius: 999px; padding: 5px 11px; font: inherit; font-size: .78rem; font-weight: 600;
          color: var(--color-ink-soft); cursor: pointer; }
        button.on { background: var(--color-surface); color: var(--color-ink); box-shadow: 0 1px 4px rgba(0,0,0,.08); } }
      .espacio { flex: 1; }
      .grupo { padding: 4px 0; overflow: hidden;
        > header { display: flex; flex-wrap: wrap; align-items: center; gap: 8px 16px; padding: 12px 16px; border-bottom: 1px solid var(--color-border); } }
      .quien { display: grid; flex: 1 1 200px; a { font-weight: 700; color: var(--color-ink); text-decoration: none; &:hover { color: var(--color-primary); } }
        span { font-size: .76rem; color: var(--color-ink-faint); } }
      .cifras { display: flex; gap: 14px; font-size: .8rem; color: var(--color-ink-soft);
        b { color: var(--color-ink); } .ok { color: var(--color-success); } .alerta { color: var(--color-danger); } }
      .venta { border-bottom: 1px solid var(--color-border); &:last-child { border-bottom: 0; } }
      .venta.anulada { opacity: .55; .concepto b { text-decoration: line-through; } }
      .fila { display: flex; align-items: center; gap: 4px; padding-left: 12px; }
      .sel { width: 16px; height: 16px; accent-color: var(--color-primary); flex-shrink: 0; cursor: pointer; }
      .abrir { flex: 1; min-width: 0; display: grid; grid-template-columns: 70px minmax(0, 1fr) 96px 92px 86px 150px 24px; align-items: center; gap: 10px;
        padding: 10px 12px 10px 6px; border: 0; background: transparent; font: inherit; color: var(--color-ink); text-align: left; cursor: pointer;
        &:hover { background: var(--color-surface-muted); } }
      .fecha { font-size: .8rem; color: var(--color-ink-soft); }
      .concepto { display: grid; min-width: 0; b { font-weight: 600; font-size: .88rem; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
        small { font-size: .74rem; color: var(--color-ink-faint); } }
      .origen { font-size: .72rem; color: var(--color-ink-faint); }
      .monto { text-align: right; font-weight: 600; }
      .estado { justify-self: start; padding: 2px 9px; border-radius: 999px; font-size: .72rem; font-weight: 600; background: var(--color-surface-muted);
        &[data-e='pagada'] { background: var(--color-success-soft); color: var(--color-success); }
        &[data-e='pendiente'] { background: var(--color-danger-soft); color: var(--color-danger); }
        &[data-e='parcial'] { background: color-mix(in srgb, var(--color-accent) 15%, transparent); color: var(--color-accent); } }
      .chip-fact { display: inline-flex; align-items: center; gap: 4px; font-size: .74rem; font-weight: 600; white-space: nowrap;
        mat-icon { font-size: 15px; width: 15px; height: 15px; }
        &.ok { color: var(--color-primary); } &.libre { color: var(--color-accent); } &.no { color: var(--color-ink-faint); } }
      .flecha { color: var(--color-ink-faint); transition: transform .18s ease; }
      .venta.abierta .flecha { transform: rotate(180deg); }
      .detalle { display: grid; grid-template-columns: 1.3fr 1fr; gap: 18px; padding: 4px 18px 16px 46px; animation: abre .18s ease-out;
        h4 { margin: 6px 0 6px; font-size: .74rem; text-transform: uppercase; letter-spacing: .06em; color: var(--color-ink-faint); }
        p { margin: 0 0 6px; font-size: .84rem; } }
      .pago { display: grid; grid-template-columns: 84px minmax(0, 1fr) minmax(0, 1fr) 84px 118px; gap: 8px; align-items: center; padding: 5px 0; font-size: .82rem;
        border-bottom: 1px dashed var(--color-border); .ref { color: var(--color-ink-soft); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; } }
      .saldo { margin-top: 8px !important; color: var(--color-ink-soft); font-size: .8rem !important; }
      .vacio { color: var(--color-ink-faint); }
      .mini { height: 32px; font-size: .78rem; margin: 2px 6px 0 0; mat-icon { font-size: 17px; width: 17px; height: 17px; } }
      .vacio-total { display: grid; justify-items: center; padding: 34px; color: var(--color-ink-faint); p { margin: 6px 0 0; } }
      .barra-sel { position: sticky; bottom: 14px; z-index: 5; display: flex; align-items: center; gap: 10px; padding: 10px 14px;
        border-radius: 999px; background: var(--color-ink); color: #fff; box-shadow: 0 16px 40px -16px rgba(0,0,0,.5); justify-self: center;
        span { padding: 0 6px; font-size: .86rem; } button[mat-button] { color: #fff; } }
      @keyframes abre { from { opacity: 0; transform: translateY(-4px); } }
      @media (max-width: 900px) {
        .abrir { grid-template-columns: 58px minmax(0, 1fr) 80px; grid-template-areas: none; }
        .origen, .estado, .fact, .flecha { display: none; }
        .detalle { grid-template-columns: 1fr; padding-left: 18px; }
        .pago { grid-template-columns: 80px 1fr auto; .ref { display: none; } }
      }
      @media (prefers-reduced-motion: reduce) { .detalle { animation: none; } }
    `,
  ],
})
export class VentasTabComponent implements OnChanges {
  @Input({ required: true }) desde!: string;
  @Input({ required: true }) hasta!: string;

  private readonly http = inject(HttpClient);
  private readonly dialog = inject(MatDialog);
  private readonly snack = inject(MatSnackBar);
  readonly puedeFacturar = inject(AuthService).hasPermission('invoices:write');
  private readonly busqueda = new Subject<string>();

  readonly datos = signal<Ventas | null>(null);
  readonly cargando = signal(true);
  readonly texto = signal('');
  readonly pago = signal<'' | 'pendiente' | 'parcial' | 'pagada' | 'anulada'>('');
  readonly factura = signal<'' | 'facturada' | 'sin_facturar'>('');
  readonly agrupar = signal(true);
  readonly abierta = signal<string | null>(null);
  readonly seleccion = signal(new Set<string>());
  readonly money = formatMoney;

  readonly opcionesPago: ['' | 'pendiente' | 'parcial' | 'pagada' | 'anulada', string][] = [
    ['', 'Todas'], ['pendiente', 'Por cobrar'], ['parcial', 'Abonadas'], ['pagada', 'Pagadas'], ['anulada', 'Anuladas'],
  ];
  readonly opcionesFactura: ['' | 'facturada' | 'sin_facturar', string][] = [['', 'Con y sin factura'], ['facturada', 'Facturadas'], ['sin_facturar', 'Sin facturar']];

  readonly grupos = computed<Grupo[]>(() => {
    const items = this.datos()?.items ?? [];
    if (!this.agrupar()) {
      return items.length
        ? [{ patient_id: '*', paciente: '', cedula: null, ventas: items, total: 0, cobrado: 0, pendiente: 0, facturables: [] }]
        : [];
    }
    const mapa = new Map<string, Grupo>();
    for (const v of items) {
      let g = mapa.get(v.patient_id);
      if (!g) {
        g = { patient_id: v.patient_id, paciente: v.paciente, cedula: v.cedula, ventas: [], total: 0, cobrado: 0, pendiente: 0, facturables: [] };
        mapa.set(v.patient_id, g);
      }
      g.ventas.push(v);
      if (!v.anulada) {
        g.total += +v.monto;
        g.cobrado += +v.pagado;
        g.pendiente += +v.pendiente;
      }
      if (v.facturable) g.facturables.push(v);
    }
    return [...mapa.values()].sort((a, b) => b.total - a.total);
  });

  readonly elegidas = computed(() => (this.datos()?.items ?? []).filter((v) => this.seleccion().has(v.id)));
  readonly pacienteSel = computed(() => this.elegidas()[0]?.paciente ?? '');
  readonly totalSel = computed(() => this.elegidas().reduce((s, v) => s + +v.monto, 0));

  constructor() {
    this.busqueda.pipe(debounceTime(300)).subscribe(() => void this.cargar());
  }

  ngOnChanges(): void {
    void this.cargar();
  }

  limpiarSeleccion(): void {
    this.seleccion.set(new Set());
  }

  buscar(t: string): void {
    this.texto.set(t);
    this.busqueda.next(t);
  }

  private params(): HttpParams {
    let p = new HttpParams().set('desde', this.desde).set('hasta', this.hasta);
    if (this.texto().trim()) p = p.set('q', this.texto().trim());
    if (this.pago()) p = p.set('pago', this.pago());
    if (this.factura()) p = p.set('factura', this.factura());
    return p;
  }

  async cargar(): Promise<void> {
    this.cargando.set(!this.datos());
    try {
      this.datos.set(await firstValueFrom(this.http.get<Ventas>(`${environment.apiUrl}/sales`, { params: this.params() })));
      const vivas = new Set((this.datos()?.items ?? []).filter((v) => v.facturable).map((v) => v.id));
      this.seleccion.set(new Set([...this.seleccion()].filter((id) => vivas.has(id))));
    } catch {
      this.snack.open('No se pudieron cargar las ventas.', 'Cerrar', { duration: 3500 });
    } finally {
      this.cargando.set(false);
    }
  }

  alternar(v: Venta): void {
    const s = new Set(this.seleccion());
    const otroPaciente = this.elegidas().some((x) => x.patient_id !== v.patient_id);
    if (otroPaciente) s.clear();
    if (s.has(v.id)) s.delete(v.id);
    else s.add(v.id);
    if (otroPaciente) this.snack.open('Una factura es de un solo paciente: se cambió la selección.', undefined, { duration: 2500 });
    this.seleccion.set(s);
  }

  async facturar(ventas: Venta[]): Promise<void> {
    if (!ventas.length) return;
    const creada = await openInvoiceCreate(this.dialog, {
      patientId: ventas[0].patient_id,
      patientName: ventas[0].paciente,
      chargeIds: ventas.map((v) => v.id),
    });
    if (creada) {
      this.seleccion.set(new Set());
      await this.cargar();
    }
  }

  facturarGrupo(g: Grupo): Promise<void> {
    return this.facturar(g.facturables);
  }

  facturarSeleccion(): Promise<void> {
    return this.facturar(this.elegidas());
  }

  verFactura(id: string): Promise<void> {
    return openInvoiceDetail(this.dialog, id).then(() => this.cargar());
  }

  async verComprobante(id: string): Promise<void> {
    const ventana = window.open('', '_blank');
    try {
      const blob = await firstValueFrom(this.http.get(`${environment.apiUrl}/portal-receipts/${id}/file`, { responseType: 'blob' }));
      const url = URL.createObjectURL(blob);
      if (ventana) ventana.location.href = url;
      setTimeout(() => URL.revokeObjectURL(url), 60000);
    } catch {
      ventana?.close();
      this.snack.open('No se pudo abrir el comprobante.', 'Cerrar', { duration: 3500 });
    }
  }

  async exportar(): Promise<void> {
    try {
      const blob = await firstValueFrom(
        this.http.get(`${environment.apiUrl}/sales/export.csv`, { params: this.params(), responseType: 'blob' }),
      );
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `ventas-${this.desde}-a-${this.hasta}.csv`;
      a.click();
      setTimeout(() => URL.revokeObjectURL(url), 5000);
    } catch {
      this.snack.open('No se pudo exportar.', 'Cerrar', { duration: 3500 });
    }
  }

  origen(v: Venta): string {
    return ORIGEN[v.origen];
  }

  estadoPago(v: Venta): string {
    return { pendiente: 'Por cobrar', parcial: 'Abonada', pagada: 'Pagada', anulada: 'Anulada' }[v.estado_pago];
  }

  estadoFactura(e: string): string {
    return ESTADO_FACTURA[e] ?? e;
  }
}
