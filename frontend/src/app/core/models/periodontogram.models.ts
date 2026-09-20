export type PeriodontalSite =
  | 'vestibular_distal'
  | 'vestibular_central'
  | 'vestibular_mesial'
  | 'lingual_distal'
  | 'lingual_central'
  | 'lingual_mesial';

/** Buccal wall first, then lingual/palatal — the order a probe walks a tooth. */
export const BUCCAL_SITES: PeriodontalSite[] = [
  'vestibular_distal',
  'vestibular_central',
  'vestibular_mesial',
];
export const LINGUAL_SITES: PeriodontalSite[] = [
  'lingual_distal',
  'lingual_central',
  'lingual_mesial',
];
export const ALL_SITES: PeriodontalSite[] = [...BUCCAL_SITES, ...LINGUAL_SITES];

export interface PeriodontalMeasurement {
  id?: string;
  fdi_number: string;
  site: PeriodontalSite;
  probing_depth: number | null;
  recession: number | null;
  bleeding: boolean;
  suppuration: boolean;
  plaque: boolean;
  /** Derived server-side: probing depth + recession, null unless both exist. */
  attachment_level?: number | null;
}

export interface PeriodontalTooth {
  id?: string;
  fdi_number: string;
  absent: boolean;
  implant: boolean;
  mobility: number | null;
  furcation: number | null;
  notes: string | null;
}

export interface PeriodontalIndices {
  sites_recorded: number;
  bleeding_sites: number;
  plaque_sites: number;
  bleeding_index: number;
  plaque_index: number;
  mean_probing_depth: number | null;
  max_probing_depth: number | null;
  sites_over_3mm: number;
  sites_over_5mm: number;
}

export interface Periodontogram {
  id: string;
  patient_id: string;
  professional_id: string | null;
  created_by_id: string | null;
  created_at: string;
  previous_periodontogram_id: string | null;
  notes: string | null;
  type: 'initial' | 'followup';
  teeth: PeriodontalTooth[];
  measurements: PeriodontalMeasurement[];
  indices: PeriodontalIndices;
}

export interface PeriodontogramSummary {
  id: string;
  created_at: string;
  type: 'initial' | 'followup';
}

export interface PeriodontogramCreate {
  professional_id?: string | null;
  notes?: string | null;
  teeth: PeriodontalTooth[];
  measurements: Omit<PeriodontalMeasurement, 'id' | 'attachment_level'>[];
}

/** Thresholds used to colour a pocket reading. These are the conventional
 *  cut-offs: up to 3 mm is a healthy sulcus, 4–5 mm is a pocket that needs
 *  attention, 6 mm and beyond is advanced. */
export const POCKET_THRESHOLDS = { healthy: 3, moderate: 5 } as const;

export function pocketSeverity(depth: number | null): 'none' | 'healthy' | 'moderate' | 'severe' {
  if (depth === null) return 'none';
  if (depth <= POCKET_THRESHOLDS.healthy) return 'healthy';
  if (depth <= POCKET_THRESHOLDS.moderate) return 'moderate';
  return 'severe';
}
