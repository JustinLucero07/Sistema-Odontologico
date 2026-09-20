export const environment = {
  production: false,
  // Relative, like production: `ng serve` proxies /api to the backend
  // (see proxy.conf.json), exactly as nginx does in a real deployment. That
  // makes every API call same-origin, so there is no CORS preflight to fail
  // and the refresh cookie is a first-party cookie in every browser.
  apiUrl: '/api/v1',
};
