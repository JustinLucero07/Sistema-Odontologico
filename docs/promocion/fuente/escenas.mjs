import { createRequire } from 'module';
import fs from 'fs';
import path from 'path';
const require = createRequire('/usr/lib/node_modules/n8n/node_modules/');
const { chromium } = require('playwright-core');

const CAPS = path.resolve('../capturas');
const img = (n) => 'data:image/png;base64,' + fs.readFileSync(`${CAPS}/${n}.png`).toString('base64');
const CONTACTO = process.env.CONTACTO || 'Escríbenos y agenda tu demo gratuita';

const TOOTH = `<svg viewBox="0 0 32 32" width="100%" height="100%"><path d="M16 3.4c-6.1 0-10.6 3.3-10.6 8.9 0 3.9 1.1 6.9 1.9 10.9.6 3 1 5.8 3 5.8s2.4-2.7 3.1-5.5c.5-2 1.3-3.1 2.6-3.1s2.1 1.1 2.6 3.1c.7 2.8 1.1 5.5 3.1 5.5s2.4-2.8 3-5.8c.8-4 1.9-7 1.9-10.9 0-5.6-4.5-8.9-10.6-8.9Z" fill="#fff" stroke="#fff" stroke-width="1.7" stroke-linejoin="round"/><path d="M10.4 9.1c1-1.6 2.9-2.6 5-2.6" stroke="#0d7f76" stroke-width="1.6" stroke-linecap="round" opacity=".5" fill="none"/></svg>`;

const base = (w, h, dark) => `
<link href="https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@500;600;700;800&family=Inter:wght@400;500;600&display=swap" rel="stylesheet">
<style>
*{box-sizing:border-box;margin:0}
body{width:${w}px;height:${h}px;overflow:hidden;font-family:'Inter',sans-serif;
 background:${dark ? '#071516' : '#eef4f2'};color:${dark ? '#e7f1f1' : '#0f2427'};position:relative}
.amb{position:absolute;inset:0;background:
 radial-gradient(45% 50% at 12% 10%, ${dark ? 'rgba(52,211,192,.22)' : 'rgba(47,191,174,.30)'}, transparent 70%),
 radial-gradient(40% 45% at 92% 90%, ${dark ? 'rgba(226,177,85,.12)' : 'rgba(185,131,47,.18)'}, transparent 70%),
 radial-gradient(35% 40% at 85% 8%, ${dark ? 'rgba(80,120,255,.10)' : 'rgba(120,170,255,.16)'}, transparent 70%)}
h1,h2{font-family:'Plus Jakarta Sans',sans-serif;letter-spacing:-.035em;line-height:1.02}
.kicker{display:inline-flex;align-items:center;gap:12px;font-family:'Plus Jakarta Sans';font-weight:700;letter-spacing:.14em;text-transform:uppercase;color:#0d7f76}
.kicker i{width:12px;height:12px;border-radius:50%;background:linear-gradient(135deg,#2fbfae,#0d7f76);box-shadow:0 0 0 6px rgba(47,191,174,.18)}
.glass{background:${dark ? 'rgba(20,40,44,.55)' : 'rgba(255,255,255,.55)'};border:1.5px solid ${dark ? 'rgba(255,255,255,.1)' : 'rgba(255,255,255,.9)'};
 box-shadow:0 40px 90px -40px rgba(7,60,56,.55), inset 0 2px 0 rgba(255,255,255,.6);backdrop-filter:blur(30px)}
.win{border-radius:28px;overflow:hidden;position:relative}
.win .bar{height:44px;display:flex;align-items:center;gap:9px;padding:0 20px;background:${dark ? 'rgba(255,255,255,.04)' : 'rgba(255,255,255,.7)'}}
.win .bar b{width:13px;height:13px;border-radius:50%;display:block}
.win img{display:block;width:100%}
.logo{border-radius:28%;background:linear-gradient(135deg,#1fb3a4,#0d7f76 55%,#074a45);display:flex;align-items:center;justify-content:center;
 box-shadow:0 30px 60px -20px rgba(7,74,69,.7), inset 0 2px 0 rgba(255,255,255,.35)}
.logo div{width:56%;height:56%}
.pill{display:inline-flex;align-items:center;gap:10px;padding:14px 26px;border-radius:999px;font-weight:600}
</style><div class="amb"></div>`;

const ventana = (n, dark) => `<div class="win glass"><div class="bar"><b style="background:#ff5f57"></b><b style="background:#febc2e"></b><b style="background:#28c840"></b></div><img src="${img(n)}"></div>`;

