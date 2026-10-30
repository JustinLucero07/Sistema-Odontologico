import { DatePipe } from '@angular/common';
import { Component, OnInit, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTabsModule } from '@angular/material/tabs';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { formatMoney } from '../../core/models/finance.models';
import { INVOICE_STATUS_LABELS, Invoice, InvoiceStatus, InvoicingSettings } from '../../core/models/invoicing.models';
import { InvoicingService } from '../../core/services/invoicing.service';
import { confirmAction } from '../../shared/confirm-dialog/confirm-dialog.component';
import { openInvoiceCreate } from '../../shared/invoicing/invoice-create-dialog.component';
import { openInvoiceDetail } from '../../shared/invoicing/invoice-detail-dialog.component';
import { SkeletonComponent } from '../../shared/skeleton/skeleton.component';

type Filter = 'todos' | 'problemas' | 'en_curso' | InvoiceStatus;

@Component({
  selector: 'app-invoicing-page',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSlideToggleModule,
    MatTabsModule,
    SkeletonComponent,
  ],
  templateUrl: './invoicing-page.component.html',
  styleUrl: './invoicing-page.component.scss',
})
export class InvoicingPageComponent implements OnInit {
  private readonly service = inject(InvoicingService);
  private readonly dialog = inject(MatDialog);
  private readonly snackBar = inject(MatSnackBar);
  readonly auth = inject(AuthService);

  readonly money = formatMoney;
  readonly labels = INVOICE_STATUS_LABELS;
  readonly canWrite = this.auth.hasPermission('invoices:write');
  readonly canConfigure = this.auth.hasPermission('settings:manage');

  readonly invoices = signal<Invoice[]>([]);
  readonly settings = signal<InvoicingSettings | null>(null);
  readonly loading = signal(true);
  readonly filter = signal<Filter>('todos');
  readonly search = signal('');
  readonly docType = signal<'' | '01' | '04'>('');
  readonly saving = signal(false);

  // Configuración.
  certFile: File | null = null;
  certPassword = '';
  nextNumber: number | null = null;
  retentionAgent = '';

  readonly filters: { code: Filter; label: string }[] = [
    { code: 'todos', label: 'Todos' },
    { code: 'autorizada', label: 'Autorizadas' },
    { code: 'en_curso', label: 'En proceso' },
    { code: 'problemas', label: 'Con problemas' },
    { code: 'descartada', label: 'Descartadas' },
  ];

  private matches(f: Invoice, code: Filter): boolean {
    if (code === 'todos') return true;
    if (code === 'problemas') return f.status === 'devuelta' || f.status === 'no_autorizada';
    if (code === 'en_curso') return f.status === 'pendiente' || f.status === 'recibida';
    return f.status === code;
  }

  readonly visible = computed(() => {
    const term = this.search().trim().toLowerCase();
    return this.invoices().filter(
      (f) =>
        this.matches(f, this.filter()) &&
        (!this.docType() || f.doc_type === this.docType()) &&
        (!term || f.buyer_name.toLowerCase().includes(term) || f.buyer_id.includes(term) || f.number.includes(term)),
    );
  });

  readonly kpis = computed(() => {
    const now = new Date();
    const month = `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, '0')}`;
    let billed = 0;
    let credited = 0;
    for (const f of this.invoices()) {
      if (f.status !== 'autorizada' || !f.issue_date.startsWith(month)) continue;
      if (f.doc_type === '01') billed += +f.total;
      else credited += +f.total;
    }
    return {
      billed,
      credited,
      inProgress: this.invoices().filter((f) => this.matches(f, 'en_curso')).length,
      problems: this.invoices().filter((f) => this.matches(f, 'problemas')).length,
    };
  });

  /** Días hasta que vence la firma (solo si está vigente). */
  readonly certDaysLeft = computed(() => {
    const s = this.settings();
    if (!s?.certificate_valid_until || s.certificate_expired) return null;
    return Math.floor((new Date(s.certificate_valid_until).getTime() - Date.now()) / 86_400_000);
  });

  count(code: Filter): number {
    return this.invoices().filter((f) => this.matches(f, code)).length;
  }

  async ngOnInit(): Promise<void> {
    await this.reload();
  }

  async reload(): Promise<void> {
    try {
      const [list, settings] = await Promise.all([
        firstValueFrom(this.service.list()),
        firstValueFrom(this.service.settings()),
      ]);
      this.invoices.set(list);
      this.applySettings(settings);
    } finally {
      this.loading.set(false);
    }
  }

  private applySettings(s: InvoicingSettings): void {
    this.settings.set(s);
    this.nextNumber = s.next_invoice_number;
    this.retentionAgent = s.retention_agent ?? '';
  }

  async newInvoice(): Promise<void> {
    const created = await openInvoiceCreate(this.dialog);
    if (created) {
      await this.reload();
      await openInvoiceDetail(this.dialog, created.id);
      await this.reload();
    }
  }

  async open(f: Invoice): Promise<void> {
    await openInvoiceDetail(this.dialog, f.id);
    await this.reload();
  }

  // ---- Configuración ----------------------------------------------------

  private report(err: unknown, fallback: string): void {
    const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
    this.snackBar.open(typeof detail === 'string' ? detail : fallback, 'Cerrar', { duration: 7000 });
  }

  onFile(event: Event): void {
    this.certFile = (event.target as HTMLInputElement).files?.[0] ?? null;
  }

  async uploadCertificate(): Promise<void> {
    if (!this.certFile || !this.certPassword) return;
    this.saving.set(true);
    try {
      this.applySettings(await firstValueFrom(this.service.uploadCertificate(this.certFile, this.certPassword)));
      this.certFile = null;
      this.certPassword = '';
      this.snackBar.open('Firma electrónica guardada (cifrada)', 'Cerrar', { duration: 4000 });
    } catch (err) {
      this.report(err, 'No se pudo guardar la firma.');
    } finally {
      this.saving.set(false);
    }
  }

  async deleteCertificate(): Promise<void> {
    const ok = await confirmAction(this.dialog, {
      title: '¿Quitar la firma electrónica?',
      message: 'Sin firma no se puede facturar hasta subir otra.',
      confirmLabel: 'Quitar',
      danger: true,
    });
    if (!ok) return;
    this.applySettings(await firstValueFrom(this.service.deleteCertificate()));
  }

  async setEnvironment(env: '1' | '2'): Promise<void> {
    if (env === this.settings()?.environment) return;
    if (env === '2') {
      const ok = await confirmAction(this.dialog, {
        title: '¿Pasar a producción?',
        message:
          'Desde ahora las facturas tendrán validez tributaria ante el SRI. Hágalo solo cuando el SRI ya le haya habilitado la producción en «SRI en línea» y sus facturas de prueba salgan autorizadas.',
        confirmLabel: 'Pasar a producción',
      });
      if (!ok) return;
    }
    await this.save({ environment: env });
  }

  async save(body: Parameters<InvoicingService['saveSettings']>[0]): Promise<void> {
    this.saving.set(true);
    try {
      this.applySettings(await firstValueFrom(this.service.saveSettings(body)));
      this.snackBar.open('Configuración guardada', 'Cerrar', { duration: 2500 });
    } catch (err) {
      this.report(err, 'No se pudo guardar.');
      const s = this.settings();
      if (s) this.applySettings(s);
    } finally {
      this.saving.set(false);
    }
  }
}
