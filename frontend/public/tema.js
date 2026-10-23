// El tema se aplica antes de pintar nada: sin esto, quien usa el modo oscuro
// ve un destello blanco mientras arranca la aplicación. Va en un archivo (y no
// en línea) porque la política de seguridad del sistema no permite scripts en línea.
(function () {
  var pref = 'system';
  try { pref = localStorage.getItem('odonto.theme') || 'system'; } catch (e) {}
  var dark = pref === 'dark' || (pref === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.dataset.theme = dark ? 'dark' : 'light';
})();
