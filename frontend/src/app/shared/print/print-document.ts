/**
 * Base común de los documentos que se imprimen (presupuesto, receta, aviso de
 * privacidad): una ventana propia con solo el documento, sin la interfaz.
 */

/** Lo que un documento necesita saber de la clínica para su encabezado. */
export interface ClinicIdentity {
  name: string;
  legal_name?: string | null;
  tax_id?: string | null;
  address?: string | null;
  phone?: string | null;
  email?: string | null;
  logo_data?: string | null;
  primary_color?: string | null;
  slogan?: string | null;
  document_footer?: string | null;
}

/** Identidad de la última clínica usada en el encabezado: el pie y el color
 *  de marca del documento salen de aquí al abrir la ventana. */
let marca: ClinicIdentity | null = null;

/** Escapa texto antes de meterlo en el HTML: lo escriben usuarios, y el
 *  documento se arma con `document.write`. Sin esto, un `<` en una nota
 *  se convertiría en marcado. */
export function esc(value: unknown): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

export function longDate(value: string | Date = new Date()): string {
  // Una fecha sola («2026-10-11») es medianoche UTC: en Ecuador eso es el día
  // anterior. Se lee al mediodía para que la fecha impresa sea la registrada.
  const d = typeof value === 'string' && /^\d{4}-\d{2}-\d{2}$/.test(value) ? new Date(value + 'T12:00:00') : new Date(value);
  return d.toLocaleDateString('es', { day: 'numeric', month: 'long', year: 'numeric' });
}

export function clinicBlock(clinic: ClinicIdentity | null): string {
  marca = clinic;
  if (!clinic) return '';
  const logo = clinic.logo_data && /^data:image\//.test(clinic.logo_data)
    ? `<img class="logo-doc" src="${esc(clinic.logo_data)}" alt=""><br>` : '';
  return `${logo}
    <b>${esc(clinic.name)}</b><br>
    ${clinic.slogan ? `<i>${esc(clinic.slogan)}</i><br>` : ''}
    ${clinic.legal_name && clinic.legal_name !== clinic.name ? esc(clinic.legal_name) + '<br>' : ''}
    ${clinic.tax_id ? 'RUC ' + esc(clinic.tax_id) + '<br>' : ''}
    ${clinic.address ? esc(clinic.address) + '<br>' : ''}
    ${[clinic.phone, clinic.email].filter(Boolean).map(esc).join(' · ')}`;
}

export const BASE_CSS = `
  * { box-sizing: border-box; }
  body { font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif; color: #0f2427;
         margin: 0; padding: 40px 48px; font-size: 13px; line-height: 1.55; }
  header { display: flex; justify-content: space-between; align-items: flex-start; gap: 24px;
           border-bottom: 2px solid #0d7f76; padding-bottom: 16px; margin-bottom: 24px; }
  h1 { margin: 0; font-size: 22px; letter-spacing: -0.02em; color: #0d7f76; }
  h2 { font-size: 13px; margin: 18px 0 4px; color: #0d7f76; }
  p { margin: 0 0 6px; }
  .clinic { text-align: right; font-size: 12px; color: #4a5c5f; }
  .clinic b { color: #0f2427; font-size: 14px; }
  .meta { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 24px; margin-bottom: 20px; }
  .meta span { color: #6b7c7e; font-size: 11px; display: block; }
  .sign { display: grid; grid-template-columns: 1fr 1fr; gap: 48px; margin-top: 64px; }
  .sign div { border-top: 1px solid #0f2427; padding-top: 6px; font-size: 11px;
              color: #4a5c5f; text-align: center; }
  footer { margin-top: 32px; font-size: 10.5px; color: #8a9a9c; }
  @media print { body { padding: 0 8px; } }
`;

/** Abre el documento y lanza el diálogo de impresión. Devuelve false si el
 *  navegador bloqueó la ventana, para que quien llama lo diga. */
export function openPrintWindow(title: string, css: string, body: string): boolean {
  const win = window.open('', '_blank', 'width=820,height=1000');
  if (!win) return false;
  const color = marca?.primary_color && /^#[0-9a-f]{6}$/i.test(marca.primary_color) ? marca.primary_color : null;
  const brandCss = `.logo-doc { max-height: 64px; max-width: 200px; object-fit: contain; margin-bottom: 6px; }
    .pie-marca { margin-top: 28px; padding-top: 10px; border-top: 1px solid #e3e8e8; text-align: center; font-size: 11px; color: #6b7c7e; }
    ${color ? `h1, h2, .accent { color: ${color} !important; } header { border-bottom-color: ${color} !important; }` : ''}`;
  if (marca?.document_footer) body += `<div class="pie-marca">${esc(marca.document_footer)}</div>`;
  win.document.write(`<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>${esc(title)}</title>
<style>${(BASE_CSS + css).split('#0d7f76').join(color ?? '#0d7f76')}${brandCss}</style></head><body>
${body}
<script>window.onload = () => { window.focus(); window.print(); };</script>
</body></html>`);
  win.document.close();
  return true;
}
