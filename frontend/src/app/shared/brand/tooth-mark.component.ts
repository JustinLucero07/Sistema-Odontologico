import { Component, Input } from '@angular/core';

/**
 * The product's brand mark: a molar drawn from its anatomy — a broad crown
 * with two cusps and two diverging roots — rather than the generic medical
 * briefcase. Inherits `currentColor` so it works on glass, on the sidebar and
 * on the accent gradient without a second copy.
 */
@Component({
  selector: 'app-tooth-mark',
  standalone: true,
  template: `
    <svg
      [attr.width]="size"
      [attr.height]="size"
      viewBox="0 0 32 32"
      fill="none"
      aria-hidden="true"
      class="tooth-mark"
    >
      <path
        d="M16 3.4c-6.1 0-10.6 3.3-10.6 8.9 0 3.9 1.1 6.9 1.9 10.9.6 3 1 5.8 3 5.8s2.4-2.7 3.1-5.5c.5-2 1.3-3.1 2.6-3.1s2.1 1.1 2.6 3.1c.7 2.8 1.1 5.5 3.1 5.5s2.4-2.8 3-5.8c.8-4 1.9-7 1.9-10.9 0-5.6-4.5-8.9-10.6-8.9Z"
        [attr.fill]="filled ? 'currentColor' : 'none'"
        stroke="currentColor"
        stroke-width="1.7"
        stroke-linejoin="round"
      />
      <!-- The enamel highlight: one short arc where light would catch the crown. -->
      <path
        d="M10.4 9.1c1-1.6 2.9-2.6 5-2.6"
        stroke="currentColor"
        stroke-width="1.6"
        stroke-linecap="round"
        [attr.opacity]="filled ? 0.45 : 0.75"
        [attr.stroke]="filled ? 'var(--tooth-mark-shine, #fff)' : 'currentColor'"
      />
    </svg>
  `,
  styles: [
    `
      :host {
        display: inline-flex;
      }
      .tooth-mark {
        display: block;
      }
    `,
  ],
})
export class ToothMarkComponent {
  @Input() size = 28;
  /** Solid crown for light-on-dark marks; outline for inline/nav use. */
  @Input() filled = false;
}
