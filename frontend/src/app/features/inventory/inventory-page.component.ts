import { DatePipe } from '@angular/common';
import { Component, HostListener, OnInit, computed, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatMenuModule } from '@angular/material/menu';
import { MatSelectModule } from '@angular/material/select';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import {
  InventoryCatalog,
  InventoryItem,
  StockAlerts,
  StockMovement,
  Supplier,
  formatQuantity,
} from '../../core/models/inventory.models';
import { InventoryService } from '../../core/services/inventory.service';

@Component({
  selector: 'app-inventory-page',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatMenuModule,
    MatSelectModule,
    MatTooltipModule,
  ],
  templateUrl: './inventory-page.component.html',
  styleUrl: './inventory-page.component.scss',
})
export class InventoryPageComponent implements OnInit {
  private readonly inventory = inject(InventoryService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  readonly auth = inject(AuthService);

  readonly items = signal<InventoryItem[]>([]);
  readonly suppliers = signal<Supplier[]>([]);
  readonly catalog = signal<InventoryCatalog>({ units: [], reasons: [] });
  readonly alerts = signal<StockAlerts | null>(null);
  readonly movements = signal<StockMovement[]>([]);
  readonly loading = signal(true);
  readonly saving = signal(false);

  readonly showItemForm = signal(false);
  /** Artículo que se edita; null cuando el panel crea uno nuevo. */
  readonly editingItem = signal<InventoryItem | null>(null);
  readonly showInactive = signal(false);
  readonly showSuppliers = signal(false);
  readonly editingSupplier = signal<Supplier | 'new' | null>(null);
  readonly movingItem = signal<InventoryItem | null>(null);
  readonly historyItem = signal<InventoryItem | null>(null);
  readonly search = signal('');
  readonly onlyAlerts = signal(false);

  readonly qty = formatQuantity;

  readonly itemForm = this.fb.nonNullable.group({
    name: ['', Validators.required],
    sku: [''],
    category: [''],
    unit: ['unidad', Validators.required],
    supplier_id: [''],
    minimum_stock: ['0'],
    unit_cost: [''],
    notes: [''],
  });

  readonly supplierForm = this.fb.nonNullable.group({
    name: ['', Validators.required],
    contact_name: [''],
    phone: [''],
    email: ['', Validators.email],
    notes: [''],
  });

  readonly activeSuppliers = computed(() => this.suppliers().filter((s) => s.is_active));

  readonly movementForm = this.fb.nonNullable.group({
    reason: ['compra', Validators.required],
    quantity: ['', [Validators.required, Validators.pattern(/^\d+([.,]\d{1,3})?$/)]],
    lot_number: [''],
    expires_on: [''],
    unit_cost: [''],
    notes: [''],
  });

  get canWrite(): boolean {
    return this.auth.hasPermission('inventory:write');
  }

  readonly visibleItems = computed(() => {
    const term = this.search().trim().toLowerCase();
    return this.items().filter((item) => {
      if (this.onlyAlerts() && !item.below_minimum && Number(item.expired_quantity) === 0) {
        return false;
      }
      if (!term) return true;
      return (
        item.name.toLowerCase().includes(term) ||
        (item.sku ?? '').toLowerCase().includes(term) ||
        (item.category ?? '').toLowerCase().includes(term)
      );
    });
  });

  readonly alertCount = computed(() => {
    const a = this.alerts();
    if (!a) return 0;
    // An item can be both low and expiring; counting the union avoids a badge
    // that claims more problems than there are.
    return new Set([
      ...a.below_minimum.map((i) => i.id),
      ...a.expiring_soon.map((i) => i.id),
      ...a.expired.map((i) => i.id),
    ]).size;
  });

  /** The chosen reason decides whether stock goes up or down; the form shows
   *  it so nobody has to remember which way "merma" points. */
  readonly movementSign = computed(() => {
    const code = this.movementForm.controls.reason.value;
    return this.catalog().reasons.find((r) => r.code === code)?.sign ?? 1;
  });

  /** Esc cierra cualquier ventana abierta, como en un diálogo normal. */
  @HostListener('document:keydown.escape')
  closePanels(): void {
    this.showItemForm.set(false);
    this.movingItem.set(null);
    this.historyItem.set(null);
    this.showSuppliers.set(false);
  }

  async ngOnInit(): Promise<void> {
    this.catalog.set(await firstValueFrom(this.inventory.getCatalog()));
    await this.reload();
  }

  private async reload(): Promise<void> {
    this.loading.set(true);
    try {
      const [items, suppliers, alerts] = await Promise.all([
        firstValueFrom(this.inventory.listItems(this.showInactive())),
        firstValueFrom(this.inventory.listSuppliers()),
        firstValueFrom(this.inventory.getAlerts()),
      ]);
      this.items.set(items);
      this.suppliers.set(suppliers);
      this.alerts.set(alerts);
    } finally {
      this.loading.set(false);
    }
  }

  unitLabel(code: string): string {
    return this.catalog().units.find((u) => u.code === code)?.label ?? code;
  }

  reasonLabel(code: string): string {
    return this.catalog().reasons.find((r) => r.code === code)?.label ?? code;
  }

  private normalize(raw: string): string {
    return raw.replace(',', '.');
  }

  async toggleInactive(): Promise<void> {
    this.showInactive.set(!this.showInactive());
    await this.reload();
  }

  openItemForm(item: InventoryItem | null = null): void {
    this.editingItem.set(item);
    this.itemForm.reset({
      name: item?.name ?? '',
      sku: item?.sku ?? '',
      category: item?.category ?? '',
      unit: item?.unit ?? 'unidad',
      supplier_id: item?.supplier_id ?? '',
      minimum_stock: item ? formatQuantity(item.minimum_stock) : '0',
      unit_cost: item?.unit_cost ?? '',
      notes: item?.notes ?? '',
    });
    this.showItemForm.set(true);
  }

  private itemPayload(isActive: boolean) {
    const raw = this.itemForm.getRawValue();
    return {
      name: raw.name,
      sku: raw.sku || null,
      category: raw.category || null,
      unit: raw.unit,
      supplier_id: raw.supplier_id || null,
      minimum_stock: this.normalize(raw.minimum_stock || '0'),
      unit_cost: raw.unit_cost ? this.normalize(raw.unit_cost) : null,
      notes: raw.notes || null,
      is_active: isActive,
    };
  }

  async submitItem(): Promise<void> {
    if (this.itemForm.invalid || this.saving()) return;
    this.saving.set(true);
    const editing = this.editingItem();
    try {
      if (editing) {
        await firstValueFrom(this.inventory.updateItem(editing.id, this.itemPayload(editing.is_active)));
      } else {
        await firstValueFrom(this.inventory.createItem(this.itemPayload(true)));
      }
      this.showItemForm.set(false);
      await this.reload();
      this.snackBar.open(editing ? 'Artículo actualizado' : 'Artículo creado', 'Cerrar', { duration: 3000 });
    } catch (error) {
      this.report(error, 'No se pudo guardar el artículo');
    } finally {
      this.saving.set(false);
    }
  }

  /** Desactivar lo saca de la lista y de las alertas; su historial se queda. */
  async toggleItemActive(item: InventoryItem): Promise<void> {
    this.editingItem.set(item);
    this.itemForm.reset({
      name: item.name,
      sku: item.sku ?? '',
      category: item.category ?? '',
      unit: item.unit,
      supplier_id: item.supplier_id ?? '',
      minimum_stock: formatQuantity(item.minimum_stock),
      unit_cost: item.unit_cost ?? '',
      notes: item.notes ?? '',
    });
    try {
      await firstValueFrom(this.inventory.updateItem(item.id, this.itemPayload(!item.is_active)));
      this.snackBar.open(item.is_active ? `${item.name} desactivado` : `${item.name} reactivado`, 'Cerrar', {
        duration: 3000,
      });
      await this.reload();
    } catch (error) {
      this.report(error, 'No se pudo cambiar el artículo');
    }
  }

  // ---- Proveedores -------------------------------------------------------

  editSupplier(supplier: Supplier | 'new'): void {
    const s = supplier === 'new' ? null : supplier;
    this.supplierForm.reset({
      name: s?.name ?? '',
      contact_name: s?.contact_name ?? '',
      phone: s?.phone ?? '',
      email: s?.email ?? '',
      notes: s?.notes ?? '',
    });
    this.editingSupplier.set(supplier);
  }

  async saveSupplier(): Promise<void> {
    const target = this.editingSupplier();
    if (!target || this.supplierForm.invalid || this.saving()) {
      this.supplierForm.markAllAsTouched();
      return;
    }
    this.saving.set(true);
    const raw = this.supplierForm.getRawValue();
    const body = {
      name: raw.name.trim(),
      contact_name: raw.contact_name || null,
      phone: raw.phone || null,
      email: raw.email || null,
      notes: raw.notes || null,
    };
    try {
      if (target === 'new') {
        await firstValueFrom(this.inventory.createSupplier({ ...body, is_active: true }));
      } else {
        await firstValueFrom(this.inventory.updateSupplier(target.id, { ...body, is_active: target.is_active }));
      }
      this.editingSupplier.set(null);
      await this.reload();
    } catch (error) {
      this.report(error, 'No se pudo guardar el proveedor');
    } finally {
      this.saving.set(false);
    }
  }

  async toggleSupplier(supplier: Supplier): Promise<void> {
    await firstValueFrom(
      this.inventory.updateSupplier(supplier.id, { ...supplier, is_active: !supplier.is_active }),
    );
    await this.reload();
  }

  openMovement(item: InventoryItem): void {
    this.movingItem.set(item);
    this.movementForm.reset({ reason: 'compra', quantity: '' });
  }

  async submitMovement(): Promise<void> {
    const item = this.movingItem();
    if (!item || this.movementForm.invalid || this.saving()) return;
    this.saving.set(true);
    try {
      const raw = this.movementForm.getRawValue();
      const updated = await firstValueFrom(
        this.inventory.recordMovement(item.id, {
          reason: raw.reason,
          quantity: this.normalize(raw.quantity),
          lot_number: raw.lot_number || null,
          expires_on: raw.expires_on || null,
          unit_cost: raw.unit_cost ? this.normalize(raw.unit_cost) : null,
          notes: raw.notes || null,
        }),
      );
      this.movingItem.set(null);
      await this.reload();
      this.snackBar.open(
        `${item.name}: quedan ${formatQuantity(updated.on_hand)} ${this.unitLabel(item.unit)}`,
        'Cerrar',
        { duration: 4000 },
      );
    } catch (error) {
      this.report(error, 'No se pudo registrar el movimiento');
    } finally {
      this.saving.set(false);
    }
  }

  async openHistory(item: InventoryItem): Promise<void> {
    this.historyItem.set(item);
    this.movements.set(await firstValueFrom(this.inventory.listMovements(item.id)));
  }

  /** The API says exactly how much is left and how much was asked for; our own
   *  wording would lose that. */
  private report(error: unknown, fallback: string): void {
    const detail = (error as { error?: { detail?: unknown } })?.error?.detail;
    this.snackBar.open(typeof detail === 'string' ? detail : fallback, 'Cerrar', {
      duration: 8000,
    });
  }
}
