import { Prescription } from '../../core/models/clinical-record.models';
import { ClinicIdentity, clinicBlock, esc, longDate, openPrintWindow } from './print-document';

export interface Prescriber {
  name: string;
  license_number: string | null;
  specialty?: string | null;
}

export interface PrescriptionPatient {
  name: string;
  national_id: string | null;
  age: number | null;
}

/**
 * Receta médica como documento propio. Lleva lo que una receta necesita para
 * ser válida: quién prescribe y su registro profesional, a quién, cuándo, cada
 * medicamento con su dosis, frecuencia y duración, y el espacio para la firma.
 * Si el profesional no tiene registro cargado, se deja la línea en blanco para
 * escribirlo a mano en vez de imprimir la receta sin él.
 */
export function printPrescription(
  prescription: Prescription,
  clinic: ClinicIdentity | null,
  patient: PrescriptionPatient,
  prescriber: Prescriber | null,
): boolean {
  const items = prescription.items
    .map(
      (item, i) => `
      <li>
        <div class="drug"><span class="n">${i + 1}.</span> ${esc(item.medication)}</div>
        <div class="how">
          ${[item.dosage, item.frequency, item.duration ? 'durante ' + item.duration : null]
            .filter(Boolean)
            .map(esc)
            .join(' · ') || '&nbsp;'}
        </div>
        ${item.instructions ? `<div class="ins">${esc(item.instructions)}</div>` : ''}
      </li>`,
    )
    .join('');

  const license = prescriber?.license_number
    ? esc(prescriber.license_number)
    : '<span class="blank">____________________</span>';

  return openPrintWindow(
    `Receta · ${patient.name}`,
    `
    .rx { font-size: 34px; font-weight: 700; color: #0d7f76; line-height: 1; margin: 4px 0 12px; }
    ol { list-style: none; padding: 0; margin: 0; }
    li { padding: 10px 0; border-bottom: 1px solid #eef2f2; }
    .drug { font-size: 14px; font-weight: 600; }
    .n { color: #6b7c7e; margin-right: 4px; }
    .how { color: #34484b; margin-top: 2px; }
    .ins { color: #4a5c5f; font-style: italic; margin-top: 2px; }
    .notes { margin-top: 18px; padding: 12px 14px; background: #f4f7f7; border-radius: 8px; }
    .prescriber { margin-top: 70px; width: 320px; margin-left: auto; text-align: center; }
    .prescriber .line { border-top: 1px solid #0f2427; padding-top: 6px; }
    .prescriber small { display: block; color: #4a5c5f; }
    .blank { color: #9aa8aa; }
    `,
    `
  <header>
    <div>
      <h1>Receta médica</h1>
      <div>${longDate(prescription.created_at)}</div>
    </div>
    <div class="clinic">${clinicBlock(clinic)}</div>
  </header>

  <div class="meta">
    <div><span>Paciente</span><b>${esc(patient.name)}</b></div>
    <div><span>Cédula</span>${esc(patient.national_id || '—')}</div>
    <div><span>Edad</span>${patient.age !== null ? patient.age + ' años' : '—'}</div>
    <div><span>Fecha de emisión</span>${longDate(prescription.created_at)}</div>
  </div>

  <div class="rx">℞</div>
  <ol>${items}</ol>

  ${prescription.notes ? `<div class="notes"><b>Indicaciones:</b> ${esc(prescription.notes)}</div>` : ''}

  <div class="prescriber">
    <div class="line">
      <b>${esc(prescriber?.name ?? '')}</b>
      ${prescriber?.specialty ? `<small>${esc(prescriber.specialty)}</small>` : ''}
      <small>Registro profesional: ${license}</small>
      <small>Firma y sello</small>
    </div>
  </div>

  <footer>Documento emitido para uso del paciente. Conserve esta receta durante todo el tratamiento.</footer>`,
  );
}
