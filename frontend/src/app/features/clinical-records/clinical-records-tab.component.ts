import { DatePipe } from '@angular/common';
import { Component, Input, OnChanges, TemplateRef, ViewChild, computed, inject, signal } from '@angular/core';
import { FormBuilder, ReactiveFormsModule, Validators } from '@angular/forms';
import { MatButtonModule } from '@angular/material/button';
import { MatCardModule } from '@angular/material/card';
import { MatDialog, MatDialogModule, MatDialogRef } from '@angular/material/dialog';
import { MatFormFieldModule } from '@angular/material/form-field';
import { MatIconModule } from '@angular/material/icon';
import { MatInputModule } from '@angular/material/input';
import { MatSelectModule } from '@angular/material/select';
import { MatMenuModule } from '@angular/material/menu';
import { MatSlideToggleModule } from '@angular/material/slide-toggle';
import { MatSnackBar } from '@angular/material/snack-bar';
import { firstValueFrom } from 'rxjs';

import { AuthService } from '../../core/auth/auth.service';
import { promptText, promptVoidReason } from '../../shared/confirm-dialog/prompt-dialog.component';
import {
  ClinicalEvolution,
  Consent,
  ConsentTemplate,
  DOCUMENT_TYPE_LABELS,
  PatientDocument,
  Prescription,
  PrescriptionItem,
} from '../../core/models/clinical-record.models';
import { ClinicalRecordsService } from '../../core/services/clinical-records.service';
import { Professional } from '../../core/models/clinic.models';
import { ClinicService } from '../../core/services/clinic.service';
import { LegalService } from '../../core/services/legal.service';
import { PatientsService } from '../../core/services/patients.service';
import { printPrescription } from '../../shared/print/prescription-print';
import { printConsent } from '../../shared/print/consent-print';

type Section = 'evoluciones' | 'recetas' | 'consentimientos' | 'documentos';

@Component({
  selector: 'app-clinical-records-tab',
  standalone: true,
  imports: [
    DatePipe,
    ReactiveFormsModule,
    MatButtonModule,
    MatCardModule,
    MatDialogModule,
    MatFormFieldModule,
    MatIconModule,
    MatInputModule,
    MatSelectModule,
    MatMenuModule,
    MatSlideToggleModule,
  ],
  templateUrl: './clinical-records-tab.component.html',
  styleUrl: './clinical-records-tab.component.scss',
})
export class ClinicalRecordsTabComponent implements OnChanges {
  @Input({ required: true }) patientId!: string;

  private readonly service = inject(ClinicalRecordsService);
  private readonly auth = inject(AuthService);
  private readonly fb = inject(FormBuilder);
  private readonly snackBar = inject(MatSnackBar);
  private readonly dialog = inject(MatDialog);

  // Los formularios de alta viven en ventanas emergentes: la lista no salta
  // y la tarea en curso queda clara.
  @ViewChild('evolucionesDialog') private evolucionesDialog!: TemplateRef<unknown>;
  @ViewChild('recetasDialog') private recetasDialog!: TemplateRef<unknown>;
  @ViewChild('consentimientosDialog') private consentimientosDialog!: TemplateRef<unknown>;
  @ViewChild('documentosDialog') private documentosDialog!: TemplateRef<unknown>;
  private formRef: MatDialogRef<unknown> | null = null;

  readonly showArchivedDocs = signal(false);
  /** Documento cuyo título o tipo se corrige; null al subir uno nuevo. */
  readonly editingDoc = signal<PatientDocument | null>(null);
  private readonly clinicService = inject(ClinicService);
  private readonly legalService = inject(LegalService);
  private readonly patientsService = inject(PatientsService);

  /** Quienes pueden firmar una receta: solo profesionales activos. */
  readonly prescribers = signal<Professional[]>([]);

  readonly documentTypeLabels = DOCUMENT_TYPE_LABELS;
  readonly documentTypes = Object.keys(DOCUMENT_TYPE_LABELS);

