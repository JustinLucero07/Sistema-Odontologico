import { abrir, grabar, mover, clic, escribir, rueda, sleep, centro, ponerCursor } from './grabadora.mjs';
const W = 1920, H = 1080, URL = 'http://localhost:4200';
const SOLO = process.argv.slice(2);
const { navegador, ctx, p } = await abrir({ ancho: W, alto: H });
await ctx.route('**/api/v1/auth/me', async (route) => { const r = await route.fetch(); const j = await r.json(); j.confidentiality_required = false; j.must_change_password = false; await route.fulfill({ response: r, json: j }); });
const ir = async (ruta, espera = 2200) => { await p.goto(URL + ruta, { waitUntil: 'domcontentloaded' }); await sleep(espera); };
const nav = (txt) => p.locator('mat-sidenav').getByText(txt, { exact: true }).first();
const tab = (txt) => p.getByRole('tab', { name: txt, exact: true });
const g = async (nombre, fn) => { if (SOLO.length && !SOLO.includes(nombre)) return; await grabar(p, `tomas/${nombre}.mp4`, fn, { ancho: W, alto: H }); };
const entrar = async () => {
  await ir('/login', 1500);
  if (!p.url().includes('/login')) return;
  await p.fill('input[type=email]', 'admin@clinicademo.com'); await p.fill('input[type=password]', 'Admin123!');
  await p.locator('button[type=submit]').click(); await p.waitForURL(/dashboard/); await sleep(1500);
};

// 01 Ingreso
if (!SOLO.length || SOLO.includes('web-01-ingreso')) {
  await ir('/login', 2000);
  await g('web-01-ingreso', async () => {
    await sleep(600);
    await clic(p, p.locator('input[type=email]'), { ms: 900 });
    await escribir(p, 'admin@clinicademo.com', 35);
    await clic(p, p.locator('input[type=password]'), { ms: 500 });
    await escribir(p, 'Admin123!', 60);
    await clic(p, p.locator('button[type=submit]'), { ms: 600, pausa: 200 });
    await p.waitForURL(/dashboard/); await sleep(3200);
  });
}
await entrar();

// 02 Panel
await ir('/dashboard', 2500);
await g('web-02-panel', async () => {
  await sleep(700);
  await mover(p, 1790, 195, 900); await sleep(700);
  for (const x of [480, 890, 1290, 1700]) { await mover(p, x, 360, 450); await sleep(350); }
  await mover(p, 900, 620, 500);
  await rueda(p, 700, 1600); await sleep(1400);
  await rueda(p, -700, 1300); await sleep(600);
});

// 03 Agenda
await ir('/dashboard', 2000);
await g('web-03-agenda', async () => {
  await clic(p, nav('Agenda'), { pausa: 2200 });
  await clic(p, p.locator('.shell-content').getByText('Semana', { exact: true }).first(), { pausa: 1800 });
  await mover(p, 1100, 600, 700); await sleep(600);
  await clic(p, p.getByRole('button', { name: /Nueva cita/ }).first(), { pausa: 2000 });
  await clic(p, p.getByRole('button', { name: 'Cerrar' }).last(), { ms: 500, pausa: 900 });
});

// 04 Paciente
await ir('/patients', 2000);
await g('web-04-paciente', async () => {
  await sleep(500);
  await clic(p, p.getByText('Isabella Zambrano').first(), { pausa: 2200 });
  for (const t of ['Historia clínica', 'Tratamientos', 'Citas', 'Pagos']) await clic(p, tab(t), { ms: 550, pausa: 1500 });
});

// 05 Odontograma
const pac = await (async () => { await ir('/patients', 1500); await p.getByText('Isabella Zambrano').first().click(); await sleep(1800); return p.url(); })();
await p.goto(pac); await sleep(2000);
await tab('Odontograma').click(); await sleep(2000);
await g('web-05-odontograma', async () => {
  const pieza = async (n, dy) => { const [x, y] = await centro(p.getByRole('button', { name: n, exact: true }).first()); return [x, y + dy]; };
  const pintar = async (n, dy, ox = 0, oy = 0) => { const [x, y] = await pieza(n, dy); await mover(p, x + ox, y + oy, 450); await p.mouse.down(); await sleep(60); await p.mouse.up(); await sleep(450); };
  await sleep(500);
  await pintar('16', -28); await pintar('16', -28, 0, -9);
  await pintar('46', 28); await pintar('47', 28, 0, 9);
  await clic(p, p.getByRole('button', { name: 'Restauración', exact: true }), { pausa: 400 });
  await pintar('26', -28); await pintar('36', 28);
  await clic(p, p.getByRole('button', { name: 'Corona', exact: true }), { pausa: 400 });
  await clic(p, p.getByRole('button', { name: '11', exact: true }), { ms: 500, pausa: 500 });
  await clic(p, p.getByRole('button', { name: 'Implante', exact: true }), { pausa: 400 });
  await clic(p, p.getByRole('button', { name: '37', exact: true }), { ms: 500, pausa: 900 });
  await clic(p, p.getByRole('button', { name: /Guardar nueva versión/ }), { ms: 800, pausa: 2200 });
});

// 06 Oportunidades
await ir('/dashboard', 1800);
await g('web-06-oportunidades', async () => {
  await clic(p, nav('Oportunidades'), { pausa: 2000 });
  await clic(p, p.getByText('Saldos pendientes').first(), { pausa: 1500 });
  await clic(p, p.getByText('Tratamientos aprobados sin cita').first(), { pausa: 1500 });
  const [wx, wy] = await centro(p.locator('.shell-content').getByText('WhatsApp', { exact: true }).first());
  await mover(p, wx, wy, 700);
  await sleep(1500);
});

