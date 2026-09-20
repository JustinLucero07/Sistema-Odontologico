import { NgTemplateOutlet } from '@angular/common';
import { Component, EventEmitter, Input, Output, computed, signal } from '@angular/core';

import { ToothCondition, ToothSurface } from '../../core/models/odontogram.models';
import { SURFACE_WHEEL_SEGMENT, ToothAnatomy, anatomyFor, toothTypeFor } from './tooth-anatomy';
import { SURFACE_LABELS, TOOTH_CONDITION_BY_CODE } from './tooth-conditions';
import {
  PERMANENT_LOWER,
  PERMANENT_UPPER,
  TEMPORARY_LOWER,
  TEMPORARY_UPPER,
  ToothLayout,
} from './tooth-layout';

interface RenderedTooth extends ToothLayout {
  wholeCondition: ToothCondition | null;
  surfaceConditions: Partial<Record<ToothSurface, ToothCondition>>;
  /** Region -> surface, already resolved for this tooth's arch/side. */
  regionSurface: { top: ToothSurface; bottom: ToothSurface; left: ToothSurface; right: ToothSurface };
  anatomy: ToothAnatomy;
  crownFill: string;
  hasActivity: boolean;
  /** First tooth of the second quadrant — where the midline divider goes. */
  startsQuadrant: boolean;
  tooltip: string;
}

@Component({
  selector: 'app-odontogram-chart',
  standalone: true,
  imports: [NgTemplateOutlet],
  templateUrl: './odontogram-chart.component.html',
  styleUrl: './odontogram-chart.component.scss',
})
export class OdontogramChartComponent {
  private readonly conditionsSignal = signal<ToothCondition[]>([]);
  @Input() set conditions(value: ToothCondition[]) {
    this.conditionsSignal.set(value ?? []);
  }

  private readonly dentureSignal = signal<'permanent' | 'temporary'>('permanent');
  @Input() set denture(value: 'permanent' | 'temporary') {
    this.dentureSignal.set(value);
  }

  @Input() readonly = false;

  @Output() surfaceClicked = new EventEmitter<{ fdi: string; surface: ToothSurface }>();
  @Output() toothClicked = new EventEmitter<{ fdi: string }>();

  readonly wheelSegment = SURFACE_WHEEL_SEGMENT;

  private readonly conditionsByFdi = computed(() => {
    const map = new Map<string, ToothCondition[]>();
    for (const c of this.conditionsSignal()) {
      const list = map.get(c.fdi_number) ?? [];
      list.push(c);
      map.set(c.fdi_number, list);
    }
    return map;
  });

  readonly upperRow = computed(() =>
    this.buildRow(this.dentureSignal() === 'permanent' ? PERMANENT_UPPER : TEMPORARY_UPPER),
  );
  readonly lowerRow = computed(() =>
    this.buildRow(this.dentureSignal() === 'permanent' ? PERMANENT_LOWER : TEMPORARY_LOWER),
  );

  /** Quadrant captions name the side as the *patient's* left and right, which
   *  is the mirror of the viewer's — the convention every dental chart uses. */
  readonly captions = computed(() => {
    const upper = this.upperRow();
    const lower = this.lowerRow();
    const half = upper.length / 2;
    const range = (row: RenderedTooth[], from: number, to: number) =>
      `${row[from].fdi}–${row[to].fdi}`;
    return {
      upperRight: `Superior derecha · ${range(upper, 0, half - 1)}`,
      upperLeft: `Superior izquierda · ${range(upper, half, upper.length - 1)}`,
      lowerRight: `Inferior derecha · ${range(lower, 0, half - 1)}`,
      lowerLeft: `Inferior izquierda · ${range(lower, half, lower.length - 1)}`,
    };
  });

  private buildRow(layout: ToothLayout[]): RenderedTooth[] {
    const byFdi = this.conditionsByFdi();
    return layout.map((tooth, index) => {
      const toothConditions = byFdi.get(tooth.fdi) ?? [];
      const wholeCondition = toothConditions.find((c) => c.surface === 'whole') ?? null;
      const surfaceConditions: Partial<Record<ToothSurface, ToothCondition>> = {};
      for (const c of toothConditions) {
        if (c.surface !== 'whole') surfaceConditions[c.surface] = c;
      }

      const vestibularSide: 'top' | 'bottom' = tooth.arch === 'upper' ? 'top' : 'bottom';
      const mesialRegionSide: 'left' | 'right' = tooth.mesialSide === 'right' ? 'right' : 'left';

      const regionSurface = {
        top: vestibularSide === 'top' ? 'vestibular' : 'lingual',
        bottom: vestibularSide === 'bottom' ? 'vestibular' : 'lingual',
        left: mesialRegionSide === 'left' ? 'mesial' : 'distal',
        right: mesialRegionSide === 'right' ? 'mesial' : 'distal',
      } as { top: ToothSurface; bottom: ToothSurface; left: ToothSurface; right: ToothSurface };

      const conditionLabel = wholeCondition
        ? TOOTH_CONDITION_BY_CODE[wholeCondition.condition]?.label
        : Object.entries(surfaceConditions)
            .map(([surface, c]) => `${SURFACE_LABELS[surface]}: ${TOOTH_CONDITION_BY_CODE[c.condition]?.label}`)
            .join(' · ');

      return {
        ...tooth,
        wholeCondition,
        surfaceConditions,
        regionSurface,
        anatomy: anatomyFor(tooth.fdi, tooth.arch),
        crownFill: wholeCondition ? this.colorFor(wholeCondition) : 'var(--tooth-enamel)',
        hasActivity: toothConditions.length > 0,
        startsQuadrant: index === layout.length / 2,
        tooltip: `Pieza ${tooth.fdi} · ${this.typeLabel(tooth.fdi)}${conditionLabel ? ' — ' + conditionLabel : ' — Sano'}`,
      };
    });
  }

  private typeLabel(fdi: string): string {
    switch (toothTypeFor(fdi)) {
      case 'incisor':
        return 'Incisivo';
      case 'canine':
        return 'Canino';
      case 'premolar':
        return 'Premolar';
      case 'molar':
        return 'Molar';
    }
  }

  colorFor(condition: ToothCondition | undefined): string {
    if (!condition) return 'transparent';
    return TOOTH_CONDITION_BY_CODE[condition.condition]?.color ?? '#bdbdbd';
  }

  isAbsent(tooth: RenderedTooth): boolean {
    return (
      tooth.wholeCondition?.condition === 'ausente' ||
      tooth.wholeCondition?.condition === 'extraccion_realizada'
    );
  }

  onSurfaceClick(tooth: RenderedTooth, surface: ToothSurface): void {
    if (this.readonly) return;
    this.surfaceClicked.emit({ fdi: tooth.fdi, surface });
  }

  onToothClick(tooth: RenderedTooth): void {
    if (this.readonly) return;
    this.toothClicked.emit({ fdi: tooth.fdi });
  }
}
