import { NgTemplateOutlet } from '@angular/common';
import { Component, EventEmitter, Input, Output, computed, signal } from '@angular/core';

import { ToothCondition, ToothSurface } from '../../core/models/odontogram.models';
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
  /** Purely cosmetic: bigger for molars, narrower for incisors, like a real arch. */
  sizePx: number;
  /** Purely cosmetic: nudges each tooth along a gentle arch curve. */
  curveTransform: string;
  hasActivity: boolean;
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

  private readonly conditionsByFdi = computed(() => {
    const map = new Map<string, ToothCondition[]>();
    for (const c of this.conditionsSignal()) {
      const list = map.get(c.fdi_number) ?? [];
      list.push(c);
      map.set(c.fdi_number, list);
    }
    return map;
  });

  readonly upperRow = computed(() => this.buildRow(this.dentureSignal() === 'permanent' ? PERMANENT_UPPER : TEMPORARY_UPPER));
  readonly lowerRow = computed(() => this.buildRow(this.dentureSignal() === 'permanent' ? PERMANENT_LOWER : TEMPORARY_LOWER));

  private buildRow(layout: ToothLayout[]): RenderedTooth[] {
    const byFdi = this.conditionsByFdi();
    const n = layout.length;
    const center = (n - 1) / 2;

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

      // Cosmetic only: real teeth get wider back near the molars and narrower
      // toward the incisors — position within the quadrant (last digit of the
      // FDI number) tells us which tooth type this is.
      const positionInQuadrant = Number(tooth.fdi[1]);
      const sizePx =
        positionInQuadrant <= 2 ? 32 : positionInQuadrant === 3 ? 34 : positionInQuadrant <= 5 ? 37 : 42;

      // Cosmetic only: nudge each tooth along a gentle arch so the row reads
      // as a dental arch rather than a flat strip of squares.
      const offset = index - center;
      const normalized = center === 0 ? 0 : offset / center;
      const curveDepth = 16;
      const rotateMax = 13;
      const dip = curveDepth * (1 - normalized * normalized);
      const translateY = tooth.arch === 'upper' ? dip : -dip;
      const rotate = normalized * rotateMax * (tooth.arch === 'upper' ? 1 : -1);
      const curveTransform = `translateY(${translateY.toFixed(1)}px) rotate(${rotate.toFixed(1)}deg)`;

      const hasActivity = toothConditions.length > 0;
      const conditionLabel = wholeCondition
        ? TOOTH_CONDITION_BY_CODE[wholeCondition.condition]?.label
        : Object.entries(surfaceConditions)
            .map(([surface, c]) => `${SURFACE_LABELS[surface]}: ${TOOTH_CONDITION_BY_CODE[c.condition]?.label}`)
            .join(' · ');
      const tooltip = `Pieza ${tooth.fdi}${conditionLabel ? ' — ' + conditionLabel : ' — Sano'}`;

      return { ...tooth, wholeCondition, surfaceConditions, regionSurface, sizePx, curveTransform, hasActivity, tooltip };
    });
  }

  colorFor(condition: ToothCondition | undefined): string {
    if (!condition) return 'transparent';
    return TOOTH_CONDITION_BY_CODE[condition.condition]?.color ?? '#bdbdbd';
  }

  isAbsent(tooth: RenderedTooth): boolean {
    return tooth.wholeCondition?.condition === 'ausente' || tooth.wholeCondition?.condition === 'extraccion_realizada';
  }

  onSurfaceClick(tooth: RenderedTooth, surface: ToothSurface): void {
    if (this.readonly) return;
    this.surfaceClicked.emit({ fdi: tooth.fdi, surface });
  }

  onToothLabelClick(tooth: RenderedTooth): void {
    if (this.readonly) return;
    this.toothClicked.emit({ fdi: tooth.fdi });
  }
}
