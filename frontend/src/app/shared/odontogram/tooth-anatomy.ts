/** Anatomical tooth silhouettes for the chart's figure row.
 *
 * Drawn in a canonical 40 × 64 viewBox with the crown at the BOTTOM
 * (y ≈ 36–60) and the roots at the TOP (y ≈ 2–37), i.e. an upper-arch tooth.
 * Lower-arch teeth reuse the same paths flipped vertically, which is how
 * printed dental charts mirror the two arches around the midline.
 *
 * Three rules keep the figures from looking like clip art:
 *   1. the root's base width EQUALS the crown's cervical width, so the two
 *      meet without a shoulder — a tooth has no step at the gum line;
 *   2. the root is the LONGER half and tapers to a fine apex; a stubby root
 *      reads as a cartoon;
 *   3. the crown flares out below the cervix and is widest at its occlusal
 *      third, which is the bulge you feel with a tongue.
 *
 * Proportions follow real dentition, because a dentist reads these shapes the
 * way a driver reads road signs:
 *   · incisors are shovel-shaped with a flat incisal edge and one conical root;
 *   · canines a single pointed cusp on the longest root in the mouth;
 *   · premolars two cusps split by a central groove, on one root;
 *   · upper molars three splayed roots, lower molars two broader ones — and
 *     the outer roots CURVE away from the midline, as they do in a radiograph;
 *   · third molars are visibly smaller than first molars.
 */

export type ToothType = 'incisor' | 'canine' | 'premolar' | 'molar';

export interface ToothAnatomy {
  crown: string;
  roots: string[];
  /** Stroked anatomical landmarks: the cementoenamel junction and the grooves
   *  between cusps. Hairlines — present when you look, quiet when you don't. */
  detail: string[];
  /** Highlight down the mesial wall of the crown. */
  gloss: string;
  /** Shadow down the distal wall. This is what gives the crown volume: it
   *  reads on a white tooth and on a filled one alike, which a highlight
   *  alone does not. */
  shade: string;
  /** Rendered cell width — a molar really is wider than an incisor. */
  width: number;
}

export function toothTypeFor(fdi: string): ToothType {
  const quadrant = Number(fdi[0]);
  const position = Number(fdi[1]);
  const isPrimary = quadrant >= 5;

  if (position <= 2) return 'incisor';
  if (position === 3) return 'canine';
  // Primary dentition has no premolars: positions 4–5 are the primary molars.
  if (isPrimary) return 'molar';
  return position <= 5 ? 'premolar' : 'molar';
}

const INCISOR: ToothAnatomy = {
  // Slender and conical, tapering to a rounded apex.
  roots: ['M 15.05 36.5 C 15.3 27 16.3 12 18.6 4.2 C 19.2 2.1 20.8 2.1 21.4 4.2 C 23.7 12 24.7 27 24.95 36.5 Z'],
  // Shovel-shaped: narrow at the neck, widening to a flat incisal edge.
  crown:
    'M 15 36 C 13.7 41.5 12.6 47.5 12.6 53 C 12.6 57.2 13.5 59.4 15.6 59.5 L 24.4 59.5 C 26.5 59.4 27.4 57.2 27.4 53 C 27.4 47.5 26.3 41.5 25 36 Z',
  // Cementoenamel junction, the incisal ridge, and the grooves left by worn
  // mamelons on a young central incisor.
  detail: [
    'M 15.2 37.4 C 18 38.7 22 38.7 24.8 37.4',
    'M 14 55.8 C 17.6 57 22.4 57 26 55.8',
    'M 17.2 56.4 L 17.2 59.4',
    'M 22.8 56.4 L 22.8 59.4',
  ],
  gloss: 'M 14.4 42.4 C 13.8 46.6 13.6 51 13.7 54.6',
  shade: 'M 25.6 42.4 C 26.2 46.6 26.4 51 26.3 54.6',
  width: 30,
};

const CANINE: ToothAnatomy = {
  // The longest root in the mouth.
  roots: ['M 14.85 36.5 C 15.1 26 15.9 10.5 18.4 2.4 C 19.1 0.4 20.9 0.4 21.6 2.4 C 24.1 10.5 24.9 26 25.15 36.5 Z'],
  // Everything converges on one pointed cusp — the canine's signature.
  crown:
    'M 14.8 36 C 13.3 41.6 12 48 12 52.4 C 12 56.2 15.6 59.6 20 63.4 C 24.4 59.6 28 56.2 28 52.4 C 28 48 26.7 41.6 25.2 36 Z',
  detail: ['M 15 37.4 C 18 38.8 22 38.8 25 37.4', 'M 14.6 53.4 L 20 59.6 L 25.4 53.4'],
  gloss: 'M 13.9 42.4 C 13.2 46.8 13 51 13.4 54',
  shade: 'M 26.1 42.4 C 26.8 46.8 27 51 26.6 54',
  width: 31,
};

