import { Clinic } from '../../core/models/clinic.models';
import { Budget } from '../../core/models/treatment.models';

/** Escapes text before it goes into the printed HTML. Treatment descriptions
 *  and notes are typed by users, and this document is written with
 *  `document.write` — unescaped, a `<` in a note would become markup. */
function esc(value: unknown): string {
  return String(value ?? '')
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

const money = (n: number) =>
  '$ ' +
  new Intl.NumberFormat('es', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);

/**
 * Opens a clean, printable budget in its own window.
 *
 * Printing the patient page itself would put the sidebar, the tabs and every
 * other panel on paper. A budget handed to a patient is a document on its own:
 * clinic, patient, lines, totals, and a place to sign.
 */
export function printBudget(
  budget: Budget,
  clinic: Clinic | null,
  patientName: string,
  planTitle?: string,
): void {
  const win = window.open('', '_blank', 'width=820,height=1000');
  if (!win) return; // blocked by the browser; the caller shows a message

  const rows = budget.items
    .map(
      (item) => `
      <tr>
        <td>${esc(item.description)}</td>
        <td class="num">${item.quantity}</td>
        <td class="num">${money(item.price)}</td>
        <td class="num">${item.discount ? '− ' + money(item.discount) : '—'}</td>
        <td class="num"><b>${money(item.net_price * item.quantity)}</b></td>
      </tr>`,
    )
    .join('');

  const issued = new Date(budget.created_at).toLocaleDateString('es', {
    day: 'numeric',
    month: 'long',
    year: 'numeric',
  });

  win.document.write(`<!doctype html>
<html lang="es"><head><meta charset="utf-8">
<title>Presupuesto · ${esc(patientName)}</title>
<style>
  * { box-sizing: border-box; }
  body { font-family: 'Inter', 'Helvetica Neue', Arial, sans-serif; color: #0f2427;
         margin: 0; padding: 40px 48px; font-size: 13px; line-height: 1.5; }
  header { display: flex; justify-content: space-between; align-items: flex-start;
           border-bottom: 2px solid #0d7f76; padding-bottom: 16px; margin-bottom: 24px; }
  h1 { margin: 0; font-size: 22px; letter-spacing: -0.02em; color: #0d7f76; }
  .clinic { text-align: right; font-size: 12px; color: #4a5c5f; }
  .clinic b { color: #0f2427; font-size: 14px; }
  .meta { display: grid; grid-template-columns: 1fr 1fr; gap: 6px 24px; margin-bottom: 24px; }
  .meta span { color: #6b7c7e; font-size: 11px; display: block; }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; font-size: 11px; color: #6b7c7e; font-weight: 600;
       border-bottom: 1px solid #cfd8d9; padding: 8px 6px; }
  td { padding: 9px 6px; border-bottom: 1px solid #eef2f2; }
  .num { text-align: right; font-variant-numeric: tabular-nums; white-space: nowrap; }
  .totals { margin-left: auto; width: 280px; margin-top: 16px; }
  .totals div { display: flex; justify-content: space-between; padding: 4px 6px; }
  .totals .grand { border-top: 2px solid #0f2427; margin-top: 6px; padding-top: 8px;
                   font-size: 16px; font-weight: 700; }
  .notes { margin-top: 28px; padding: 12px 14px; background: #f4f7f7; border-radius: 8px; }
  .sign { display: grid; grid-template-columns: 1fr 1fr; gap: 48px; margin-top: 72px; }
  .sign div { border-top: 1px solid #0f2427; padding-top: 6px; font-size: 11px;
              color: #4a5c5f; text-align: center; }
  footer { margin-top: 36px; font-size: 10.5px; color: #8a9a9c; }
  @media print { body { padding: 0 8px; } }
</style></head><body>
  <header>
    <div>
      <h1>Presupuesto</h1>
      <div>${esc(planTitle ?? '')}</div>
    </div>
    <div class="clinic">
      <b>${esc(clinic?.name ?? '')}</b><br>
      ${clinic?.legal_name ? esc(clinic.legal_name) + '<br>' : ''}
      ${clinic?.tax_id ? 'RUC ' + esc(clinic.tax_id) + '<br>' : ''}
      ${clinic?.address ? esc(clinic.address) + '<br>' : ''}
      ${[clinic?.phone, clinic?.email].filter(Boolean).map(esc).join(' · ')}
    </div>
  </header>

  <div class="meta">
    <div><span>Paciente</span><b>${esc(patientName)}</b></div>
    <div><span>Fecha</span>${esc(issued)}</div>
  </div>

  <table>
    <thead><tr>
      <th>Tratamiento</th><th class="num">Cant.</th><th class="num">Precio</th>
      <th class="num">Descuento</th><th class="num">Importe</th>
    </tr></thead>
    <tbody>${rows}</tbody>
  </table>

  <div class="totals">
    <div><span>Subtotal</span><span class="num">${money(budget.subtotal)}</span></div>
    ${budget.tax_rate ? `<div><span>Impuesto (${budget.tax_rate} %)</span><span class="num">${money(budget.tax_amount)}</span></div>` : ''}
    <div class="grand"><span>Total</span><span class="num">${money(budget.total)}</span></div>
  </div>

  ${budget.notes ? `<div class="notes">${esc(budget.notes)}</div>` : ''}

  <div class="sign">
    <div>Firma del profesional</div>
    <div>Firma del paciente — acepto el presupuesto</div>
  </div>

  <footer>Presupuesto con validez de 30 días desde su emisión, salvo indicación en contrario.</footer>
  <script>window.onload = () => { window.focus(); window.print(); };</script>
</body></html>`);
  win.document.close();
}
