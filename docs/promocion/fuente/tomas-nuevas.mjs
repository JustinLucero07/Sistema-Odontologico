// Tomas de las funciones nuevas: facturación SRI, consentimientos con firma,
// app con login animado y Liquid Glass, trabajo sin internet y tablet.
// node tomas-nuevas.mjs [nombre ...]
import { abrir, grabar, mover, clic, escribir, rueda, sleep, tocar, deslizar } from './grabadora.mjs';
const SOLO = process.argv.slice(2);
const quiere = (n) => !SOLO.length || SOLO.includes(n);
const WEB = 'http://localhost:4200', APP = 'http://localhost:5050', API = 'http://localhost:8000/api/v1';
const PACIENTE = process.env.PACIENTE, CONSENT = process.env.CONSENT;
const sinPendientes = async (ctx) => ctx.route('**/api/v1/auth/me', async (route) => { const r = await route.fetch(); const j = await r.json(); j.confidentiality_required = false; j.must_change_password = false; await route.fulfill({ response: r, json: j }); });

// Facturas de demostración (la emisión real necesita la firma de la consulta y el SRI).
const hoy = new Date(); const iso = (d) => d.toISOString().slice(0, 10);
const linea = (id, d, base, iva, code) => ({ id, charge_id: null, code: 'S1', description: d, quantity: '1', unit_price: String(base), discount: '0', subtotal: base.toFixed(2), vat_code: code, vat_rate: code === '4' ? '15' : '0', vat: iva.toFixed(2) });
const factura = (n, nombre, ced, total, estado = 'autorizada', dias = 0, conIva = false) => {
  const base = conIva ? +(total / 1.15).toFixed(2) : total, iva = conIva ? +(total - base).toFixed(2) : 0;
  const d = new Date(hoy); d.setDate(d.getDate() - dias);
  return { id: 'f' + n, doc_type: '01', number: `001-001-${String(n).padStart(9, '0')}`, patient_id: PACIENTE, modified_invoice_id: null, reason: null, environment: '2',
    access_key: `${iso(d).split('-').reverse().join('')}01179001234500120010010000000${String(n).padStart(2, '0')}12345678${n % 10}`.slice(0, 49).padEnd(49, '7'),
    issue_date: iso(d), buyer_id_type: '05', buyer_id: ced, buyer_name: nombre, buyer_email: 'paciente@correo.ec', buyer_address: 'Quito', buyer_phone: '0999123456',
    payment_method: '19', subtotal: base.toFixed(2), discount: '0.00', vat: iva.toFixed(2), total: total.toFixed(2), notes: null, status: estado, sri_messages: [],
    authorized_at: estado === 'autorizada' ? d.toISOString() : null, attempts: 0, next_attempt_at: null, last_error: null, emailed_at: d.toISOString(), discarded_at: null, discard_reason: null,
    created_at: d.toISOString(), credited: '0', lines: [linea('l' + n, conIva ? 'Blanqueamiento estético' : 'Tratamiento odontológico', base, iva, conIva ? '4' : '0')] };
};
const FACTURAS = [
  factura(48, 'Andrés Guerrero', '1734256684', 115, 'autorizada', 0, true),
  factura(47, 'Camila Paredes', '1742301241', 40, 'autorizada', 0),
  factura(46, 'Carlos Pérez', '0607080910', 850, 'autorizada', 1),
  factura(45, 'Daniel Proaño', '1783517017', 60, 'autorizada', 2),
  factura(44, 'Diego Castro', '1788590039', 180, 'autorizada', 3),
  factura(43, 'Emilia Navarrete', '1795753514', 35, 'autorizada', 5),
  factura(42, 'Gabriela Salinas', '0992346398', 1200, 'autorizada', 6),
];
async function facturasDemo(ctx) {
  await ctx.route('**/api/v1/invoicing/settings', async (route) => { const r = await route.fetch(); const j = await r.json(); j.missing = []; j.has_certificate = true; j.environment = '2'; j.certificate_subject = 'CN=CLINICA DENTAL SONRISA'; j.email_configured = true; await route.fulfill({ response: r, json: j }); });
  await ctx.route(/\/api\/v1\/invoices(\?.*)?$/, async (route) => {
    if (route.request().method() === 'POST') return route.fulfill({ status: 201, json: FACTURAS[0] });
    return route.fulfill({ json: FACTURAS });
  });
  await ctx.route(/\/api\/v1\/invoices\/f\d+$/, (route) => route.fulfill({ json: FACTURAS.find((f) => route.request().url().endsWith('/' + f.id)) }));
  await ctx.route(/\/api\/v1\/patients\/[^/]+\/invoices$/, (route) => route.fulfill({ json: [FACTURAS[0]] }));
}

