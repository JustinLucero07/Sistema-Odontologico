import { abrir, grabar, mover, tocar, escribir, rueda, sleep } from './grabadora.mjs';
const W = 1080, H = 2338, A = 400, L = 866;
const SOLO = process.argv.slice(2);
const { navegador, ctx, p } = await abrir({ ancho: A, alto: L, escala: 2.7, movil: true });
await ctx.route('**/api/v1/auth/me', async (route) => { const r = await route.fetch(); const j = await r.json(); j.confidentiality_required = false; j.must_change_password = false; await route.fulfill({ response: r, json: j }); });
const g = async (n, fn) => { if (SOLO.length && !SOLO.includes(n)) return; await grabar(p, `tomas/${n}.mp4`, fn, { ancho: W, alto: H }); };
const NAV = { panel: [67, 818], agenda: [155, 818], pacientes: [245, 818], mas: [333, 818] };
const inicio = async () => { await p.reload(); await sleep(6000); };
const bajar = async (dy, ms = 1300) => { await mover(p, 200, 500, 300); await rueda(p, dy, ms); };

await p.goto('http://localhost:5050/'); await sleep(6000);
await g('app-01-ingreso', async () => {
  await sleep(500);
  await tocar(p, 199, 440); await escribir(p, 'admin@clinicademo.com', 35);
  await tocar(p, 199, 502); await escribir(p, 'Admin123!', 60);
  await tocar(p, 199, 572, 200); await sleep(4200);
});
if (p.url() && SOLO.length && !SOLO.includes('app-01-ingreso')) {
  await tocar(p, 199, 440); await escribir(p, 'admin@clinicademo.com', 5);
  await tocar(p, 199, 502); await escribir(p, 'Admin123!', 5); await tocar(p, 199, 572); await sleep(5000);
}

await inicio();
await g('app-02-panel', async () => {
  await sleep(900); await mover(p, 200, 300, 500); await sleep(500);
  await bajar(500); await sleep(1300); await bajar(-500, 1000); await sleep(500);
  await tocar(p, 199, 180, 2600);
  await bajar(400); await sleep(1500);
});

await inicio();
await g('app-03-agenda', async () => {
  await tocar(p, ...NAV.agenda, 1800);
  await bajar(600, 1600); await sleep(1000);
  await tocar(p, 332, 80, 1800);
  await tocar(p, 332, 80, 1800);
});

await inicio();
await g('app-04-paciente', async () => {
  await tocar(p, ...NAV.pacientes, 1500);
  await tocar(p, 200, 82, 600); await escribir(p, 'Isabe', 110); await sleep(1600);
  await tocar(p, 200, 156, 2300);
  await tocar(p, 216, 78, 3200);
  await bajar(400); await sleep(1500);
});

await inicio();
await g('app-05-cartera', async () => {
  await tocar(p, ...NAV.mas, 1300);
  await tocar(p, 175, 419, 2600);
  await bajar(450); await sleep(1200);
  await tocar(p, 195, 78, 2200);
  await tocar(p, 325, 78, 2200);
});

await inicio();
await g('app-06-finanzas', async () => {
  await tocar(p, ...NAV.mas, 1300);
  await tocar(p, 304, 419, 2600);
  await bajar(400); await sleep(1200);
});

await inicio();
await g('app-07-oportunidades', async () => {
  await tocar(p, ...NAV.mas, 1300);
  await tocar(p, 68, 170, 2600);
  await bajar(500); await sleep(1500);
});
await navegador.close();
