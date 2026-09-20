export interface StockUnit {
  code: string;
  label: string;
}

export interface MovementReason {
  code: string;
  label: string;
  /** +1 adds to stock, −1 removes. Fixed by the reason, never chosen. */
  sign: number;
}

export interface InventoryCatalog {
  units: StockUnit[];
  reasons: MovementReason[];
}

export interface Supplier {
  id: string;
  name: string;
  contact_name: string | null;
  phone: string | null;
  email: string | null;
  notes: string | null;
  is_active: boolean;
}

export interface InventoryItem {
  id: string;
  name: string;
  sku: string | null;
  category: string | null;
  unit: string;
  supplier_id: string | null;
  supplier_name: string | null;
  minimum_stock: string;
  unit_cost: string | null;
  is_active: boolean;
  notes: string | null;
  /** Summed from the movement ledger server-side; never a stored column. */
  on_hand: string;
  below_minimum: boolean;
  next_expiry: string | null;
  expired_quantity: string;
}

export interface StockMovement {
  id: string;
  item_id: string;
  item_name: string;
  reason: string;
  quantity: string;
  sign: number;
  unit_cost: string | null;
  lot_number: string | null;
  expires_on: string | null;
  patient_id: string | null;
  notes: string | null;
  created_by_id: string | null;
  created_at: string;
}

export interface StockAlerts {
  below_minimum: InventoryItem[];
  expiring_soon: InventoryItem[];
  expired: InventoryItem[];
}

/** Quantities travel as strings so three decimals survive the round trip. */
export function formatQuantity(value: string | number): string {
  const n = typeof value === 'number' ? value : Number(value);
  // Whole counts read as "12", not "12,000" — boxes are not measured in grams.
  return Number.isInteger(n)
    ? String(n)
    : new Intl.NumberFormat('es', { maximumFractionDigits: 3 }).format(n);
}
