export interface ToothLayout {
  fdi: string;
  arch: 'upper' | 'lower';
  mesialSide: 'left' | 'right';
}

function quadrantRow(quadrants: number[], teethPerQuadrant: number, arch: 'upper' | 'lower'): ToothLayout[] {
  const row: ToothLayout[] = [];
  quadrants.forEach((quadrant, qIndex) => {
    const mesialSide: 'left' | 'right' = qIndex === 0 ? 'right' : 'left';
    const numbers =
      qIndex === 0
        ? Array.from({ length: teethPerQuadrant }, (_, i) => teethPerQuadrant - i) // descending toward midline
        : Array.from({ length: teethPerQuadrant }, (_, i) => i + 1); // ascending away from midline
    for (const n of numbers) {
      row.push({ fdi: `${quadrant}${n}`, arch, mesialSide });
    }
  });
  return row;
}

export const PERMANENT_UPPER: ToothLayout[] = quadrantRow([1, 2], 8, 'upper');
export const PERMANENT_LOWER: ToothLayout[] = quadrantRow([4, 3], 8, 'lower');

export const TEMPORARY_UPPER: ToothLayout[] = quadrantRow([5, 6], 5, 'upper');
export const TEMPORARY_LOWER: ToothLayout[] = quadrantRow([8, 7], 5, 'lower');