// ---------- Escenas horizontales (1920x1080) ----------
const H = {
  intro: () => `${base(1920,1080)}
   <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:34px">
     <div class="logo" style="width:200px;height:200px"><div>${TOOTH}</div></div>
     <h1 style="font-size:112px">Sistema Odontológico</h1>
     <p style="font-size:40px;color:#4a6266;max-width:1200px">La gestión de tu clínica dental, en una sola pantalla.</p>
   </div>`,
  problema: () => `${base(1920,1080,true)}
   <div style="position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 200px;gap:28px">
     <h1 style="font-size:88px;color:#fff">¿Agenda en papel?</h1>
     <h1 style="font-size:88px;color:#fff;opacity:.85">¿Pacientes que no vuelven?</h1>
     <h1 style="font-size:88px;color:#fff;opacity:.7">¿Cobros que se olvidan?</h1>
     <p style="font-size:44px;color:#5ee0ce;margin-top:30px;font-family:'Plus Jakarta Sans';font-weight:700">Hay una forma más fácil.</p>
   </div>`,
  pantalla: (cap, kicker, titulo, sub, dark) => `${base(1920,1080,dark)}
   <div style="position:absolute;left:110px;top:0;bottom:0;width:560px;display:flex;flex-direction:column;justify-content:center;gap:26px">
     <span class="kicker" style="font-size:22px"><i></i>${kicker}</span>
     <h2 style="font-size:76px">${titulo}</h2>
     <p style="font-size:32px;line-height:1.4;color:${dark ? '#9fb7b8' : '#4a6266'}">${sub}</p>
   </div>
   <div style="position:absolute;left:740px;top:120px;width:1260px">${ventana(cap, dark)}</div>`,
  dispositivos: () => `${base(1920,1080,true)}
   <div style="position:absolute;left:110px;top:0;bottom:0;width:560px;display:flex;flex-direction:column;justify-content:center;gap:26px">
     <span class="kicker" style="font-size:22px;color:#5ee0ce"><i></i>Donde estés</span>
     <h2 style="font-size:76px;color:#fff">Computadora, tablet y celular</h2>
     <p style="font-size:32px;line-height:1.4;color:#9fb7b8">Modo claro y oscuro. Y app móvil para el sillón.</p>
   </div>
   <div style="position:absolute;left:720px;top:150px;width:1000px">${ventana('panel-oscuro', true)}</div>
   <div style="position:absolute;left:1500px;top:250px;width:330px;border-radius:52px;padding:12px;background:#0b1b1d;box-shadow:0 50px 90px -30px rgba(0,0,0,.8);border:2px solid rgba(255,255,255,.12)">
     <img src="${img('movil-oportunidades')}" style="width:100%;border-radius:42px;display:block"></div>`,
  confianza: () => `${base(1920,1080)}
   <div style="position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:60px">
     <h2 style="font-size:80px;text-align:center">Tus datos, seguros y en regla</h2>
     <div style="display:grid;grid-template-columns:repeat(2,640px);gap:26px">
       ${[['🔒','Conexión segura HTTPS'],['🛡️','Pensado para la LOPDP de Ecuador'],['💾','Respaldo automático diario'],['👥','Roles, permisos y registro de accesos']]
         .map(([e,t])=>`<div class="glass" style="border-radius:28px;padding:34px 38px;display:flex;align-items:center;gap:26px;font-size:34px;font-weight:600"><span style="font-size:52px">${e}</span>${t}</div>`).join('')}
     </div>
   </div>`,
  cta: () => `${base(1920,1080,true)}
   <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:36px">
     <div class="logo" style="width:150px;height:150px"><div>${TOOTH}</div></div>
     <h1 style="font-size:96px;color:#fff">Moderniza tu clínica hoy</h1>
     <div class="pill" style="font-size:40px;background:linear-gradient(135deg,#3ddcc8,#17a394);color:#04201d;padding:22px 46px;box-shadow:0 20px 50px -18px rgba(61,220,200,.7)">${CONTACTO}</div>
     <p style="font-size:30px;color:#9fb7b8">Sistema Odontológico · Web y app móvil</p>
   </div>`,
};

