import { ClinicIdentity, clinicBlock, esc, longDate, openPrintWindow } from './print-document';

const money = (v: string | number) =>
  '$ ' + new Intl.NumberFormat('es', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(v));

export interface StatementData {
  patient_name: string;
  patient_id_number: string | null;
  total_charged: string;
  total_paid: string;
  balance: string;
  charges: { description: string; issued_on: string; amount: string; paid: string; pending: string; status: string; voided: boolean }[];
  payments: { received_on: string; amount: string; method_label: string; reference: string | null; voided: boolean }[];
}

/** Estado de cuenta: cuánto se cargó, cuánto abonó y cuánto le queda. */
export function printStatement(d: StatementData, clinic: ClinicIdentity | null): boolean {
  const saldo = Number(d.balance);
  const estado = saldo > 0 ? 'Saldo pendiente' : saldo < 0 ? 'Saldo a favor del paciente' : 'Cuenta saldada';
  const cargos = d.charges.filter((c) => !c.voided);
  const pagos = d.payments.filter((p) => !p.voided);
  return openPrintWindow(
    `Estado de cuenta · ${d.patient_name}`,
    `
    .totales { display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; margin: 8px 0 22px; }
    .totales div { padding: 14px; border-radius: 10px; background: #f4f7f7; }
    .totales span { display: block; font-size: 11px; color: #6b7c7e; }
    .totales b { font-size: 20px; }
    .totales .saldo { background: #0f2427; color: #fff; }
    .totales .saldo span { color: #b8c7c8; }
    table { width: 100%; border-collapse: collapse; margin-bottom: 18px; }
    th { text-align: left; font-size: 10.5px; text-transform: uppercase; letter-spacing: .05em; color: #6b7c7e; border-bottom: 1.5px solid #cdd8d8; padding: 6px 4px; }
    td { padding: 7px 4px; border-bottom: 1px solid #e8eeee; }
    td.n, th.n { text-align: right; font-variant-numeric: tabular-nums; }
    .chip { font-size: 10.5px; padding: 1px 8px; border-radius: 99px; background: #eef3f3; }
    .chip.pagada { background: #e3f4ea; color: #1e7a45; } .chip.pendiente { background: #fdecea; color: #b3352b; } .chip.parcial { background: #fdf4e3; color: #9a6a14; }
    `,
    `
  <header>
    <div><h1>Estado de cuenta</h1><div>Al ${longDate(new Date())}</div></div>
    <div class="clinic">${clinicBlock(clinic)}</div>
  </header>
  <div class="meta">
    <div><span>Paciente</span><b>${esc(d.patient_name)}</b></div>
    <div><span>Cédula</span>${esc(d.patient_id_number || '—')}</div>
  </div>
  <div class="totales">
    <div><span>Total de tratamientos</span><b>${money(d.total_charged)}</b></div>
    <div><span>Total abonado</span><b>${money(d.total_paid)}</b></div>
    <div class="saldo"><span>${estado}</span><b>${money(Math.abs(saldo))}</b></div>
  </div>
  <h2>Tratamientos y cargos</h2>
  <table><thead><tr><th>Fecha</th><th>Concepto</th><th class="n">Valor</th><th class="n">Abonado</th><th class="n">Pendiente</th><th>Estado</th></tr></thead><tbody>
  ${cargos.map((c) => `<tr><td>${new Date(c.issued_on + 'T12:00:00').toLocaleDateString('es')}</td><td>${esc(c.description)}</td><td class="n">${money(c.amount)}</td><td class="n">${money(c.paid)}</td><td class="n">${money(c.pending)}</td><td><span class="chip ${esc(c.status)}">${esc(c.status)}</span></td></tr>`).join('') || '<tr><td colspan="6">Sin cargos.</td></tr>'}
  </tbody></table>
  <h2>Abonos recibidos</h2>
  <table><thead><tr><th>Fecha</th><th>Medio de pago</th><th>Referencia</th><th class="n">Monto</th></tr></thead><tbody>
  ${pagos.map((p) => `<tr><td>${new Date(p.received_on + 'T12:00:00').toLocaleDateString('es')}</td><td>${esc(p.method_label)}</td><td>${esc(p.reference || '—')}</td><td class="n">${money(p.amount)}</td></tr>`).join('') || '<tr><td colspan="4">Sin abonos.</td></tr>'}
  </tbody></table>
  <footer>Documento informativo de la cuenta del paciente. No reemplaza al comprobante de venta autorizado por el SRI.</footer>`,
  );
}
