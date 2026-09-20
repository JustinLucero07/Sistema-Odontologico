import { Injectable, signal } from '@angular/core';

export type ThemePreference = 'light' | 'dark' | 'system';

const STORAGE_KEY = 'odonto.theme';

@Injectable({ providedIn: 'root' })
export class ThemeService {
  /** What the user chose. "system" follows the OS and keeps following it. */
  readonly preference = signal<ThemePreference>(this.read());
  /** What is actually on screen right now. */
  readonly resolved = signal<'light' | 'dark'>('light');

  private readonly media = window.matchMedia('(prefers-color-scheme: dark)');

  constructor() {
    this.apply();
    // Only meaningful while the preference is "system" — apply() re-checks.
    this.media.addEventListener('change', () => {
      if (this.preference() === 'system') this.apply();
    });
  }

  set(preference: ThemePreference): void {
    this.preference.set(preference);
    try {
      localStorage.setItem(STORAGE_KEY, preference);
    } catch {
      // Blocked storage: the choice just won't survive a reload.
    }
    this.apply();
  }

  /** Cycles light → dark → system, which is what a single toolbar button needs. */
  cycle(): void {
    const order: ThemePreference[] = ['light', 'dark', 'system'];
    const next = order[(order.indexOf(this.preference()) + 1) % order.length];
    this.set(next);
  }

  private apply(): void {
    const preference = this.preference();
    const resolved = preference === 'system' ? (this.media.matches ? 'dark' : 'light') : preference;
    this.resolved.set(resolved);

    const root = document.documentElement;
    // A brightness jump is jarring, so the swap eases — the class is removed
    // once the transition has run so it never slows ordinary interaction.
    root.classList.add('theme-transition');
    root.dataset['theme'] = resolved;
    window.setTimeout(() => root.classList.remove('theme-transition'), 320);
  }

  private read(): ThemePreference {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      if (stored === 'light' || stored === 'dark' || stored === 'system') return stored;
    } catch {
      // ignore
    }
    return 'system';
  }
}
