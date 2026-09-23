import { LegalController } from '../../core/services/legal.service';
import { confidentialityAgreement, controllerName, privacyNotice } from '../legal/legal-texts';
import { clinicBlock, esc, longDate, openPrintWindow } from './print-document';

function sections(list: { title: string; paragraphs: string[] }[]): string {
  return list
    .map((s) => `<h2>${esc(s.title)}</h2>${s.paragraphs.map((p) => `<p>${esc(p)}</p>`).join('')}`)
    .join('');
}

/**
 * Aviso de privacidad para entregar y firmar. Deja dos constancias separadas:
 * que se informó (obligatorio) y si autoriza mensajes (opcional). Mezclarlas
 * en una sola firma haría que negarse a los mensajes pareciera negarse a
 * ser atendido.
 */
export function printPrivacyNotice(controller: LegalController, patientName: string | null): boolean {
  return openPrintWindow(
    'Aviso de privacidad',
    `
    .box { margin-top: 22px; padding: 14px 16px; border: 1px solid #cfd8d9; border-radius: 8px; }
    .check { display: flex; gap: 10px; align-items: flex-start; margin: 8px 0; }
    .sq { width: 14px; height: 14px; border: 1.5px solid #0f2427; flex-shrink: 0; margin-top: 2px; }
    .fill { display: inline-block; min-width: 260px; border-bottom: 1px solid #0f2427; }
    `,
    `
  <header>
    <div>
      <h1>Aviso de privacidad</h1>
      <div>Tratamiento de datos personales y de salud · versión ${esc(controller.privacy_policy_version)}</div>
    </div>
    <div class="clinic">${clinicBlock(controller)}</div>
  </header>

  ${sections(privacyNotice(controller))}

  <div class="box">
    <p><b>Paciente:</b> <span class="fill">${esc(patientName ?? '')}</span></p>
    <p><b>Representante legal</b> (si es menor de edad): <span class="fill"></span></p>
    <div class="check"><span class="sq"></span>
      <span>Declaro que ${esc(controllerName(controller))} me informó cómo trata mis datos personales y de salud,
      y que recibí una copia de este aviso.</span></div>
    <div class="check"><span class="sq"></span>
      <span><b>Opcional:</b> autorizo recibir recordatorios de citas y otros mensajes por WhatsApp o correo
      electrónico. Puedo retirar esta autorización cuando quiera.</span></div>
  </div>

  <div class="sign">
    <div>Firma del paciente o representante</div>
    <div>Fecha: ${longDate()}</div>
  </div>`,
  );
}

export function printConfidentialityAgreement(controller: LegalController, staffName: string): boolean {
  return openPrintWindow(
    'Acuerdo de confidencialidad',
    '',
    `
  <header>
    <div>
      <h1>Acuerdo de confidencialidad</h1>
      <div>Personal con acceso a datos de pacientes · versión ${esc(controller.confidentiality_version)}</div>
    </div>
    <div class="clinic">${clinicBlock(controller)}</div>
  </header>
  ${sections(confidentialityAgreement(controller))}
  <div class="sign">
    <div>${esc(staffName)}</div>
    <div>Fecha: ${longDate()}</div>
  </div>`,
  );
}
