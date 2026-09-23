import { DatePipe } from '@angular/common';
import { Component, Input, OnDestroy, OnInit, TemplateRef, ViewChild, inject, signal } from '@angular/core';
import { FormBuilder, FormsModule, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatMenuModule } from '@angular/material/menu';
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
import { promptText } from '../../shared/confirm-dialog/prompt-dialog.component';

@Component({
  selector: 'app-imaging-tab',
  standalone: true,
  imports: [
    DatePipe,
    FormsModule,
    ReactiveFormsModule,
    MatButtonModule,
    MatDialogModule,
    MatMenuModule,
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
  private readonly dialog = inject(MatDialog);

  @ViewChild('formDialog') formDialog!: TemplateRef<unknown>;
  private dialogRef: MatDialogRef<unknown> | null = null;
  /** Estudio que se edita; null cuando el diálogo sube uno nuevo. */
  readonly editing = signal<ClinicalImage | null>(null);
  readonly auth = inject(AuthService);

  readonly images = signal<ClinicalImage[]>([]);
  readonly types = signal<ClinicalImageTypeOption[]>([]);
  readonly loading = signal(true);
  readonly uploading = signal(false);
  readonly showArchived = signal(false);

  /** Object URLs are revoked on destroy; a blob URL that is never released
   *  keeps a whole radiograph alive in memory for the tab's lifetime. */
  private readonly objectUrls = new Map<string, string>();
  readonly previews = signal<Record<string, string>>({});

  readonly viewing = signal<ClinicalImage | null>(null);
  readonly viewerUrl = signal<string | null>(null);
  readonly zoom = signal(1);


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
    if (!this.selectedFile) {
      this.snackBar.open('Elija el archivo de la imagen', 'Cerrar', { duration: 3000 });
      return;
    }
    if (this.form.invalid) {
      this.form.markAllAsTouched();
      return;
    }
    if (this.uploading()) return;
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
      this.dialogRef?.close();
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

  openForm(image: ClinicalImage | null = null): void {
    this.editing.set(image);
    this.selectedFile = null;
    this.form.reset({
      title: image?.title ?? '',
      image_type: image?.image_type ?? 'panoramica',
      taken_on: image?.taken_on ?? '',
      fdi_numbers: (image?.fdi_numbers ?? []).join(','),
      description: image?.description ?? '',
    });
    this.dialogRef = this.dialog.open(this.formDialog, {
      width: '640px',
      maxWidth: '96vw',
      autoFocus: 'first-tabbable',
      panelClass: 'app-dialog',
    });
  }

  async save(): Promise<void> {
    const editing = this.editing();
    if (!editing) {
      await this.upload();
      return;
    }
    if (this.form.invalid || this.uploading()) {
      this.form.markAllAsTouched();
      return;
    }
    this.uploading.set(true);
    try {
      const raw = this.form.getRawValue();
      await firstValueFrom(
        this.service.update(editing.id, {
          title: raw.title,
          image_type: raw.image_type,
          description: raw.description || null,
          taken_on: raw.taken_on || null,
          fdi_numbers: raw.fdi_numbers
            .split(',')
            .map((n) => n.trim())
            .filter(Boolean),
        }),
      );
      this.dialogRef?.close();
      this.snackBar.open('Datos del estudio actualizados', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch (error: unknown) {
      const detail = (error as { error?: { detail?: string } })?.error?.detail;
      this.snackBar.open(detail ?? 'No se pudo guardar', 'Cerrar', { duration: 5000 });
    } finally {
      this.uploading.set(false);
    }
  }

  async askArchive(image: ClinicalImage): Promise<void> {
    const reason = await promptText(this.dialog, {
      title: `Archivar «${image.title}»`,
      message:
        'Deja de aparecer en la lista activa, pero se conserva: saber qué estudio se vio en cada ' +
        'momento forma parte de la historia clínica. Se puede restaurar.',
      label: 'Motivo',
      minLength: 3,
      confirmLabel: 'Archivar',
      danger: true,
    });
    if (!reason) return;
    try {
      await firstValueFrom(this.service.archive(image.id, reason));
      this.snackBar.open('Imagen archivada', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch {
      this.snackBar.open('No se pudo archivar la imagen', 'Cerrar', { duration: 5000 });
    }
  }

  async restore(image: ClinicalImage): Promise<void> {
    try {
      await firstValueFrom(this.service.restore(image.id));
      this.snackBar.open('Imagen restaurada', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch {
      this.snackBar.open('No se pudo restaurar la imagen', 'Cerrar', { duration: 5000 });
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