// ------------------------------------------------------------------ Web
if (['web-20-facturas', 'web-21-emitir', 'web-22-firma'].some(quiere)) {
  const { navegador, ctx, p } = await abrir({ ancho: 1920, alto: 1080 });
  await sinPendientes(ctx); await facturasDemo(ctx);
  const ir = async (r, e = 2500) => { await p.goto(WEB + r, { waitUntil: 'domcontentloaded' }); await sleep(e); };
  await ir('/login', 1500);
  await p.fill('input[type=email]', 'admin@clinicademo.com'); await p.fill('input[type=password]', 'Admin123!');
  await p.locator('button[type=submit]').click(); await p.waitForURL(/dashboard/); await sleep(1500);
  const g = (n, fn) => quiere(n) ? grabar(p, `tomas/${n}.mp4`, fn, { ancho: 1920, alto: 1080 }) : null;

  if (quiere('web-20-facturas')) {
    await ir('/invoices', 3000);
    await g('web-20-facturas', async () => {
      await sleep(600);
      for (const x of [520, 860, 1200, 1540]) { await mover(p, x, 300, 420); await sleep(260); }
      await mover(p, 900, 600, 500); await sleep(400);
      await clic(p, p.locator('.list .row').nth(0), { ms: 700, pausa: 2200 });
      await mover(p, 1100, 800, 600); await sleep(1600);
      await p.keyboard.press('Escape'); await sleep(900);
    });
  }
  if (quiere('web-21-emitir')) {
    await ir(`/patients/${PACIENTE}`, 3500);
    await p.getByRole('tab', { name: 'Pagos' }).click(); await sleep(2000);
    await g('web-21-emitir', async () => {
      await sleep(400);
      await clic(p, p.getByRole('button', { name: 'Facturar' }), { ms: 800, pausa: 1800 });
      // Solo el blanqueamiento: se desmarcan los cargos pendientes de la cuenta.
      const marcas = p.locator('mat-dialog-container .rows mat-checkbox');
      for (let i = 0; i < await marcas.count(); i++) await clic(p, marcas.nth(i).locator('input'), { ms: 350, pausa: 150 });
      await clic(p, p.getByRole('button', { name: 'Agregar concepto' }), { ms: 600, pausa: 500 });
      const fila = p.locator('mat-dialog-container .manual').last();
      await clic(p, fila.locator('input').nth(0), { ms: 500, pausa: 150 }); await escribir(p, 'Blanqueamiento estético', 35);
      await clic(p, fila.locator('input').nth(2), { ms: 450, pausa: 150 }); await escribir(p, '115', 80);
      await clic(p, fila.locator('mat-select'), { ms: 450, pausa: 500 });
      await clic(p, p.getByRole('option', { name: 'IVA 15 %' }), { ms: 400, pausa: 900 });
      await clic(p, p.getByRole('button', { name: 'Emitir factura' }), { ms: 700, pausa: 2600 });
      await mover(p, 1000, 640, 600); await sleep(1800);
    });
  }
  if (quiere('web-22-firma')) {
    await ir(`/patients/${PACIENTE}`, 3500);
    await p.getByRole('tab', { name: 'Documentos' }).click(); await sleep(1500);
    await p.getByRole('button', { name: /Consentimientos/ }).first().click(); await sleep(1500);
    await g('web-22-firma', async () => {
      await sleep(500);
      await clic(p, p.getByRole('button', { name: /Firmar aquí/ }).first(), { ms: 800, pausa: 1800 });
      const lienzo = p.locator('mat-dialog-container app-signature-pad canvas').first();
      await lienzo.scrollIntoViewIfNeeded(); await sleep(600);
      const b = await lienzo.boundingBox();
      await mover(p, b.x + 60, b.y + 110, 600); await p.mouse.down();
      for (let i = 0; i <= 50; i++) { const t = i / 50; await p.mouse.move(b.x + 60 + t * (b.width - 140), b.y + 110 - Math.sin(t * Math.PI * 3.2) * 42 - t * 18); await sleep(14); }
      await p.mouse.up(); await sleep(200);
      await mover(p, b.x + b.width * 0.42, b.y + 60, 300); await p.mouse.down();
      for (let i = 0; i <= 12; i++) { await p.mouse.move(b.x + b.width * 0.42 + i * 2, b.y + 60 + i * 7); await sleep(14); }
      await p.mouse.up(); await sleep(700);
      await clic(p, p.locator('mat-dialog-container').getByRole('button', { name: 'Firmar' }), { ms: 700, pausa: 2400 });
      await rueda(p, 450, 1200); await sleep(1600);
    });
  }
  await navegador.close();
}

