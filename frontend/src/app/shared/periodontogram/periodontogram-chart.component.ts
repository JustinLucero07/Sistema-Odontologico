import { Component, Input, computed, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';

import {
  BUCCAL_SITES,
  LINGUAL_SITES,
  Periodontogram,
  PeriodontalSite,
  pocketSeverity,
} from '../../core/models/periodontogram.models';
import { PERMANENT_LOWER, PERMANENT_UPPER, ToothLayout } from '../odontogram/tooth-layout';

type SiteFlag = 'bleeding' | 'plaque' | 'suppuration';

interface SiteState {
  probing_depth: number | null;
  recession: number | null;
  bleeding: boolean;
  suppuration: boolean;
  plaque: boolean;
}

interface ToothState {
  fdi: string;
  arch: 'upper' | 'lower';
  absent: boolean;
  implant: boolean;
  mobility: number | null;
  furcation: number | null;
  sites: Record<PeriodontalSite, SiteState>;
}

/** One millimetre, in SVG units. The chart is read by eye, so the scale has
 *  to be generous enough that 3 mm and 5 mm are obviously different heights. */
const MM = 4.2;
/** Width of one site column; a tooth is three of them. */
const SITE_W = 15;
const TOOTH_W = SITE_W * 3;
/** Where the cementoenamel junction sits: recession draws above it, pockets
 *  below, which is how a printed perio chart is laid out. */
const CEJ_Y = 26;
const GRAPH_H = 92;

function emptySite(): SiteState {
  return { probing_depth: null, recession: null, bleeding: false, suppuration: false, plaque: false };
}

function emptyTooth(layout: ToothLayout): ToothState {
  return {
    fdi: layout.fdi,
    arch: layout.arch,
    absent: false,
    implant: false,
    mobility: null,
    furcation: null,
    sites: [...BUCCAL_SITES, ...LINGUAL_SITES].reduce(
      (acc, site) => ({ ...acc, [site]: emptySite() }),
      {} as Record<PeriodontalSite, SiteState>,
    ),
  };
}

@Component({
  selector: 'app-periodontogram-chart',
  standalone: true,
  imports: [FormsModule],
  templateUrl: './periodontogram-chart.component.html',
  styleUrl: './periodontogram-chart.component.scss',
})
export class PeriodontogramChartComponent {
  @Input() readonly = false;

  private readonly stateSignal = signal<ToothState[]>(
    [...PERMANENT_UPPER, ...PERMANENT_LOWER].map(emptyTooth),
  );

  /** Loading a saved exam replaces the whole grid: an exam is a snapshot, so
   *  merging one into another would invent a reading nobody took. */
  @Input() set value(exam: Periodontogram | null) {
    const fresh = [...PERMANENT_UPPER, ...PERMANENT_LOWER].map(emptyTooth);
    if (!exam) {
      this.stateSignal.set(fresh);
      return;
    }
    const byFdi = new Map(fresh.map((t) => [t.fdi, t]));
    for (const tooth of exam.teeth) {
      const target = byFdi.get(tooth.fdi_number);
      if (!target) continue;
      target.absent = tooth.absent;
      target.implant = tooth.implant;
      target.mobility = tooth.mobility;
      target.furcation = tooth.furcation;
    }
    for (const m of exam.measurements) {
      const target = byFdi.get(m.fdi_number);
      if (!target) continue;
      target.sites[m.site] = {
        probing_depth: m.probing_depth,
        recession: m.recession,
        bleeding: m.bleeding,
        suppuration: m.suppuration,
        plaque: m.plaque,
      };
    }
    this.stateSignal.set(fresh);
  }

  readonly buccalSites = BUCCAL_SITES;
  readonly lingualSites = LINGUAL_SITES;
  readonly siteWidth = SITE_W;
  readonly toothWidth = TOOTH_W;
  readonly graphHeight = GRAPH_H;
  readonly cejY = CEJ_Y;

  readonly upper = computed(() => this.stateSignal().filter((t) => t.arch === 'upper'));
  readonly lower = computed(() => this.stateSignal().filter((t) => t.arch === 'lower'));

  rowWidth(row: ToothState[]): number {
    return row.length * TOOTH_W;
  }

  /** The lingual wall is charted from the other side of the arch, so its three
   *  sites run in the mirror order of the buccal wall's. Getting this wrong
   *  swaps mesial and distal on half the chart. */
  sitesFor(wall: 'buccal' | 'lingual', tooth: ToothState): PeriodontalSite[] {
    const sites = wall === 'buccal' ? BUCCAL_SITES : LINGUAL_SITES;
    return tooth.arch === 'upper' ? sites : [...sites].reverse();
  }

  /** The three per-site toggles, reached by name so the template never has to
   *  index into the state with an untyped key. */
  flagValue(tooth: ToothState, site: PeriodontalSite, field: SiteFlag): boolean {
    return tooth.sites[site][field];
  }

  severity(tooth: ToothState, site: PeriodontalSite): string {
    return pocketSeverity(tooth.sites[site].probing_depth);
  }

  // ---- Editing -----------------------------------------------------------

  setDepth(tooth: ToothState, site: PeriodontalSite, raw: string): void {
    tooth.sites[site].probing_depth = this.clampNumber(raw, 0, 15);
    this.stateSignal.set([...this.stateSignal()]);
  }

  setRecession(tooth: ToothState, site: PeriodontalSite, raw: string): void {
    tooth.sites[site].recession = this.clampNumber(raw, -10, 20);
    this.stateSignal.set([...this.stateSignal()]);
  }

  setTooth(tooth: ToothState, field: 'mobility' | 'furcation', raw: string): void {
    tooth[field] = this.clampNumber(raw, 0, 3);
    this.stateSignal.set([...this.stateSignal()]);
  }

  toggle(tooth: ToothState, site: PeriodontalSite, field: SiteFlag): void {
    if (this.readonly) return;
    tooth.sites[site][field] = !tooth.sites[site][field];
    this.stateSignal.set([...this.stateSignal()]);
  }

  toggleAbsent(tooth: ToothState): void {
    if (this.readonly) return;
    tooth.absent = !tooth.absent;
    this.stateSignal.set([...this.stateSignal()]);
  }

  /** Out-of-range input is clamped rather than rejected: a probe cannot read
   *  20 mm, and silently dropping the keystroke leaves the field looking
   *  accepted when it was not. */
  private clampNumber(raw: string, min: number, max: number): number | null {
    if (raw === '' || raw === '-') return null;
    const parsed = Number(raw);
    if (Number.isNaN(parsed)) return null;
    return Math.min(Math.max(Math.round(parsed), min), max);
  }

  // ---- Profile curves ----------------------------------------------------

  /** Two polylines per wall: the gingival margin and the bottom of the pocket.
   *  The band between them IS the attachment loss, which is why they are drawn
   *  together rather than as two separate charts. */
  curve(row: ToothState[], wall: 'buccal' | 'lingual', line: 'margin' | 'pocket'): string {
    const points: string[] = [];
    row.forEach((tooth, toothIndex) => {
      if (tooth.absent) return;
      this.sitesFor(wall, tooth).forEach((site, siteIndex) => {
        const state = tooth.sites[site];
        if (state.probing_depth === null) return;
        const recession = state.recession ?? 0;
        const mm = line === 'margin' ? recession : recession + state.probing_depth!;
        const x = toothIndex * TOOTH_W + siteIndex * SITE_W + SITE_W / 2;
        const y = Math.min(Math.max(CEJ_Y + mm * MM, 2), GRAPH_H - 2);
        points.push(`${x.toFixed(1)},${y.toFixed(1)}`);
      });
    });
    return points.join(' ');
  }

  /** Bleeding points are plotted on the margin line, where a clinician looks
   *  for them, rather than listed in a separate row. */
  bleedingDots(row: ToothState[], wall: 'buccal' | 'lingual'): { x: number; y: number }[] {
    const dots: { x: number; y: number }[] = [];
    row.forEach((tooth, toothIndex) => {
      if (tooth.absent) return;
      this.sitesFor(wall, tooth).forEach((site, siteIndex) => {
        const state = tooth.sites[site];
        if (!state.bleeding) return;
        const y = Math.min(Math.max(CEJ_Y + (state.recession ?? 0) * MM, 2), GRAPH_H - 2);
        dots.push({ x: toothIndex * TOOTH_W + siteIndex * SITE_W + SITE_W / 2, y });
      });
    });
    return dots;
  }

  // ---- Output ------------------------------------------------------------

  /** Only sites that were actually charted are sent. An untouched site is
   *  absent from the payload, not a row of zeros — "not probed" and "0 mm"
   *  are different findings. */
  buildPayload() {
    const teeth = [];
    const measurements = [];
    for (const tooth of this.stateSignal()) {
      const touched =
        tooth.absent ||
        tooth.implant ||
        tooth.mobility !== null ||
        tooth.furcation !== null ||
        Object.values(tooth.sites).some(
          (s) => s.probing_depth !== null || s.recession !== null || s.bleeding || s.plaque || s.suppuration,
        );
      if (!touched) continue;

      teeth.push({
        fdi_number: tooth.fdi,
        absent: tooth.absent,
        implant: tooth.implant,
        mobility: tooth.mobility,
        furcation: tooth.furcation,
        notes: null,
      });

      if (tooth.absent) continue;
      for (const site of [...BUCCAL_SITES, ...LINGUAL_SITES]) {
        const state = tooth.sites[site];
        const charted =
          state.probing_depth !== null ||
          state.recession !== null ||
          state.bleeding ||
          state.plaque ||
          state.suppuration;
        if (!charted) continue;
        measurements.push({ fdi_number: tooth.fdi, site, ...state });
      }
    }
    return { teeth, measurements };
  }

  hasAnyData(): boolean {
    return this.buildPayload().measurements.length > 0;
  }
}
