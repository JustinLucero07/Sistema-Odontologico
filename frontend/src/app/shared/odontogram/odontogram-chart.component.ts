import { NgTemplateOutlet } from '@angular/common';
import { Component, EventEmitter, Input, Output, computed, signal } from '@angular/core';

import { ToothCondition, ToothSurface } from '../../core/models/odontogram.models';
import { TOOTH_CONDITION_BY_CODE } from './tooth-conditions';
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
    return layout.map((tooth) => {
      const toothConditions = byFdi.get(tooth.fdi) ?? [];
      const wholeCondition = toothConditions.find((c) => c.surface === 'whole') ?? null;
      const surfaceConditions: Partial<Record<ToothSurface, ToothCondition>> = {};
      for (const c of toothConditions) {
        if (c.surface !== 'whole') surfaceConditions[c.surface] = c;
      }

      const vestibularSide: 'top' | 'bottom' = tooth.arch === 'upper' ? 'top' : 'bottom';
      const lingualSide: 'top' | 'bottom' = tooth.arch === 'upper' ? 'bottom' : 'top';
      const mesialRegionSide: 'left' | 'right' = tooth.mesialSide === 'right' ? 'right' : 'left';
      const distalRegionSide: 'left' | 'right' = mesialRegionSide === 'right' ? 'left' : 'right';

      const regionSurface = {
        top: vestibularSide === 'top' ? 'vestibular' : 'lingual',
        bottom: vestibularSide === 'bottom' ? 'vestibular' : 'lingual',
        left: mesialRegionSide === 'left' ? 'mesial' : 'distal',
        right: mesialRegionSide === 'right' ? 'mesial' : 'distal',
      } as { top: ToothSurface; bottom: ToothSurface; left: ToothSurface; right: ToothSurface };

      return { ...tooth, wholeCondition, surfaceConditions, regionSurface };
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
