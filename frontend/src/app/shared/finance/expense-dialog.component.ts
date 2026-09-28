import { Component, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MAT_DIALOG_DATA, MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { firstValueFrom } from 'rxjs';

import { Expense, ExpenseCategory, PaymentMethodOption } from '../../core/models/finance.models';
import { FinanceService } from '../../core/services/finance.service';
import { InventoryService } from '../../core/services/inventory.service';

function today(): string {
  const d = new Date();
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

/** Registrar o corregir un egreso. Al editar, el importe y el medio quedan
 *  fijos: se corrigen anulando y registrando de nuevo, para no descuadrar la
 *  caja del día en que se pagó. */
@Component({
  selector: 'app-expense-dialog',
  standalone: true,
  imports: [
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
  ],
  template: `
    <h2 mat-dialog-title>{{ data.expense ? 'Editar egreso' : 'Registrar egreso' }}</h2>
    <form [formGroup]="form" (ngSubmit)="save()">
      <mat-dialog-content>
        <div class="dialog-grid">
          <mat-form-field appearance="outline" class="full">
            <mat-label>Concepto</mat-label>
            <input matInput formControlName="description" placeholder="Ej. Resinas y adhesivo" />
            <mat-error>Escriba en qué se gastó</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Categoría</mat-label>
            <mat-select formControlName="category">
              @for (c of categories(); track c.code) {
                <mat-option [value]="c.code">{{ c.label }}</mat-option>
              }
            </mat-select>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Fecha</mat-label>
            <input matInput type="date" formControlName="spent_on" [max]="maxDate" />
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Importe</mat-label>
            <span matTextPrefix>$&nbsp;</span>
            <input matInput formControlName="amount" inputmode="decimal" placeholder="0.00" />
            <mat-error>Importe mayor que cero</mat-error>
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Medio de pago</mat-label>
            <mat-select formControlName="method">
              @for (m of methods(); track m.code) {
                <mat-option [value]="m.code">{{ m.label }}</mat-option>
              }
            </mat-select>
            @if (form.controls.method.value === 'efectivo' && form.controls.spent_on.value === maxDate && !data.expense) {
              <mat-hint>{{ cashOpen() ? 'Sale de la caja abierta de hoy' : 'No hay caja abierta: no se descuenta de ninguna' }}</mat-hint>
            }
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>Proveedor</mat-label>
            @if (suppliers().length > 0) {
              <mat-select formControlName="supplier_id">
                <mat-option value="">Otro / sin registrar</mat-option>
                @for (s of suppliers(); track s.id) {
                  <mat-option [value]="s.id">{{ s.name }}</mat-option>
                }
              </mat-select>
            } @else {
              <input matInput formControlName="supplier_name" />
            }
          </mat-form-field>

          <mat-form-field appearance="outline">
            <mat-label>N.° de factura o comprobante</mat-label>
            <input matInput formControlName="receipt_number" placeholder="001-001-000000123" />
            <mat-hint>Respaldo para el contador</mat-hint>
          </mat-form-field>

          @if (suppliers().length > 0 && !form.controls.supplier_id.value) {
            <mat-form-field appearance="outline" class="full">
              <mat-label>Nombre del proveedor (opcional)</mat-label>
              <input matInput formControlName="supplier_name" />
            </mat-form-field>
          }

          <mat-form-field appearance="outline" class="full">
            <mat-label>Notas</mat-label>
            <textarea matInput formControlName="notes" rows="2"></textarea>
          </mat-form-field>
        </div>
        @if (data.expense) {
          <p class="dialog-note">
            El importe y el medio de pago no se cambian: si están mal, anule este egreso y regístrelo de nuevo.
          </p>
        }
        @if (error()) {
          <p class="dialog-error">{{ error() }}</p>
        }
      </mat-dialog-content>
      <mat-dialog-actions align="end">
        <button mat-button type="button" mat-dialog-close>Cancelar</button>
        <button mat-flat-button type="submit" [disabled]="saving()">
          {{ saving() ? 'Guardando…' : data.expense ? 'Guardar cambios' : 'Registrar egreso' }}
        </button>
      </mat-dialog-actions>
    </form>
  `,
})
export class ExpenseDialogComponent implements OnInit {
  readonly data = inject<{ expense: Expense | null }>(MAT_DIALOG_DATA);
  private readonly ref = inject(MatDialogRef<ExpenseDialogComponent, Expense>);
  private readonly finance = inject(FinanceService);
  private readonly inventory = inject(InventoryService);

  readonly categories = signal<ExpenseCategory[]>([]);
  readonly methods = signal<PaymentMethodOption[]>([]);
  readonly suppliers = signal<{ id: string; name: string }[]>([]);
  readonly saving = signal(false);
  readonly cashOpen = signal(false);
  readonly error = signal<string | null>(null);
  readonly maxDate = today();

  readonly form = inject(FormBuilder).nonNullable.group({
    description: ['', Validators.required],
    category: ['insumos', Validators.required],
    spent_on: [today(), Validators.required],
    amount: ['', [Validators.required, Validators.pattern(/^\d+([.,]\d{1,2})?$/)]],
    method: ['efectivo'],
    supplier_id: [''],
    supplier_name: [''],
    receipt_number: [''],
    notes: [''],
  });

  async ngOnInit(): Promise<void> {
    const e = this.data.expense;
    if (e) {
      this.form.reset({
        description: e.description,
        category: e.category,
        spent_on: e.spent_on,
        amount: e.amount,
        method: e.method,
        supplier_id: e.supplier_id ?? '',
        supplier_name: e.supplier_id ? '' : e.supplier_name ?? '',
        receipt_number: e.receipt_number ?? '',
        notes: e.notes ?? '',
      });
      this.form.controls.amount.disable();
      this.form.controls.method.disable();
    }
    const [categories, methods] = await Promise.all([
      firstValueFrom(this.finance.getExpenseCategories()),
      firstValueFrom(this.finance.getMethods()),
    ]);
    this.categories.set(categories);
    this.methods.set(methods);
    try {
      this.cashOpen.set((await firstValueFrom(this.finance.getOpenCashSession())) !== null);
    } catch {
      this.cashOpen.set(false);
    }
    try {
      // Si el usuario no ve inventario, el proveedor se escribe a mano.
      this.suppliers.set((await firstValueFrom(this.inventory.listSuppliers())).filter((s) => s.is_active));
    } catch {
      this.suppliers.set([]);
    }
  }

  async save(): Promise<void> {
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    const v = this.form.getRawValue();
    if (!this.data.expense && Number(v.amount.replace(',', '.')) <= 0) {
      this.form.controls.amount.setErrors({ min: true });
      return;
    }
    this.saving.set(true);
    this.error.set(null);
    const body = {
      spent_on: v.spent_on,
      category: v.category,
      description: v.description.trim(),
      supplier_id: v.supplier_id || null,
      supplier_name: v.supplier_id ? null : v.supplier_name.trim() || null,
      receipt_number: v.receipt_number.trim() || null,
      notes: v.notes.trim() || null,
    };
    try {
      const saved = this.data.expense
        ? await firstValueFrom(this.finance.updateExpense(this.data.expense.id, body))
        : await firstValueFrom(
            this.finance.createExpense({ ...body, amount: v.amount.replace(',', '.'), method: v.method as never }),
          );
      this.ref.close(saved);
    } catch (err: unknown) {
      const detail = (err as { error?: { detail?: unknown } })?.error?.detail;
      this.error.set(typeof detail === 'string' ? detail : 'No se pudo guardar el egreso.');
    } finally {
      this.saving.set(false);
    }
  }
}

export function openExpenseDialog(dialog: MatDialog, expense: Expense | null = null): Promise<Expense | undefined> {
  return firstValueFrom(
    dialog
      .open(ExpenseDialogComponent, {
        data: { expense },
        width: '640px',
        maxWidth: '96vw',
        autoFocus: 'first-tabbable',
        panelClass: 'app-dialog',
      })
      .afterClosed(),
  );
}
