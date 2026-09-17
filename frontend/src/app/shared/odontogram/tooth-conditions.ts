export interface ToothConditionDef {
  code: string;
  label: string;
  color: string;
  /** Whole-tooth conditions render as a symbol over the tooth instead of a surface fill. */
  wholeToothOnly?: boolean;
}

export const TOOTH_CONDITIONS: ToothConditionDef[] = [
  { code: 'sano', label: 'Sano', color: 'transparent' },
  { code: 'caries', label: 'Caries', color: '#e53935' },
  { code: 'restauracion', label: 'Restauración', color: '#1e88e5' },
  { code: 'restauracion_defectuosa', label: 'Restauración defectuosa', color: '#fb8c00' },
  { code: 'corona', label: 'Corona', color: '#fdd835', wholeToothOnly: true },
  { code: 'puente', label: 'Puente', color: '#8e24aa', wholeToothOnly: true },
  { code: 'implante', label: 'Implante', color: '#00897b', wholeToothOnly: true },
  { code: 'ausente', label: 'Ausente', color: '#9e9e9e', wholeToothOnly: true },
  { code: 'extraccion_indicada', label: 'Extracción indicada', color: '#fb8c00', wholeToothOnly: true },
  { code: 'extraccion_realizada', label: 'Extracción realizada', color: '#757575', wholeToothOnly: true },
  { code: 'endodoncia', label: 'Endodoncia', color: '#6d4c41', wholeToothOnly: true },
  { code: 'fractura', label: 'Fractura', color: '#212121' },
  { code: 'sellante', label: 'Sellante', color: '#7cb342' },
  { code: 'protesis', label: 'Prótesis', color: '#3949ab', wholeToothOnly: true },
  { code: 'movilidad', label: 'Movilidad', color: '#d81b60', wholeToothOnly: true },
  { code: 'diente_retenido', label: 'Diente retenido', color: '#795548', wholeToothOnly: true },
  { code: 'tratamiento_pendiente', label: 'Tratamiento pendiente', color: '#fdd835' },
  { code: 'tratamiento_realizado', label: 'Tratamiento realizado', color: '#43a047' },
];

export const TOOTH_CONDITION_BY_CODE: Record<string, ToothConditionDef> = Object.fromEntries(
  TOOTH_CONDITIONS.map((c) => [c.code, c]),
);

export const SURFACE_LABELS: Record<string, string> = {
  whole: 'Diente completo',
  mesial: 'Mesial',
  distal: 'Distal',
  vestibular: 'Vestibular',
  lingual: 'Lingual/Palatina',
  oclusal: 'Oclusal/Incisal',
};
