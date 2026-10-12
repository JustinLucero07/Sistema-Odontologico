import { ClinicIdentity, clinicBlock, esc, longDate, openPrintWindow } from './print-document';

const CSS = `
  body { max-width: 720px; margin: 0 auto; }
  .titulo { text-align: center; margin: 26px 0 22px; }
  .titulo h1 { font-size: 26px; letter-spacing: .08em; text-transform: uppercase; }
  .cuerpo { font-size: 14px; line-height: 1.9; text-align: justify; }
  ul { margin: 10px 0 16px; padding-left: 20px; } li { margin: 3px 0; }
  .firma { margin: 80px auto 0; width: 300px; border-top: 1px solid #0f2427; padding-top: 6px; text-align: center; font-size: 12px; }
  .lugar { text-align: right; margin-top: 28px; }
`;

export interface TreatmentCertificate {
  patient_name: string;
  patient_id_number: string | null;
  treatments: { name: string; tooth: string | null; date: string | null }[];
  professional_name: string;
  license_number: string | null;
  city: string | null;
  notes: string | null;
}

/** Certificado de tratamiento realizado (para el paciente, su seguro o su trabajo). */
export function printTreatmentCertificate(d: TreatmentCertificate, clinic: ClinicIdentity | null): boolean {
  return openPrintWindow(
    `Certificado de tratamiento · ${d.patient_name}`,
    CSS,
    `
  <header><div></div><div class="clinic">${clinicBlock(clinic)}</div></header>
  <div class="titulo"><h1>Certificado odontológico</h1></div>
  <div class="cuerpo">
    <p>Quien suscribe, <b>${esc(d.professional_name)}</b>${d.license_number ? `, con registro profesional ${esc(d.license_number)}` : ''},
    certifica que el/la paciente <b>${esc(d.patient_name)}</b>${d.patient_id_number ? `, con cédula de identidad N.° ${esc(d.patient_id_number)}` : ''},
    ha recibido en ${esc(clinic?.name ?? 'esta consulta')} los siguientes tratamientos odontológicos:</p>
    <ul>${d.treatments.map((t) => `<li>${esc(t.name)}${t.tooth ? ` — pieza ${esc(t.tooth)}` : ''}${t.date ? ` (${new Date(t.date + 'T12:00:00').toLocaleDateString('es')})` : ''}</li>`).join('')}</ul>
    ${d.notes ? `<p>${esc(d.notes)}</p>` : ''}
    <p>Se extiende el presente certificado a petición del interesado, para los fines que estime convenientes.</p>
  </div>
  <p class="lugar">${esc(d.city || '')}${d.city ? ', ' : ''}${longDate(new Date())}</p>
  <div class="firma"><b>${esc(d.professional_name)}</b><br>${d.license_number ? 'Reg. ' + esc(d.license_number) + '<br>' : ''}Odontólogo/a</div>`,
  );
}

export interface AttendanceCertificate {
  patient_name: string;
  patient_id_number: string | null;
  date: string;          // ISO de la cita
  ends_at: string;
  reason: string | null;
  professional_name: string;
  license_number: string | null;
  rest_days: number;
  city: string | null;
}

/** Certificado de asistencia: el justificativo para el trabajo o el colegio. */
export function printAttendanceCertificate(d: AttendanceCertificate, clinic: ClinicIdentity | null): boolean {
  const ini = new Date(d.date);
  const fin = new Date(d.ends_at);
  const hora = (x: Date) => x.toLocaleTimeString('es', { hour: '2-digit', minute: '2-digit' });
  return openPrintWindow(
    `Certificado de asistencia · ${d.patient_name}`,
    CSS,
    `
  <header><div></div><div class="clinic">${clinicBlock(clinic)}</div></header>
  <div class="titulo"><h1>Certificado de asistencia</h1></div>
  <div class="cuerpo">
    <p>Certifico que el/la paciente <b>${esc(d.patient_name)}</b>${d.patient_id_number ? `, con cédula N.° ${esc(d.patient_id_number)}` : ''},
    asistió a consulta odontológica el día <b>${longDate(ini)}</b>, de <b>${hora(ini)}</b> a <b>${hora(fin)}</b>${d.reason ? `, para <b>${esc(d.reason)}</b>` : ''}.</p>
    ${d.rest_days > 0 ? `<p>Se recomienda reposo de <b>${d.rest_days} ${d.rest_days === 1 ? 'día' : 'días'}</b> a partir de la fecha.</p>` : ''}
    <p>Se extiende el presente certificado a petición del interesado.</p>
  </div>
  <p class="lugar">${esc(d.city || '')}${d.city ? ', ' : ''}${longDate(new Date())}</p>
  <div class="firma"><b>${esc(d.professional_name)}</b><br>${d.license_number ? 'Reg. ' + esc(d.license_number) + '<br>' : ''}Odontólogo/a</div>`,
  );
}