// 07 Cartera
await ir('/dashboard', 1800);
await g('web-07-cartera', async () => {
  await clic(p, nav('Cartera'), { pausa: 2200 });
  await mover(p, 900, 600, 600); await sleep(500);
  await clic(p, p.getByRole('button', { name: /Cargos y abonos/ }), { pausa: 2000 });
  await clic(p, p.getByRole('button', { name: /Tratamientos/ }).first(), { pausa: 2000 });
  await clic(p, p.getByRole('button', { name: /Pacientes/ }).first(), { pausa: 1200 });
});

// 08 Finanzas
await ir('/dashboard', 1800);
await g('web-08-finanzas', async () => {
  await clic(p, nav('Finanzas'), { pausa: 2200 });
  await clic(p, p.locator('.shell-content').getByText('Gastos fijos').first(), { pausa: 2200 });
  await clic(p, p.locator('.shell-content').getByText('Proyección').first(), { pausa: 2600 });
});

// 09 Comprobante / estado de cuenta (la ventana de impresión se graba aparte)
await p.goto(pac); await sleep(1800); await tab('Pagos').click(); await sleep(1800);
if (!SOLO.length || SOLO.includes('web-09-comprobante')) {
  const [vent] = await Promise.all([ctx.waitForEvent('page'), p.getByRole('button', { name: /Estado de cuenta/ }).first().click()]);
  await sleep(1500);
  const html = await vent.content(); await vent.close();
  // Vista previa: la hoja como sale impresa, sobre un fondo neutro.
  const doc = await ctx.newPage(); doc.__pos = { x: 1500, y: 700 };
  await doc.setContent(`<!doctype html><html><head><style>html,body{margin:0;background:#e9eef0}
    .hoja{zoom:1.5;width:900px;margin:40px auto 80px;background:#fff;border-radius:6px;box-shadow:0 30px 80px -30px rgba(10,40,45,.45),0 0 0 1px rgba(0,0,0,.04)}
    iframe{display:block;width:900px;border:0}</style></head><body><div class="hoja"><iframe id="f"></iframe></div></body></html>`);
  await doc.evaluate((h) => new Promise((ok) => { const f = document.getElementById('f'); f.onload = () => { f.style.height = f.contentDocument.documentElement.scrollHeight + 40 + 'px'; ok(); }; f.srcdoc = h; }), html);
  await ponerCursor(doc);
  await sleep(1500);
  await grabar(doc, 'tomas/web-09-comprobante.mp4', async () => {
    await sleep(900); await mover(doc, 1180, 520, 900); await sleep(400);
    await rueda(doc, 450, 1600); await sleep(1300); await rueda(doc, 550, 1500); await sleep(1300); await rueda(doc, -1000, 1500); await sleep(600);
  }, { ancho: W, alto: H });
  await doc.close();
  await p.bringToFront();
}

// 10 Personalización: el color cambia en vivo en toda la app
await ir('/settings/branding', 2500);
await g('web-10-marca', async () => {
  await clic(p, p.getByRole('button', { name: /Continuar/ }), { pausa: 900 });
  await clic(p, p.getByRole('button', { name: /Continuar/ }), { pausa: 1200 });
  const logo = p.locator('input[type=file]').first();
  if (await logo.count()) { await logo.setInputFiles('logo-demo.png'); await sleep(1200); }
  const colores = p.locator('.colores button.color');
  const n = await colores.count();
  for (const i of [3, 1, 4, 7, 0].filter((k) => k < n)) await clic(p, colores.nth(i), { ms: 450, pausa: 1100 });
  await sleep(600);
});

// 11 Legal y cumplimiento
await ir('/settings/compliance', 2500);
await g('web-11-legal', async () => {
  await mover(p, 800, 420, 800); await sleep(600);
  for (const y of [470, 590, 710, 830]) { await mover(p, 760, y, 380); await sleep(250); }
  await clic(p, p.getByRole('tab', { name: /Términos/ }), { pausa: 1200 });
  await clic(p, p.getByText('Contrato de encargo de tratamiento').first(), { pausa: 1800 });
  await mover(p, 900, 600, 500); await rueda(p, 500, 1400); await sleep(900);
  await p.keyboard.press('Escape'); await sleep(500);
  await clic(p, p.getByRole('tab', { name: /Solicitudes/ }), { pausa: 1500 });
});

// 12 Modo oscuro
await p.evaluate((k) => localStorage.setItem(k, 'light'), 'odonto.theme');
await ir('/dashboard', 2500);
await g('web-12-modo-oscuro', async () => {
  const boton = p.locator('button.theme-toggle');
  await clic(p, boton, { ms: 900, pausa: 2200 });
  await mover(p, 900, 600, 600); await rueda(p, 600, 1400); await sleep(1000); await rueda(p, -600, 1200); await sleep(700);
  await clic(p, boton, { ms: 700, pausa: 1500 });
});
await p.evaluate((k) => localStorage.setItem(k, 'light'), 'odonto.theme');

// 13 Búsqueda instantánea
await ir('/dashboard', 2200);
await g('web-13-busqueda', async () => {
  await mover(p, 480, 42, 700); await sleep(300);
  await p.keyboard.press('Control+k'); await sleep(500);
  await escribir(p, 'Cam', 140); await sleep(1500);
  await clic(p, p.getByText('Camila Paredes').first(), { pausa: 2400 });
});

await navegador.close();