// ------------------------------------------------- Firma a distancia (celular)
if (quiere('movil-23-firma') && process.env.ENLACE) {
  const { navegador, p } = await abrir({ ancho: 400, alto: 866, escala: 2.7, movil: true });
  await p.goto(process.env.ENLACE); await sleep(3500);
  await grabar(p, 'tomas/movil-23-firma.mp4', async () => {
    await sleep(800);
    await deslizar(p, 200, 700, 260, 900); await sleep(700);
    await deslizar(p, 200, 700, 200, 900); await sleep(500);
    await p.locator('input[inputmode=numeric]').scrollIntoViewIfNeeded(); await sleep(500);
    await clic(p, p.locator('input[inputmode=numeric]'), { ms: 500, pausa: 200 }); await escribir(p, '1734256684', 45);
    await p.keyboard.press('Tab'); await sleep(300);
    const lienzo = p.locator('app-signature-pad canvas');
    await lienzo.scrollIntoViewIfNeeded(); await sleep(900);
    const b = await lienzo.boundingBox();
    await mover(p, b.x + 30, b.y + 115, 400); await p.mouse.down();
    for (let i = 0; i <= 45; i++) { const t = i / 45; await p.mouse.move(b.x + 30 + t * (b.width - 70), b.y + 115 - Math.sin(t * Math.PI * 3) * 40 - t * 15); await sleep(16); }
    await p.mouse.up(); await sleep(600);
    await clic(p, p.getByText('He leído el consentimiento completo'), { ms: 500, pausa: 500 });
    await clic(p, p.getByRole('button', { name: 'Firmar y enviar' }), { ms: 600, pausa: 2800 });
  }, { ancho: 1080, alto: 2338 });
  await navegador.close();
}

// ------------------------------------------------------------------ App
const NAV = { panel: [67, 822], agenda: [155, 822], pacientes: [245, 822], mas: [333, 822] };
if (['app-20-login', 'app-21-glass', 'app-22-ficha', 'app-23-sin-red'].some(quiere)) {
  const { navegador, ctx, p } = await abrir({ ancho: 400, alto: 866, escala: 2.7, movil: true });
  await sinPendientes(ctx);
  const g = (n, fn) => quiere(n) ? grabar(p, `tomas/${n}.mp4`, fn, { ancho: 1080, alto: 2338 }) : null;
  const entrar = async () => {
    await tocar(p, 199, 639, 250); await escribir(p, 'admin@clinicademo.com', quiere('app-20-login') ? 32 : 4);
    await tocar(p, 199, 699, 250); await escribir(p, 'Admin123!', quiere('app-20-login') ? 55 : 4);
    await tocar(p, 199, 767, 200);
  };
  await p.goto('about:blank');
  if (quiere('app-20-login')) {
    await g('app-20-login', async () => {
      await p.goto(APP + '/'); await sleep(4200);
      await entrar(); await sleep(4200);
    });
  } else { await p.goto(APP + '/'); await sleep(6000); await entrar(); await sleep(5000); }
  if (quiere('app-21-glass')) {
    await g('app-21-glass', async () => {
      await sleep(600);
      for (const k of ['agenda', 'pacientes', 'mas', 'panel', 'pacientes']) { await tocar(p, ...NAV[k], 1250); }
    });
  }
  if (quiere('app-22-ficha')) {
    await tocar(p, ...NAV.pacientes, 2200);
    await g('app-22-ficha', async () => {
      await sleep(400);
      await tocar(p, 200, 150, 3200);
      for (let i = 0; i < 2; i++) await tocar(p, 343, 80, 1500);
      await deslizar(p, 200, 600, 300, 700); await sleep(1300);
      for (let i = 0; i < 4; i++) await tocar(p, 343, 80, 1000);
      await sleep(900);
    });
  }
  if (quiere('app-23-sin-red')) {
    await p.goto(APP + '/'); await sleep(6500);
    // Lo que se ve con red queda guardado: una ficha y la agenda de hoy.
    await tocar(p, ...NAV.pacientes, 2200); await tocar(p, 200, 150, 3500); await p.goBack(); await sleep(1500);
    await tocar(p, ...NAV.agenda, 2500); await tocar(p, ...NAV.pacientes, 2000);
    await g('app-23-sin-red', async () => {
      await sleep(600);
      await ctx.setOffline(true);
      await tocar(p, ...NAV.agenda, 2600);
      await deslizar(p, 200, 650, 380, 700); await sleep(900);
      await tocar(p, ...NAV.pacientes, 1500);
      await tocar(p, 200, 150, 2600);
      await p.goBack(); await sleep(1000);
      await ctx.setOffline(false);
      await tocar(p, ...NAV.panel, 3200);
    });
  }
  await navegador.close();
}

if (quiere('app-24-tablet')) {
  const { navegador, ctx, p } = await abrir({ ancho: 1280, alto: 800, escala: 1.5, movil: true });
  await sinPendientes(ctx);
  await p.goto(APP + '/'); await sleep(6500);
  await tocar(p, 640, 573, 250); await escribir(p, 'admin@clinicademo.com', 4);
  await tocar(p, 640, 633, 250); await escribir(p, 'Admin123!', 4); await tocar(p, 640, 701, 200); await sleep(6000);
  await grabar(p, 'tomas/app-24-tablet.mp4', async () => {
    await sleep(900);
    await tocar(p, 58, 462, 2200);
    await tocar(p, 220, 160, 3500);
    await tocar(p, 220, 240, 3200);
    await tocar(p, 58, 394, 2200);
  }, { ancho: 1920, alto: 1200 });
  await navegador.close();
}
console.log('tomas nuevas listas');