// ---------- Escenas verticales (1080x1920) ----------
const V = {
  intro: () => `${base(1080,1920)}
   <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:40px;padding:0 70px">
     <div class="logo" style="width:240px;height:240px"><div>${TOOTH}</div></div>
     <h1 style="font-size:104px">Sistema Odontológico</h1>
     <p style="font-size:46px;color:#4a6266">La gestión de tu clínica dental, en una sola pantalla.</p>
   </div>`,
  problema: () => `${base(1080,1920,true)}
   <div style="position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;padding:0 80px;gap:34px">
     <h1 style="font-size:92px;color:#fff">¿Agenda en papel?</h1>
     <h1 style="font-size:92px;color:#fff;opacity:.85">¿Pacientes que no vuelven?</h1>
     <h1 style="font-size:92px;color:#fff;opacity:.7">¿Cobros que se olvidan?</h1>
     <p style="font-size:52px;color:#5ee0ce;margin-top:30px;font-family:'Plus Jakarta Sans';font-weight:700">Hay una forma más fácil.</p>
   </div>`,
  pantalla: (cap, kicker, titulo, sub, dark, movil) => `${base(1080,1920,dark)}
   <div style="position:absolute;left:80px;right:80px;top:170px;display:flex;flex-direction:column;gap:24px">
     <span class="kicker" style="font-size:28px"><i></i>${kicker}</span>
     <h2 style="font-size:84px">${titulo}</h2>
     <p style="font-size:38px;line-height:1.35;color:${dark ? '#9fb7b8' : '#4a6266'}">${sub}</p>
   </div>
   ${movil
     ? `<div style="position:absolute;left:250px;top:760px;width:580px;border-radius:70px;padding:16px;background:#0b1b1d;box-shadow:0 50px 90px -30px rgba(0,0,0,.6)"><img src="${img(movil)}" style="width:100%;border-radius:56px;display:block"></div>`
     : `<div style="position:absolute;left:-330px;top:700px;width:1750px">${ventana(cap, dark)}</div>`}`,
  confianza: () => `${base(1080,1920)}
   <div style="position:absolute;inset:0;display:flex;flex-direction:column;justify-content:center;align-items:center;gap:60px;padding:0 70px">
     <h2 style="font-size:88px;text-align:center">Tus datos, seguros y en regla</h2>
     <div style="display:grid;gap:26px;width:100%">
       ${[['🔒','Conexión segura HTTPS'],['🛡️','Pensado para la LOPDP'],['💾','Respaldo automático diario'],['👥','Roles, permisos y accesos']]
         .map(([e,t])=>`<div class="glass" style="border-radius:30px;padding:36px 40px;display:flex;align-items:center;gap:28px;font-size:42px;font-weight:600"><span style="font-size:60px">${e}</span>${t}</div>`).join('')}
     </div>
   </div>`,
  cta: () => `${base(1080,1920,true)}
   <div style="position:absolute;inset:0;display:flex;flex-direction:column;align-items:center;justify-content:center;text-align:center;gap:44px;padding:0 70px">
     <div class="logo" style="width:190px;height:190px"><div>${TOOTH}</div></div>
     <h1 style="font-size:100px;color:#fff">Moderniza tu clínica hoy</h1>
     <div class="pill" style="font-size:44px;background:linear-gradient(135deg,#3ddcc8,#17a394);color:#04201d;padding:26px 50px">${CONTACTO}</div>
     <p style="font-size:34px;color:#9fb7b8">Sistema Odontológico · Web y app móvil</p>
   </div>`,
};

const guion = [
  ['01-intro', (S) => S.intro()],
  ['02-problema', (S) => S.problema()],
  ['03-panel', (S) => S.pantalla('panel', 'Panel del día', 'Todo tu día, de un vistazo', 'Citas de hoy, cobros del mes y lo que necesita tu atención.', false, 'movil-panel')],
  ['04-agenda', (S) => S.pantalla('agenda', 'Agenda', 'Sin choques de horario', 'Y te sugiere los próximos huecos libres de cada profesional.')],
  ['05-odontograma', (S) => S.pantalla('odontograma', 'Odontograma digital', 'Marca, corrige y compara', 'Pincel por superficie, deshacer y versiones guardadas.')],
  ['06-historia', (S) => S.pantalla('historia', 'Historia clínica', 'Segura y versionada', 'Recetas, consentimientos y evoluciones. Nada se borra.')],
  ['07-oportunidades', (S) => S.pantalla('oportunidades', 'Oportunidades', 'Recupera pacientes por WhatsApp', 'Te dice a quién escribir hoy. El mensaje ya va escrito.', false, 'movil-oportunidades')],
  ['08-finanzas', (S) => S.pantalla('finanzas', 'Finanzas', 'Caja, cobros y créditos', 'Ingresos, egresos, utilidad y tratamientos en cuotas.')],
  ['09-dispositivos', (S) => (S.dispositivos ? S.dispositivos() : S.pantalla('panel-oscuro', 'Donde estés', 'Computadora y celular', 'Modo claro y oscuro. Y app móvil para el sillón.', true, 'movil-panel'))],
  ['10-confianza', (S) => S.confianza()],
  ['11-cta', (S) => S.cta()],
];

const browser = await chromium.launch({ executablePath: process.env.CHROME });
for (const [formato, S, w, h] of [['h', H, 1920, 1080], ['v', V, 1080, 1920]]) {
  fs.mkdirSync(`escenas/${formato}`, { recursive: true });
  const page = await browser.newPage({ viewport: { width: w, height: h }, deviceScaleFactor: 2 });
  for (const [nombre, f] of guion) {
    await page.setContent(f(S), { waitUntil: 'networkidle' });
    await page.waitForTimeout(400);
    await page.screenshot({ path: `escenas/${formato}/${nombre}.png` });
  }
  await page.close();
  console.log('escenas', formato);
}
await browser.close();
