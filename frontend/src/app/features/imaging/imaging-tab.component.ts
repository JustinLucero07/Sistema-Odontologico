import { DatePipe } from '@angular/common';
import { Component, Input, OnDestroy, OnInit, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { MatTooltipModule } from '@angular/material/tooltip';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import {
  ClinicalImage,
  ClinicalImageTypeOption,
  IMAGE_TYPE_ICONS,
} from '../../core/models/clinical-image.models';
import { ImagingService } from '../../core/services/imaging.service';

@Component({
  selector: 'app-imaging-tab',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatSlideToggleModule,
    MatTooltipModule,
  ],
  templateUrl: './imaging-tab.component.html',
  styleUrl: './imaging-tab.component.scss',
})
export class ImagingTabComponent implements OnInit, OnDestroy {
  @Input({ required: true }) patientId!: string;

  private readonly service = inject(ImagingService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  readonly auth = inject(AuthService);

  readonly images = signal<ClinicalImage[]>([]);
  readonly types = signal<ClinicalImageTypeOption[]>([]);
  readonly loading = signal(true);
  readonly uploading = signal(false);
  readonly showArchived = signal(false);
  readonly showForm = signal(false);

  /** Object URLs are revoked on destroy; a blob URL that is never released
   *  keeps a whole radiograph alive in memory for the tab's lifetime. */
  private readonly objectUrls = new Map<string, string>();
  readonly previews = signal<Record<string, string>>({});

  readonly viewing = signal<ClinicalImage | null>(null);
  readonly viewerUrl = signal<string | null>(null);
  readonly zoom = signal(1);

  readonly archiving = signal<ClinicalImage | null>(null);
  archiveReason = '';

  selectedFile: File | null = null;
  readonly icons = IMAGE_TYPE_ICONS;

  readonly form = this.fb.nonNullable.group({
    title: ['', Validators.required],
    image_type: ['panoramica', Validators.required],
    taken_on: [''],
    fdi_numbers: [''],
    description: [''],
  });

  get canWrite(): boolean {
    return this.auth.hasPermission('imaging:write');
  }

  get selectedTypeIsToothScoped(): boolean {
    const code = this.form.controls.image_type.value;
    return this.types().find((t) => t.code === code)?.tooth_scoped ?? false;
  }

  async ngOnInit(): Promise<void> {
    this.types.set(await firstValueFrom(this.service.getTypes()));
    await this.reload();
  }

  ngOnDestroy(): void {
    for (const url of this.objectUrls.values()) URL.revokeObjectURL(url);
    this.objectUrls.clear();
  }

  async reload(): Promise<void> {
    this.loading.set(true);
    try {
      const images = await firstValueFrom(
        this.service.list(this.patientId, this.showArchived()),
      );
      this.images.set(images);
      // Thumbnails load one by one rather than in one burst, so a patient with
      // forty studies does not open forty parallel requests.
      for (const image of images) void this.loadPreview(image);
    } finally {
      this.loading.set(false);
    }
  }

  async toggleArchived(value: boolean): Promise<void> {
    this.showArchived.set(value);
    await this.reload();
  }

  private async loadPreview(image: ClinicalImage): Promise<void> {
    if (this.objectUrls.has(image.id)) return;
    try {
      const blob = await firstValueFrom(this.service.fetchBlob(image.id));
      const url = URL.createObjectURL(blob);
      this.objectUrls.set(image.id, url);
      this.previews.set({ ...this.previews(), [image.id]: url });
    } catch {
      // A study whose bytes are unreadable still lists its metadata; the card
      // shows a placeholder instead of vanishing.
    }
  }

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    this.selectedFile = input.files?.[0] ?? null;
    if (this.selectedFile && !this.form.controls.title.value) {
      this.form.controls.title.setValue(this.selectedFile.name.replace(/\.[^.]+$/, ''));
    }
  }

  async upload(): Promise<void> {
    if (!this.selectedFile || this.form.invalid || this.uploading()) return;
    this.uploading.set(true);
    try {
      const raw = this.form.getRawValue();
      await firstValueFrom(
        this.service.upload(this.patientId, {
          file: this.selectedFile,
          title: raw.title,
          image_type: raw.image_type,
          description: raw.description || null,
          taken_on: raw.taken_on || null,
          fdi_numbers: raw.fdi_numbers || null,
        }),
      );
      this.snackBar.open('Imagen guardada', 'Cerrar', { duration: 3000 });
      this.form.reset({ image_type: 'panoramica' });
      this.selectedFile = null;
      this.showForm.set(false);
      await this.reload();
    } catch (error: unknown) {
      const detail = (error as { error?: { detail?: string } })?.error?.detail;
      this.snackBar.open(detail ?? 'No se pudo subir la imagen', 'Cerrar', { duration: 6000 });
    } finally {
      this.uploading.set(false);
    }
  }

  open(image: ClinicalImage): void {
    this.viewing.set(image);
    this.viewerUrl.set(this.previews()[image.id] ?? null);
    this.zoom.set(1);
    if (!this.previews()[image.id]) {
      void this.loadPreview(image).then(() => this.viewerUrl.set(this.previews()[image.id] ?? null));
    }
  }

  closeViewer(): void {
    this.viewing.set(null);
    this.viewerUrl.set(null);
  }

  /** A radiograph is diagnosed by zooming into it, so the viewer needs real
   *  magnification rather than a lightbox that only fits the screen. */
  adjustZoom(delta: number): void {
    this.zoom.set(Math.min(Math.max(this.zoom() + delta, 0.5), 6));
  }

  askArchive(image: ClinicalImage): void {
    this.archiving.set(image);
    this.archiveReason = '';
  }

  async confirmArchive(): Promise<void> {
    const image = this.archiving();
    if (!image || !this.archiveReason.trim()) return;
    try {
      await firstValueFrom(this.service.archive(image.id, this.archiveReason.trim()));
      this.snackBar.open('Imagen archivada', 'Cerrar', { duration: 3000 });
      this.archiving.set(null);
      await this.reload();
    } catch {
      this.snackBar.open('No se pudo archivar la imagen', 'Cerrar', { duration: 5000 });
    }
  }

  typeLabel(code: string): string {
    return this.types().find((t) => t.code === code)?.label ?? code;
  }

  sizeLabel(bytes: number | null): string {
    if (!bytes) return '';
    const mb = bytes / (1024 * 1024);
    if (mb >= 1) return `${mb.toFixed(1)} MB`;
    // Rounding to whole kilobytes prints "0 KB" for a small file, which reads
    // as a broken upload rather than a small one.
    const kb = bytes / 1024;
    return kb >= 1 ? `${kb.toFixed(kb < 10 ? 1 : 0)} KB` : `${bytes} B`;
  }
}
