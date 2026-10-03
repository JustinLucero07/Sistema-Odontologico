import { Component, Input } from '@angular/core';

export type SkeletonVariant = 'list' | 'cards' | 'table' | 'detail' | 'chart' | 'gallery';

/**
 * Esqueleto de carga: la forma de lo que va a aparecer, con un brillo que la
 * recorre. Se lee como "ya casi" en vez de "no hay nada", y cuando llegan los
 * datos el contenido ocupa el mismo sitio sin que la página salte.
 */
@Component({
  selector: 'app-skeleton',
  standalone: true,
  template: `
    <div class="sk-root" role="status" [attr.aria-label]="label">
      @switch (variant) {
        @case ('cards') {
          <div class="sk-cards">
            @for (i of items; track i) {
              <div class="sk-card" [style.animation-delay.ms]="i * 70">
                <div class="sk-row">
                  <span class="sk sk-line" style="width: 46%"></span>
                  <span class="sk sk-tile"></span>
                </div>
                <span class="sk sk-line sk-big" style="width: 58%"></span>
                <span class="sk sk-line" style="width: 72%"></span>
              </div>
            }
          </div>
        }
        @case ('table') {
          <div class="sk-panel">
            <div class="sk-row sk-head">
              @for (c of cols; track c) {
                <span class="sk sk-line" [style.width.%]="c"></span>
              }
            </div>
            @for (i of items; track i) {
              <div class="sk-row sk-tr" [style.animation-delay.ms]="i * 60">
                @for (c of cols; track c) {
                  <span class="sk sk-line" [style.width.%]="c - (i % 3) * 4"></span>
                }
              </div>
            }
          </div>
        }
        @case ('detail') {
          <div class="sk-panel sk-detail">
            <div class="sk-row">
              <span class="sk sk-avatar sk-avatar-lg"></span>
              <div class="sk-col">
                <span class="sk sk-line sk-big" style="width: 220px"></span>
                <span class="sk sk-line" style="width: 300px"></span>
              </div>
            </div>
            <div class="sk-row sk-chips">
              <span class="sk sk-pill"></span><span class="sk sk-pill"></span><span class="sk sk-pill"></span>
            </div>
          </div>
          <div class="sk-panel sk-tabs">
            @for (i of [1, 2, 3, 4, 5, 6]; track i) {
              <span class="sk sk-line" style="width: 90px"></span>
            }
          </div>
          <div class="sk-panel sk-block"></div>
        }
        @case ('chart') {
          <div class="sk-panel">
            <span class="sk sk-line sk-big" style="width: 30%"></span>
            <div class="sk-bars">
              @for (h of [62, 40, 78, 52, 88, 46, 70, 58]; track $index) {
                <span class="sk sk-bar" [style.height.%]="h" [style.animation-delay.ms]="$index * 60"></span>
              }
            </div>
          </div>
        }
        @case ('gallery') {
          <div class="sk-gallery">
            @for (i of items; track i) {
              <div class="sk-card" [style.animation-delay.ms]="i * 70">
                <span class="sk sk-thumb"></span>
                <span class="sk sk-line" style="width: 70%"></span>
                <span class="sk sk-line" style="width: 45%"></span>
              </div>
            }
          </div>
        }
        @default {
          <div class="sk-panel">
            @for (i of items; track i) {
              <div class="sk-row sk-item" [style.animation-delay.ms]="i * 70">
                <span class="sk sk-avatar"></span>
                <div class="sk-col">
                  <span class="sk sk-line" [style.width.%]="52 - (i % 3) * 8"></span>
                  <span class="sk sk-line sk-thin" [style.width.%]="34 + (i % 2) * 10"></span>
                </div>
                <span class="sk sk-pill"></span>
              </div>
            }
          </div>
        }
      }
    </div>
  `,
  styles: [
    `
      :host {
        display: block;
      }

      .sk-root {
        display: grid;
        gap: 16px;
      }

      /* La forma: un vidrio apenas más denso, con un destello que la cruza. */
      .sk {
        display: block;
        border-radius: 8px;
        background:
          linear-gradient(
              100deg,
              transparent 20%,
              var(--sk-shine) 50%,
              transparent 80%
            )
            0 0 / 220% 100% no-repeat,
          var(--sk-base);
        animation: sk-shimmer 1.6s cubic-bezier(0.4, 0, 0.2, 1) infinite;
      }

      .sk-line {
        height: 12px;
      }

      .sk-thin {
        height: 9px;
        opacity: 0.8;
      }

      .sk-big {
        height: 22px;
        border-radius: 10px;
      }

      .sk-avatar {
        flex-shrink: 0;
        width: 40px;
        height: 40px;
        border-radius: 50%;
      }

      .sk-avatar-lg {
        width: 56px;
        height: 56px;
      }

      .sk-tile {
        width: 40px;
        height: 40px;
        border-radius: 13px;
      }

      .sk-pill {
        flex-shrink: 0;
        width: 84px;
        height: 26px;
        border-radius: 999px;
      }

      .sk-panel,
      .sk-card {
        padding: 18px 20px;
        border-radius: var(--radius-lg, 20px);
        background: var(--glass-card-bg);
        border: 1px solid var(--glass-card-border, var(--color-border));
        box-shadow: var(--glass-specular, none);
        animation: sk-in 0.4s ease both;
      }

      .sk-panel {
        display: grid;
        gap: 4px;
      }

      .sk-row {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 14px;
      }

      .sk-col {
        flex: 1;
        display: grid;
        gap: 8px;
      }

      .sk-item {
        padding: 10px 0;
        animation: sk-in 0.4s ease both;

        & + .sk-item {
          border-top: 1px solid var(--color-border);
        }
      }

      .sk-head {
        padding-bottom: 12px;
        border-bottom: 1px solid var(--color-border);

        .sk-line {
          height: 9px;
          opacity: 0.7;
        }
      }

      .sk-tr {
        padding: 14px 0;
        animation: sk-in 0.4s ease both;

        & + .sk-tr {
          border-top: 1px solid var(--color-border);
        }
      }

      .sk-cards {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
        gap: 16px;
      }

      .sk-card {
        display: grid;
        gap: 12px;
      }

      .sk-gallery {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(190px, 1fr));
        gap: 16px;
      }

      .sk-thumb {
        height: 130px;
        border-radius: 14px;
      }

      .sk-detail {
        gap: 16px;
      }

      .sk-chips {
        justify-content: flex-start;
      }

      .sk-tabs {
        display: flex;
        gap: 28px;
        padding: 14px 22px;
        overflow: hidden;
      }

      .sk-block {
        height: 280px;
      }

      .sk-bars {
        display: flex;
        align-items: flex-end;
        gap: 14px;
        height: 180px;
        margin-top: 14px;
      }

      .sk-bar {
        flex: 1;
        border-radius: 10px 10px 4px 4px;
        transform-origin: bottom;
        animation:
          sk-shimmer 1.6s cubic-bezier(0.4, 0, 0.2, 1) infinite,
          sk-grow 0.6s cubic-bezier(0.2, 0.8, 0.2, 1) both;
      }

      @keyframes sk-shimmer {
        from {
          background-position: 130% 0, 0 0;
        }
        to {
          background-position: -130% 0, 0 0;
        }
      }

      @keyframes sk-in {
        from {
          opacity: 0;
          transform: translateY(6px);
        }
      }

      @keyframes sk-grow {
        from {
          transform: scaleY(0.2);
        }
      }

      @media (prefers-reduced-motion: reduce) {
        .sk,
        .sk-bar {
          animation: sk-pulse 1.6s ease-in-out infinite;
        }

        .sk-panel,
        .sk-card,
        .sk-item,
        .sk-tr {
          animation: none;
        }

        @keyframes sk-pulse {
          50% {
            opacity: 0.55;
          }
        }
      }
    `,
  ],
})
export class SkeletonComponent {
  @Input() variant: SkeletonVariant = 'list';
  @Input() rows = 5;
  @Input() label = 'Cargando';

  get items(): number[] {
    return Array.from({ length: this.rows }, (_, i) => i);
  }

  readonly cols = [26, 18, 16, 14, 12];
}