  readonly section = signal<Section>('evoluciones');
  readonly evolutions = signal<ClinicalEvolution[]>([]);
  readonly prescriptions = signal<Prescription[]>([]);
  readonly consents = signal<Consent[]>([]);
  readonly templates = signal<ConsentTemplate[]>([]);
  readonly documents = signal<PatientDocument[]>([]);

  readonly openForm = signal<Section | null>(null);
  readonly saving = signal(false);
  readonly selectedFile = signal<File | null>(null);
  readonly prescriptionItems = signal<PrescriptionItem[]>([{ medication: '' }]);

  readonly canWriteEvolutions = computed(() => this.auth.hasPermission('evolutions:write'));
  readonly canWritePrescriptions = computed(() => this.auth.hasPermission('prescriptions:write'));
  readonly canWriteConsents = computed(() => this.auth.hasPermission('consents:write'));
  readonly canWriteDocuments = computed(() => this.auth.hasPermission('documents:write'));

  /** Evolución que se corrige; null cuando el formulario registra una nueva. */
  readonly editingEvolution = signal<ClinicalEvolution | null>(null);

  readonly evolutionForm = this.fb.nonNullable.group({
    procedure: ['', Validators.required],
    fdi_numbers: [''],
    anesthesia: [''],
    materials: [''],
    diagnosis: [''],
    evolution: [''],
    instructions: [''],
    next_appointment_notes: [''],
  });

  readonly prescriptionForm = this.fb.nonNullable.group({
    professional_id: ['', Validators.required],
    notes: [''],
  });

  readonly consentForm = this.fb.nonNullable.group({
    template_id: [''],
    title: [''],
    body: [''],
  });

  readonly documentForm = this.fb.nonNullable.group({
    title: ['', Validators.required],
    document_type: ['otro', Validators.required],
    description: [''],
  });

  readonly signForm = this.fb.nonNullable.group({ signed_by_name: ['', Validators.required] });
  readonly signingConsent = signal<Consent | null>(null);

  async ngOnChanges(): Promise<void> {
    if (this.patientId) await this.reload();
  }

