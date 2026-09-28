import { CreditDetail } from '../../core/models/credit.models';
import { ClinicIdentity, clinicBlock, esc, longDate, openPrintWindow } from './print-document';

const money = (v: string | number) =>
  '$ ' + new Intl.NumberFormat('es', { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(Number(v));

/**
 * Acuerdo de pago en cuotas, para firmar. Recoge lo que el paciente acepta:
 * el monto financiado, la tasa (mensual y su equivalente anual), el costo
 * total del financiamiento, el calendario completo y las firmas, incluida la
 * del garante si lo hay. Mostrar el costo total del crédito es lo que la
 * normativa de protección al consumidor exige que el cliente conozca.
 */
export function printCreditAgreement(
  credit: CreditDetail,
  clinic: ClinicIdentity | null,
  patient: { national_id: string | null },
): boolean {
  const rows = credit.installments
    .map(
      (r) => `<tr>
        <td class="num">${r.number}</td><td>${longDate(r.due_on)}</td>
        <td class="num">${money(r.principal)}</td><td class="num">${money(r.interest)}</td>
        <td class="num"><b>${money(r.amount)}</b></td>
        <td>${r.status === 'pagada' ? 'Pagada' : ''}</td></tr>`,
    )
    .join('');
  const rate = Number(credit.monthly_rate);
  const guarantor = credit.guarantor_name
    ? `<p><b>Garante:</b> ${esc(credit.guarantor_name)}${credit.guarantor_id_number ? `, C.I. ${esc(credit.guarantor_id_number)}` : ''}${credit.guarantor_phone ? `, tel. ${esc(credit.guarantor_phone)}` : ''}. Se obliga solidariamente al pago de las cuotas si el paciente no lo hiciera.</p>`
    : '';

  return openPrintWindow(
    `Acuerdo de pago · ${credit.patient_name}`,
    `
    table { width: 100%; border-collapse: collapse; margin-top: 10px; font-size: 12px; }
    th { text-align: left; font-size: 11px; color: #6b7c7e; border-bottom: 1px solid #cfd8d9; padding: 6px; }
    td { padding: 6px; border-bottom: 1px solid #eef2f2; }
    .num { text-align: right; font-variant-numeric: tabular-nums; }
    .terms { display: grid; grid-template-columns: repeat(3, 1fr); gap: 8px 20px; margin: 16px 0;
             padding: 12px 14px; background: #f4f7f7; border-radius: 8px; }
    .terms span { display: block; color: #6b7c7e; font-size: 11px; }
    .sign { grid-template-columns: repeat(${credit.guarantor_name ? 3 : 2}, 1fr); }
    `,
    `
  <header>
    <div>
      <h1>Acuerdo de pago en cuotas</h1>
      <div>${esc(credit.charge_description)}</div>
    </div>
    <div class="clinic">${clinicBlock(clinic)}</div>
  </header>

  <div class="meta">
    <div><span>Paciente</span><b>${esc(credit.patient_name)}</b></div>
    <div><span>Cédula</span>${esc(patient.national_id || '—')}</div>
    <div><span>Fecha</span>${longDate(credit.created_at)}</div>
    <div><span>Frecuencia</span>${esc(credit.frequency_label)}</div>
  </div>

  <div class="terms">
    <div><span>Entrada pagada</span><b>${money(credit.down_payment)}</b></div>
    <div><span>Monto financiado</span><b>${money(credit.principal)}</b></div>
    <div><span>Número de cuotas</span><b>${credit.installments.length}</b></div>
    <div><span>Tasa de interés</span><b>${rate.toFixed(2)} % mensual (${(rate * 12).toFixed(2)} % anual)</b></div>
    <div><span>Costo del financiamiento</span><b>${money(credit.total_interest)}</b></div>
    <div><span>Total a pagar en cuotas</span><b>${money(credit.total)}</b></div>
  </div>

  <table>
    <thead><tr><th class="num">N.°</th><th>Vence</th><th class="num">Capital</th><th class="num">Interés</th><th class="num">Cuota</th><th></th></tr></thead>
    <tbody>${rows}</tbody>
  </table>

  <h2>Condiciones</h2>
  <p>El paciente se compromete a pagar cada cuota en su fecha de vencimiento. Los pagos se aplican a la
  cuota más antigua pendiente, primero al interés y luego al capital. Puede adelantar el pago de cuotas en
  cualquier momento sin recargo, y acordar con la clínica un nuevo calendario para el saldo pendiente.</p>
  ${guarantor}
  ${credit.notes ? `<p><b>Observaciones:</b> ${esc(credit.notes)}</p>` : ''}

  <div class="sign">
    <div>${esc(credit.patient_name)}<br>Paciente</div>
    ${credit.guarantor_name ? `<div>${esc(credit.guarantor_name)}<br>Garante</div>` : ''}
    <div>Por la clínica</div>
  </div>
  <footer>Este acuerdo no es un comprobante de venta. Cada pago se respalda con su recibo.</footer>`,
  );
}
