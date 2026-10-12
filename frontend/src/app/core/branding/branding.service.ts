import { HttpClient } from '@angular/common/http';
import { Injectable, computed, inject, signal } from '@angular/core';
import { firstValueFrom } from 'rxjs';

import { environment } from '../../../environments/environment';

export type PracticeType = 'independiente' | 'consultorio' | 'clinica';

export interface Branding {
  name: string;
  practice_type: PracticeType;
  logo_data: string | null;
  slogan: string | null;
  primary_color: string | null;
  secondary_color: string | null;
  hidden_modules: string[];
  setup_completed: boolean;
  opens_at: string;
  closes_at: string;
  work_days: string;
  session_timeout_minutes: number;
  terms_pending: boolean;
  health_permit_expires_on: string | null;
}

/** Colores de marca que se ofrecen en el asistente (además de uno libre). */
export const BRAND_PALETTE: { name: string; hex: string }[] = [
  { name: 'Verde azulado', hex: '#0D7F76' },
  { name: 'Azul clínico', hex: '#1F6FD1' },
  { name: 'Índigo', hex: '#4F46E5' },
  { name: 'Violeta', hex: '#7B5BD6' },
  { name: 'Rosa', hex: '#D0457E' },
  { name: 'Coral', hex: '#E0614A' },
  { name: 'Ámbar', hex: '#C2851B' },
  { name: 'Verde', hex: '#2B8A4B' },
  { name: 'Grafito', hex: '#334155' },
];

const CACHE_KEY = 'odonto.branding';
const DEFAULT_PRIMARY = '#0D7F76';

/**
 * La identidad de cada consulta: nombre, logo y color. El color no se
 * aplica a un componente suelto: reescribe las variables del tema, así que
 * botones, menú, gráficos y documentos cambian a la vez, en claro y oscuro.
 */
@Injectable({ providedIn: 'root' })
export class BrandingService {
  private readonly http = inject(HttpClient);
  readonly branding = signal<Branding | null>(this.readCache());

  readonly name = computed(() => this.branding()?.name ?? 'Sistema Odontológico');
  readonly logo = computed(() => this.branding()?.logo_data ?? null);
  readonly hidden = computed(() => new Set(this.branding()?.hidden_modules ?? []));
  readonly practiceType = computed<PracticeType>(() => this.branding()?.practice_type ?? 'clinica');

  constructor() {
    this.apply(this.branding()?.primary_color ?? DEFAULT_PRIMARY);
  }

  async load(): Promise<Branding | null> {
    try {
      const b = await firstValueFrom(this.http.get<Branding>(`${environment.apiUrl}/clinics/branding`));
      this.set(b);
      return b;
    } catch {
      return this.branding();
    }
  }

  set(b: Branding): void {
    this.branding.set(b);
    try {
      localStorage.setItem(CACHE_KEY, JSON.stringify(b));
    } catch {
      // Sin almacenamiento: el login usará la marca por defecto.
    }
    this.apply(b.primary_color ?? DEFAULT_PRIMARY);
  }

  /** Vista previa en el asistente sin guardar. */
  preview(hex: string): void {
    this.apply(hex);
  }

  restore(): void {
    this.apply(this.branding()?.primary_color ?? DEFAULT_PRIMARY);
  }

  private readCache(): Branding | null {
    try {
      const raw = localStorage.getItem(CACHE_KEY);
      return raw ? (JSON.parse(raw) as Branding) : null;
    } catch {
      return null;
    }
  }

  private apply(hex: string): void {
    const el = document.getElementById('brand-vars') ?? document.head.appendChild(document.createElement('style'));
    el.id = 'brand-vars';
    if (hex.toUpperCase() === DEFAULT_PRIMARY) {
      el.textContent = ''; // el tema de fábrica ya está afinado a mano
      return;
    }
    const c = rgb(hex);
    const light = {
      primary: hex,
      dark: mix(c, [0, 0, 0], 0.28),
      mint: mix(c, [255, 255, 255], 0.3),
      onPrimary: luminance(c) > 0.55 ? '#0f2427' : '#ffffff',
    };
    const darkPrimary = mix(c, [255, 255, 255], 0.38);
    const dp = rgb(darkPrimary);
    el.textContent = `
      :root, :root[data-theme='light'] {
        --color-primary: ${light.primary};
        --color-primary-dark: ${light.dark};
        --color-primary-soft: rgba(${c.join(',')}, 0.1);
        --color-on-primary: ${light.onPrimary};
        --color-mint: ${light.mint};
        --nav-active-bg: linear-gradient(135deg, ${mix(c, [255, 255, 255], 0.12)} 0%, ${mix(c, [0, 0, 0], 0.14)} 100%);
        --nav-active-glow: 0 10px 22px -10px rgba(${c.join(',')}, 0.75);
        --nav-hover: rgba(${c.join(',')}, 0.08);
      }
      :root[data-theme='dark'] {
        --color-primary: ${darkPrimary};
        --color-primary-dark: ${hex};
        --color-primary-soft: rgba(${dp.join(',')}, 0.14);
        --color-on-primary: ${luminance(dp) > 0.55 ? '#05221f' : '#ffffff'};
        --color-mint: ${mix(c, [255, 255, 255], 0.5)};
        --nav-active-bg: linear-gradient(135deg, ${mix(c, [255, 255, 255], 0.45)} 0%, ${mix(c, [255, 255, 255], 0.15)} 100%);
        --nav-active-ink: #05221f;
        --nav-active-glow: 0 10px 24px -10px rgba(${dp.join(',')}, 0.6);
        --nav-hover: rgba(${dp.join(',')}, 0.1);
      }`;
  }
}

function rgb(hex: string): [number, number, number] {
  const n = parseInt(hex.replace('#', ''), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

function mix(c: number[], target: number[], t: number): string {
  const v = c.map((x, i) => Math.round(x + (target[i] - x) * t));
  return '#' + v.map((x) => x.toString(16).padStart(2, '0')).join('');
}

function luminance([r, g, b]: number[]): number {
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255;
}
