import { AfterViewInit, Component, ElementRef, EventEmitter, Input, OnDestroy, Output, ViewChild, signal } from '@angular/core';
import { MatButtonModule } from '@angular/material/button';
import { MatIconModule } from '@angular/material/icon';

/** Recuadro de firma: se firma con el dedo, el lápiz o el ratón. Emite la
 *  firma como PNG (data URL), o null si está vacío. */
@Component({
  selector: 'app-signature-pad',
  standalone: true,
  imports: [MatButtonModule, MatIconModule],
  template: `
    <div class="pad" [class.filled]="!empty()">
      <canvas #canvas aria-label="Recuadro para firmar"></canvas>
      @if (empty()) {
        <span class="hint">{{ placeholder }}</span>
      }
      <span class="line"></span>
    </div>
    <div class="row">
      <span class="label">{{ label }}</span>
      <button mat-button type="button" (click)="clear()" [disabled]="empty()"><mat-icon>backspace</mat-icon>Borrar</button>
    </div>
  `,
  styles: [
    `
      :host { display: block; }
      .pad { position: relative; height: 180px; border: 1.5px dashed var(--color-border-strong); border-radius: 16px;
        background: #fff; touch-action: none; overflow: hidden; }
      .pad.filled { border-style: solid; }
      canvas { position: absolute; inset: 0; width: 100%; height: 100%; cursor: crosshair; touch-action: none; }
      .hint { position: absolute; inset: 0; display: grid; place-items: center; color: #9aa5a8; pointer-events: none; font-size: 0.95rem; }
      .line { position: absolute; left: 24px; right: 24px; bottom: 38px; border-bottom: 1px solid #d9d4ca; pointer-events: none; }
      .row { display: flex; align-items: center; justify-content: space-between; margin-top: 4px; }
      .label { font-size: 0.82rem; color: var(--color-ink-faint); }
    `,
  ],
})
export class SignaturePadComponent implements AfterViewInit, OnDestroy {
  @Input() label = 'Firma';
  @Input() placeholder = 'Firme aquí con el dedo o el ratón';
  @Output() changed = new EventEmitter<string | null>();
  @ViewChild('canvas', { static: true }) canvasRef!: ElementRef<HTMLCanvasElement>;

  readonly empty = signal(true);
  private ctx!: CanvasRenderingContext2D;
  private drawing = false;
  private last: { x: number; y: number } | null = null;
  private resizeObserver?: ResizeObserver;

  ngAfterViewInit(): void {
    const canvas = this.canvasRef.nativeElement;
    this.ctx = canvas.getContext('2d')!;
    this.resize();
    this.resizeObserver = new ResizeObserver(() => this.resize());
    this.resizeObserver.observe(canvas);
    canvas.addEventListener('pointerdown', this.down);
    canvas.addEventListener('pointermove', this.move);
    canvas.addEventListener('pointerup', this.up);
    canvas.addEventListener('pointercancel', this.up);
    canvas.addEventListener('pointerleave', this.up);
  }

  ngOnDestroy(): void {
    this.resizeObserver?.disconnect();
  }

  /** Ajusta el lienzo a su tamaño real (y a la densidad de la pantalla) sin
   *  perder lo ya dibujado. */
  private resize(): void {
    const canvas = this.canvasRef.nativeElement;
    const ratio = Math.max(window.devicePixelRatio || 1, 1);
    const { width, height } = canvas.getBoundingClientRect();
    if (!width || !height) return;
    const previous = this.empty() ? null : canvas.toDataURL('image/png');
    canvas.width = Math.round(width * ratio);
    canvas.height = Math.round(height * ratio);
    this.ctx.setTransform(ratio, 0, 0, ratio, 0, 0);
    this.ctx.lineCap = 'round';
    this.ctx.lineJoin = 'round';
    this.ctx.strokeStyle = '#14242b';
    if (previous) {
      const img = new Image();
      img.onload = () => this.ctx.drawImage(img, 0, 0, width, height);
      img.src = previous;
    }
  }

  private point(e: PointerEvent): { x: number; y: number } {
    const r = this.canvasRef.nativeElement.getBoundingClientRect();
    return { x: e.clientX - r.left, y: e.clientY - r.top };
  }

  private readonly down = (e: PointerEvent): void => {
    e.preventDefault();
    this.canvasRef.nativeElement.setPointerCapture(e.pointerId);
    this.drawing = true;
    this.last = this.point(e);
    // Un toque sin mover también deja un punto.
    this.ctx.beginPath();
    this.ctx.arc(this.last.x, this.last.y, 1.2, 0, Math.PI * 2);
    this.ctx.fillStyle = '#14242b';
    this.ctx.fill();
  };

  private readonly move = (e: PointerEvent): void => {
    if (!this.drawing || !this.last) return;
    const p = this.point(e);
    // Grosor según presión (lápiz) y algo de velocidad: trazo más natural.
    const dist = Math.hypot(p.x - this.last.x, p.y - this.last.y);
    const presion = e.pressure && e.pointerType === 'pen' ? e.pressure : 0.5;
    this.ctx.lineWidth = Math.max(1.4, Math.min(3.6, 1.2 + presion * 3 - dist * 0.04));
    this.ctx.beginPath();
    this.ctx.moveTo(this.last.x, this.last.y);
    this.ctx.lineTo(p.x, p.y);
    this.ctx.stroke();
    this.last = p;
    if (this.empty()) this.empty.set(false);
  };

  private readonly up = (): void => {
    if (!this.drawing) return;
    this.drawing = false;
    this.last = null;
    this.empty.set(false);
    this.changed.emit(this.dataUrl());
  };

  clear(): void {
    const canvas = this.canvasRef.nativeElement;
    this.ctx.clearRect(0, 0, canvas.width, canvas.height);
    this.empty.set(true);
    this.changed.emit(null);
  }

  /** PNG con fondo transparente, recortado al tamaño visible. */
  dataUrl(): string | null {
    return this.empty() ? null : this.canvasRef.nativeElement.toDataURL('image/png');
  }
}
