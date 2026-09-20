import { HttpClient } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';
import { Observable } from 'rxjs';

import { environment } from '../../../environments/environment';
import {
  InventoryCatalog,
  InventoryItem,
  StockAlerts,
  StockMovement,
  Supplier,
} from '../models/inventory.models';

export interface ItemInput {
  name: string;
  sku?: string | null;
  category?: string | null;
  unit: string;
  supplier_id?: string | null;
  minimum_stock: string;
  unit_cost?: string | null;
  notes?: string | null;
  is_active: boolean;
}

export interface MovementInput {
  reason: string;
  /** Always positive; the reason carries the direction. */
  quantity: string;
  unit_cost?: string | null;
  lot_number?: string | null;
  expires_on?: string | null;
  patient_id?: string | null;
  notes?: string | null;
}

@Injectable({ providedIn: 'root' })
export class InventoryService {
  private readonly http = inject(HttpClient);
  private readonly base = `${environment.apiUrl}/inventory`;

  getCatalog(): Observable<InventoryCatalog> {
    return this.http.get<InventoryCatalog>(`${this.base}/catalog`);
  }

  listSuppliers(): Observable<Supplier[]> {
    return this.http.get<Supplier[]>(`${this.base}/suppliers`);
  }

  createSupplier(body: Partial<Supplier>): Observable<Supplier> {
    return this.http.post<Supplier>(`${this.base}/suppliers`, body);
  }

  listItems(includeInactive = false): Observable<InventoryItem[]> {
    const query = includeInactive ? '?include_inactive=true' : '';
    return this.http.get<InventoryItem[]>(`${this.base}/items${query}`);
  }

  createItem(body: ItemInput): Observable<InventoryItem> {
    return this.http.post<InventoryItem>(`${this.base}/items`, body);
  }

  updateItem(itemId: string, body: ItemInput): Observable<InventoryItem> {
    return this.http.put<InventoryItem>(`${this.base}/items/${itemId}`, body);
  }

  /** Returns the item with its stock recomputed, so the caller never adds up
   *  the ledger itself. */
  recordMovement(itemId: string, body: MovementInput): Observable<InventoryItem> {
    return this.http.post<InventoryItem>(`${this.base}/items/${itemId}/movements`, body);
  }

  listMovements(itemId?: string): Observable<StockMovement[]> {
    const query = itemId ? `?item_id=${itemId}` : '';
    return this.http.get<StockMovement[]>(`${this.base}/movements${query}`);
  }

  getAlerts(): Observable<StockAlerts> {
    return this.http.get<StockAlerts>(`${this.base}/alerts`);
  }
}