  async voidPrescription(prescription: Prescription): Promise<void> {
    const reason = await promptVoidReason(this.dialog, 'receta');
    if (!reason) return;
    try {
      await firstValueFrom(this.service.voidPrescription(this.patientId, prescription.id, reason));
      this.snackBar.open('Receta anulada', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch {
      this.snackBar.open('No se pudo anular la receta', 'Cerrar', { duration: 3500 });
    }
  }

  async reload(): Promise<void> {
    const results = await Promise.allSettled([
      firstValueFrom(this.service.listEvolutions(this.patientId)),
      firstValueFrom(this.service.listPrescriptions(this.patientId)),
      firstValueFrom(this.service.listConsents(this.patientId)),
      firstValueFrom(this.service.listDocuments(this.patientId, this.showArchivedDocs())),
      firstValueFrom(this.service.listConsentTemplates()),
      firstValueFrom(this.clinicService.listProfessionals()),
    ]);
    // A role may hold only some of these permissions; the sections it cannot
    // read simply stay empty rather than breaking the whole tab.
    if (results[0].status === 'fulfilled') this.evolutions.set(results[0].value);
    if (results[1].status === 'fulfilled') this.prescriptions.set(results[1].value);
    if (results[2].status === 'fulfilled') this.consents.set(results[2].value);
    if (results[3].status === 'fulfilled') this.documents.set(results[3].value);
    if (results[4].status === 'fulfilled') this.templates.set(results[4].value);
    if (results[5].status === 'fulfilled') {
      const active = results[5].value.filter((p) => p.is_active);
      this.prescribers.set(active);
      // Con un solo profesional no hay nada que elegir.
      if (active.length === 1 && !this.prescriptionForm.controls.professional_id.value) {
        this.prescriptionForm.controls.professional_id.setValue(active[0].id);
      }
    }
  }

  toggleForm(section: Section): void {
    const templates: Partial<Record<Section, TemplateRef<unknown>>> = {
      evoluciones: this.evolucionesDialog,
      recetas: this.recetasDialog,
      consentimientos: this.consentimientosDialog,
      documentos: this.documentosDialog,
    };
    const template = templates[section];
    if (!template) return;
    this.formRef?.close();
    this.openForm.set(section);
    this.formRef = this.dialog.open(template, {
      width: section === 'recetas' ? '820px' : '680px',
      maxWidth: '96vw',
      autoFocus: 'first-tabbable',
      panelClass: 'app-dialog',
    });
    this.formRef.afterClosed().subscribe(() => {
      this.closeForm();
      this.editingEvolution.set(null);
    });
  }

  closeForm(): void {
    this.formRef?.close();
    this.formRef = null;
  }

  // ---- Evolutions ------------------------------------------------------

  startEvolution(): void {
    this.editingEvolution.set(null);
    this.evolutionForm.reset();
    this.toggleForm('evoluciones');
  }

  correctEvolution(item: ClinicalEvolution): void {
    this.editingEvolution.set(item);
    this.evolutionForm.reset({
      procedure: item.procedure,
      fdi_numbers: item.fdi_numbers ?? '',
      anesthesia: item.anesthesia ?? '',
      materials: item.materials ?? '',
      diagnosis: item.diagnosis ?? '',
      evolution: item.evolution ?? '',
      instructions: item.instructions ?? '',
      next_appointment_notes: item.next_appointment_notes ?? '',
    });
    this.toggleForm('evoluciones');
  }

  async saveEvolution(): Promise<void> {
    if (this.evolutionForm.invalid || this.saving()) return;
    this.saving.set(true);
    const editing = this.editingEvolution();
    try {
      if (editing) {
        await firstValueFrom(this.service.updateEvolution(editing.id, this.evolutionForm.getRawValue()));
      } else {
        await firstValueFrom(this.service.createEvolution(this.patientId, this.evolutionForm.getRawValue()));
      }
      this.evolutionForm.reset();
      this.editingEvolution.set(null);
      this.closeForm();
      this.snackBar.open(editing ? 'Corrección guardada (queda en la auditoría)' : 'Evolución registrada', 'Cerrar', {
        duration: 3000,
      });
      await this.reload();
    } finally {
      this.saving.set(false);
    }
  }

  // ---- Prescriptions ---------------------------------------------------

  addPrescriptionItem(): void {
    this.prescriptionItems.set([...this.prescriptionItems(), { medication: '' }]);
  }

  removePrescriptionItem(index: number): void {
    this.prescriptionItems.set(this.prescriptionItems().filter((_, i) => i !== index));
  }

  updateItem(index: number, field: keyof PrescriptionItem, value: string): void {
    const items = [...this.prescriptionItems()];
    items[index] = { ...items[index], [field]: value };
    this.prescriptionItems.set(items);
  }

  async savePrescription(): Promise<void> {
    const items = this.prescriptionItems().filter((item) => item.medication.trim());
    if (items.length === 0 || this.saving()) {
      this.snackBar.open('Agrega al menos un medicamento', 'Cerrar', { duration: 3000 });
      return;
    }
    if (this.prescriptionForm.invalid) {
      this.prescriptionForm.markAllAsTouched();
      this.snackBar.open('Elija el profesional que firma la receta', 'Cerrar', { duration: 3000 });
      return;
    }
    this.saving.set(true);
    try {
      await firstValueFrom(
        this.service.createPrescription(this.patientId, {
          professional_id: this.prescriptionForm.getRawValue().professional_id,
          notes: this.prescriptionForm.getRawValue().notes || null,
          items,
        }),
      );
      this.prescriptionForm.reset({ professional_id: this.prescriptionForm.getRawValue().professional_id });
      this.prescriptionItems.set([{ medication: '' }]);
      this.closeForm();
      this.snackBar.open('Receta emitida', 'Cerrar', { duration: 3000 });
      await this.reload();
    } finally {
      this.saving.set(false);
    }
  }

  // ---- Consents --------------------------------------------------------

  onTemplateSelected(templateId: string): void {
    const template = this.templates().find((t) => t.id === templateId);
    if (template) {
      this.consentForm.patchValue({ title: template.name, body: template.body });
    }
  }

  async saveConsent(): Promise<void> {
    if (this.saving()) return;
    const value = this.consentForm.getRawValue();
    if (!value.template_id && (!value.title || !value.body)) {
      this.snackBar.open('Elige una plantilla o escribe el título y el texto', 'Cerrar', { duration: 3500 });
      return;
    }
    this.saving.set(true);
    try {
      await firstValueFrom(
        this.service.createConsent(this.patientId, {
          template_id: value.template_id || null,
          title: value.title || null,
          body: value.body || null,
        }),
      );
      this.consentForm.reset();
      this.closeForm();
      this.snackBar.open('Consentimiento creado', 'Cerrar', { duration: 3000 });
      await this.reload();
    } finally {
      this.saving.set(false);
    }
  }

  startSigning(consent: Consent): void {
    this.signingConsent.set(consent);
    this.signForm.reset();
  }

  async confirmSignature(): Promise<void> {
    const consent = this.signingConsent();
    if (!consent || this.signForm.invalid) return;
    await firstValueFrom(
      this.service.signConsent(consent.id, this.signForm.getRawValue().signed_by_name),
    );
    this.signingConsent.set(null);
    this.snackBar.open('Consentimiento firmado', 'Cerrar', { duration: 3000 });
    await this.reload();
  }

  // ---- Documents -------------------------------------------------------

  onFileSelected(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0] ?? null;
    this.selectedFile.set(file);
    if (file && !this.documentForm.getRawValue().title) {
      this.documentForm.patchValue({ title: file.name });
    }
  }

  async uploadDocument(): Promise<void> {
    const editing = this.editingDoc();
    if (editing) {
      if (this.documentForm.invalid || this.saving()) return;
      this.saving.set(true);
      try {
        const v = this.documentForm.getRawValue();
        await firstValueFrom(
          this.service.updateDocument(editing.id, {
            title: v.title,
            document_type: v.document_type,
            description: v.description || null,
          }),
        );
        this.closeForm();
        this.snackBar.open('Documento actualizado', 'Cerrar', { duration: 3000 });
        await this.reload();
      } finally {
        this.saving.set(false);
      }
      return;
    }
    const file = this.selectedFile();
    if (!file) {
      this.snackBar.open('Elija el archivo a subir', 'Cerrar', { duration: 3000 });
      return;
    }
    if (this.documentForm.invalid || this.saving()) return;
    this.saving.set(true);
    try {
      const value = this.documentForm.getRawValue();
      await firstValueFrom(
        this.service.uploadDocument(this.patientId, file, value.title, value.document_type, value.description),
      );
      this.documentForm.reset({ document_type: 'otro' });
      this.selectedFile.set(null);
      this.closeForm();
      this.snackBar.open('Documento subido', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch {
      this.snackBar.open('No se pudo subir el documento', 'Cerrar', { duration: 3000 });
    } finally {
      this.saving.set(false);
    }
  }

  async toggleArchivedDocs(value: boolean): Promise<void> {
    this.showArchivedDocs.set(value);
    await this.reload();
  }

  editDocument(doc: PatientDocument): void {
    this.editingDoc.set(doc);
    this.documentForm.reset({
      title: doc.title,
      document_type: doc.document_type,
      description: doc.description ?? '',
    });
    this.toggleForm('documentos');
  }

  newDocument(): void {
    this.editingDoc.set(null);
    this.selectedFile.set(null);
    this.documentForm.reset({ document_type: 'otro' });
    this.toggleForm('documentos');
  }

  async archiveDocument(doc: PatientDocument): Promise<void> {
    const reason = await promptText(this.dialog, {
      title: `Archivar «${doc.title}»`,
      message: 'Deja de aparecer en la lista pero no se borra: el archivo se conserva y se puede restaurar.',
      label: 'Motivo',
      minLength: 3,
      confirmLabel: 'Archivar',
      danger: true,
    });
    if (!reason) return;
    await firstValueFrom(this.service.archiveDocument(doc.id, reason));
    this.snackBar.open('Documento archivado', 'Cerrar', { duration: 3000 });
    await this.reload();
  }

  async restoreDocument(doc: PatientDocument): Promise<void> {
    await firstValueFrom(this.service.restoreDocument(doc.id));
    this.snackBar.open('Documento restaurado', 'Cerrar', { duration: 3000 });
    await this.reload();
  }

  async voidConsent(consent: Consent): Promise<void> {
    const signed = consent.status === 'firmado';
    const reason = await promptVoidReason(this.dialog, signed ? 'consentimiento (revocación)' : 'consentimiento');
    if (!reason) return;
    try {
      await firstValueFrom(this.service.voidConsent(consent.id, reason));
      this.snackBar.open(signed ? 'Revocación registrada' : 'Consentimiento anulado', 'Cerrar', { duration: 3000 });
      await this.reload();
    } catch {
      this.snackBar.open('No se pudo registrar', 'Cerrar', { duration: 4000 });
    }
  }

  async download(doc: PatientDocument): Promise<void> {
    const blob = await firstValueFrom(this.service.downloadDocument(doc.id));
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = doc.original_filename;
    link.click();
    URL.revokeObjectURL(url);
  }

  fileSize(bytes: number | null): string {
    if (!bytes) return '';
    if (bytes < 1024) return `${bytes} B`;
    if (bytes < 1024 * 1024) return `${Math.round(bytes / 1024)} KB`;
    return `${(bytes / 1024 / 1024).toFixed(1)} MB`;
  }

  async printConsent(consent: Consent): Promise<void> {
    try {
      const [clinic, patient] = await Promise.all([
        firstValueFrom(this.legalService.getController()),
        firstValueFrom(this.patientsService.getPatient(this.patientId)),
      ]);
      const opened = printConsent(consent, clinic, {
        name: `${patient.first_name} ${patient.last_name}`,
        national_id: patient.national_id,
        age: patient.age,
      });
      if (!opened) {
        this.snackBar.open('El navegador bloqueó la ventana de impresión', 'Cerrar', { duration: 4000 });
      }
    } catch {
      this.snackBar.open('No se pudo preparar el consentimiento', 'Cerrar', { duration: 4000 });
    }
  }

  /** La receta como documento propio, con prescriptor y registro profesional. */
  async printPrescription(prescription: Prescription): Promise<void> {
    try {
      const [clinic, patient, professionals] = await Promise.all([
        firstValueFrom(this.legalService.getController()),
        firstValueFrom(this.patientsService.getPatient(this.patientId)),
        firstValueFrom(this.clinicService.listProfessionals()),
      ]);
      const prof = professionals.find((p) => p.id === prescription.professional_id) ?? null;
      const opened = printPrescription(
        prescription,
        clinic,
        {
          name: `${patient.first_name} ${patient.last_name}`,
          national_id: patient.national_id,
          age: patient.age,
        },
        prof ? { name: `${prof.first_name} ${prof.last_name}`, license_number: prof.license_number } : null,
      );
      if (!opened) {
        this.snackBar.open('El navegador bloqueó la ventana de impresión', 'Cerrar', { duration: 4000 });
      }
    } catch {
      this.snackBar.open('No se pudo preparar la receta', 'Cerrar', { duration: 4000 });
    }
  }
}
