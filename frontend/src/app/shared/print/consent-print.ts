import { Consent } from '../../core/models/clinical-record.models';
import { ClinicIdentity, clinicBlock, esc, longDate, openPrintWindow } from './print-document';

/**
 * Consentimiento informado como documento para firmar. El texto es la copia
 * que se guardó al emitirlo: lo que el paciente lee en papel es exactamente lo
 * que consta en su historia, aunque la plantilla haya cambiado después.
 */
export function printConsent(
  consent: Consent,
  clinic: ClinicIdentity | null,
  patient: { name: string; national_id: string | null; age: number | null },
): boolean {
  const minor = patient.age !== null && patient.age < 18;
  const signed =
    consent.status === 'firmado'
      ? `<p class="done">Firmado por <b>${esc(consent.signed_by_name)}</b> el ${longDate(consent.signed_at!)}.</p>`
      : '';
  return openPrintWindow(
    `Consentimiento · ${patient.name}`,
    `
    .body { white-space: pre-line; margin-top: 8px; }
    .done { margin-top: 18px; padding: 10px 12px; background: #f4f7f7; border-radius: 8px; }
    `,
    `
  <header>
    <div>
      <h1>Consentimiento informado</h1>
      <div>${esc(consent.title)}</div>
    </div>
    <div class="clinic">${clinicBlock(clinic)}</div>
  </header>

  <div class="meta">
    <div><span>Paciente</span><b>${esc(patient.name)}</b></div>
    <div><span>Cédula</span>${esc(patient.national_id || '—')}</div>
    ${consent.procedure_type ? `<div><span>Procedimiento</span>${esc(consent.procedure_type)}</div>` : ''}
    <div><span>Fecha</span>${longDate(consent.created_at)}</div>
  </div>

  <div class="body">${esc(consent.body)}</div>
  ${signed}

  <div class="sign">
    <div>${minor ? 'Firma del representante legal' : 'Firma del paciente'}<br>C.I.: ____________________</div>
    <div>Firma del profesional</div>
  </div>
  <footer>El paciente declara haber leído este documento, haber recibido respuesta a sus preguntas y que
  puede revocar su consentimiento antes del procedimiento.</footer>`,
  );
}
