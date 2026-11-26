// Futbol Kariyer Yolu: çevrimdışı çalışma. Sürüm 20261126123402
const CACHE='kariyer-yolu-20261126123402';
const FILES=['./','index.html','manifest.webmanifest','icon-192.png','icon-512.png','apple-touch-icon.png'];
self.addEventListener('install',e=>{e.waitUntil(caches.open(CACHE).then(c=>c.addAll(FILES.map(f=>new Request(f,{cache:'reload'})))).then(()=>self.skipWaiting()))});
self.addEventListener('activate',e=>{e.waitUntil(caches.keys().then(ks=>Promise.all(ks.filter(k=>k!==CACHE).map(k=>caches.delete(k)))).then(()=>self.clients.claim()))});
// Önce ağ (tarayıcı önbelleğini atlayarak güncel sürüm), ağ yoksa uygulama önbelleği
self.addEventListener('fetch',e=>{
  const req=e.request;if(req.method!=='GET')return;
  const url=new URL(req.url);if(url.origin!==location.origin)return;
  if(url.pathname.endsWith('version.json'))return;
  e.respondWith(fetch(req,{cache:'no-store'}).then(r=>{if(r.ok){const c=r.clone();caches.open(CACHE).then(x=>x.put(req,c))}return r})
    .catch(()=>caches.match(req,{ignoreSearch:true}).then(m=>m||caches.match('index.html'))));
});