const PREMOLAR: ToothAnatomy = {
  roots: ['M 14.05 36.5 C 14.3 27 15.3 11.5 18.2 3.6 C 19 1.6 21 1.6 21.8 3.6 C 24.7 11.5 25.7 27 25.95 36.5 Z'],
  // Buccal and lingual cusps separated by a central groove.
  crown:
    'M 14 36 C 12.3 41.6 11 48 11 52.2 C 11 56 13 59.4 15.6 59.5 C 17.6 59.6 18.8 57.2 19.4 55 C 19.6 54 20.4 54 20.6 55 C 21.2 57.2 22.4 59.6 24.4 59.5 C 27 59.4 29 56 29 52.2 C 29 48 27.7 41.6 26 36 Z',
  detail: ['M 14.3 37.4 C 17.6 38.9 22.4 38.9 25.7 37.4', 'M 20 48 L 20 54'],
  gloss: 'M 12.8 42.4 C 12.1 46.8 12 51.4 12.2 54.8',
  shade: 'M 27.2 42.4 C 27.9 46.8 28 51.4 27.8 54.8',
  width: 35,
};

// The outer roots curve away from the midline; only the palatal root runs
// straight. Three carrots standing in a row is the giveaway of a fake chart.
const MOLAR_ROOT_LEFT =
  'M 8.55 36.5 C 7.7 28 6 15.5 4.7 7.2 C 4.3 4.8 6 4.2 6.9 6.2 C 9.7 14 13 25.5 14.5 36.5 Z';
const MOLAR_ROOT_CENTER =
  'M 17 36.5 C 17.2 28 17.8 13 18.7 5.2 C 19.1 3 20.9 3 21.3 5.2 C 22.2 13 22.8 28 23 36.5 Z';
const MOLAR_ROOT_RIGHT =
  'M 31.45 36.5 C 32.3 28 34 15.5 35.3 7.2 C 35.7 4.8 34 4.2 33.1 6.2 C 30.3 14 27 25.5 25.5 36.5 Z';

// Four cusps across the occlusal edge.
const MOLAR_CROWN =
  'M 8.5 36 C 6.6 41.6 5 48 5 52.2 C 5 56 7.6 59.4 10.4 59.5 C 12.8 59.6 14 57.4 14.7 55 C 15 54 16 54 16.3 55 C 16.9 57 18.1 58.2 20 58.2 C 21.9 58.2 23.1 57 23.7 55 C 24 54 25 54 25.3 55 C 26 57.4 27.2 59.6 29.6 59.5 C 32.4 59.4 35 56 35 52.2 C 35 48 33.4 41.6 31.5 36 Z';

const MOLAR_DETAIL = [
  'M 8.8 37.4 C 15.4 39.4 24.6 39.4 31.2 37.4',
  'M 15.5 49 L 15.5 54.2',
  'M 20 47.6 L 20 57.6',
  'M 24.5 49 L 24.5 54.2',
];
const MOLAR_GLOSS = 'M 7 42.4 C 6.3 46.8 6.2 51.4 6.4 54.8';
const MOLAR_SHADE = 'M 33 42.4 C 33.7 46.8 33.8 51.4 33.6 54.8';

const MOLAR_UPPER: ToothAnatomy = {
  roots: [MOLAR_ROOT_LEFT, MOLAR_ROOT_CENTER, MOLAR_ROOT_RIGHT],
  crown: MOLAR_CROWN,
  detail: MOLAR_DETAIL,
  gloss: MOLAR_GLOSS,
  shade: MOLAR_SHADE,
  width: 46,
};

// Lower molars carry two roots, upper molars three — a small anatomical detail
// a dentist notices immediately. The two are broader to span the same crown.
const MOLAR_LOWER: ToothAnatomy = {
  roots: [
    'M 8.55 36.5 C 7.9 28 6.7 15.2 5.9 6.8 C 5.6 4.4 7.5 3.8 8.5 6 C 11.5 13.6 14.5 25.5 16 36.5 Z',
    'M 31.45 36.5 C 32.1 28 33.3 15.2 34.1 6.8 C 34.4 4.4 32.5 3.8 31.5 6 C 28.5 13.6 25.5 25.5 24 36.5 Z',
  ],
  crown: MOLAR_CROWN,
  detail: MOLAR_DETAIL,
  gloss: MOLAR_GLOSS,
  shade: MOLAR_SHADE,
  width: 46,
};

/** Width multipliers per FDI position. Real teeth are not interchangeable
 *  within a type: upper laterals are narrower than upper centrals, LOWER
 *  centrals are the smallest teeth in the mouth, and third molars shrink. */
function widthScale(fdi: string, arch: 'upper' | 'lower'): number {
  const position = Number(fdi[1]);
  if (position === 1) return arch === 'upper' ? 1 : 0.8;
  if (position === 2) return arch === 'upper' ? 0.87 : 0.88;
  if (position === 7) return 0.95;
  if (position === 8) return 0.87;
  return 1;
}

export function anatomyFor(fdi: string, arch: 'upper' | 'lower'): ToothAnatomy {
  const base = (() => {
    switch (toothTypeFor(fdi)) {
      case 'incisor':
        return INCISOR;
      case 'canine':
        return CANINE;
      case 'premolar':
        return PREMOLAR;
      case 'molar':
        return arch === 'upper' ? MOLAR_UPPER : MOLAR_LOWER;
    }
  })();

  const scale = widthScale(fdi, arch);
  return scale === 1 ? base : { ...base, width: Math.round(base.width * scale) };
}

/** One quadrant of the circular surface wheel, drawn pointing up. The other
 * three are the same path rotated 90°, 180° and 270° about the centre — which
 * is why only one definition is needed. */
export const SURFACE_WHEEL_SEGMENT =
  'M 7.3 7.3 A 18 18 0 0 1 32.7 7.3 L 25 15 A 7 7 0 0 0 15 15 Z';
