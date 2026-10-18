// GitHub Pages does not expose custom headers. A scoped worker supplies COOP/COEP.
if ('serviceWorker' in navigator && !crossOriginIsolated) {
  navigator.serviceWorker.register('./isolation-sw.js').then(()=>{
    navigator.serviceWorker.addEventListener('controllerchange',()=>location.reload());
  }).catch(error=>console.warn('Isolation worker unavailable; runtime may use single-thread fallback',error));
}
