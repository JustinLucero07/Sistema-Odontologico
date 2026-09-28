import { ClinicIdentity, clinicBlock, esc, longDate, openPrintWindow } from './print-document';

const money = (v: string | number) =>
  '$ ' + new Intl.NumberFormat('es', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(v));

export interface ReceiptData {
  number: string;
  received_on: string;
  patient_name: string;
  patient_id_number: string | null;
  concept: string;
  amount: string;
  method_label: string;
  reference: string | null;
  received_by: string | null;
  /** Saldo que queda después de este pago, si se conoce. */
  balance_after: string | null;
}

/** Recibo de pago para el paciente: constancia interna de lo que pagó. No es
 *  una factura; lo dice el propio documento para que nadie lo confunda. */
export function printReceipt(data: ReceiptData, clinic: ClinicIdentity | null): boolean {
  return openPrintWindow(
    `Recibo · ${data.patient_name}`,
    `
    body { max-width: 640px; margin: 0 auto; }
    .amount { margin: 20px 0; padding: 18px; text-align: center; border-radius: 10px;
              background: #f4f7f7; font-size: 28px; font-weight: 700; color: #0d7f76; }
    .amount span { display: block; font-size: 11px; font-weight: 500; color: #6b7c7e; }
    `,
    `
  <header>
    <div>
      <h1>Recibo de pago</h1>
      <div>N.° ${esc(data.number)}</div>
    </div>
    <div class="clinic">${clinicBlock(clinic)}</div>
  </header>
  <div class="meta">
    <div><span>Recibimos de</span><b>${esc(data.patient_name)}</b></div>
    <div><span>Cédula</span>${esc(data.patient_id_number || '—')}</div>
    <div><span>Fecha</span>${longDate(data.received_on)}</div>
    <div><span>Medio de pago</span>${esc(data.method_label)}${data.reference ? ` · Ref. ${esc(data.reference)}` : ''}</div>
  </div>
  <div class="amount"><span>La cantidad de</span>${money(data.amount)}</div>
  <p><b>Por concepto de:</b> ${esc(data.concept)}</p>
  ${data.balance_after !== null ? `<p><b>Saldo pendiente después de este pago:</b> ${money(data.balance_after)}</p>` : ''}
  <div class="sign">
    <div>${esc(data.received_by || '')}<br>Recibí conforme</div>
    <div>${esc(data.patient_name)}<br>Paciente</div>
  </div>
  <footer>Este recibo es una constancia de pago y no reemplaza al comprobante de venta autorizado por el SRI.</footer>`,
  );
}
