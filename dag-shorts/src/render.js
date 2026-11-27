// Kullanım: node src/render.js stills t1,t2,...   |  node src/render.js video <başlangıçKare> <bitişKare> <çıktı.mp4>
const { chromium } = require('playwright');
const { spawn } = require('child_process');
const http = require('http'), fs = require('fs'), path = require('path');
const ROOT = path.resolve(__dirname, '..');
const TYPES = { '.html': 'text/html', '.js': 'text/javascript', '.json': 'application/json', '.otf': 'font/otf' };
const [mode, a, b, out] = process.argv.slice(2);
(async () => {
  const srv = http.createServer((q, r) => { const f = path.join(ROOT, decodeURIComponent(q.url.split('?')[0]));
    fs.readFile(f, (e, d) => { if (e) { r.writeHead(404); return r.end(); } r.writeHead(200, { 'Content-Type': TYPES[path.extname(f)] || 'application/octet-stream' }); r.end(d); }); });
  await new Promise(r => srv.listen(0, r));
  const browser = await chromium.launch({ args: ['--use-gl=angle', '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--ignore-gpu-blocklist'] });
  const page = await browser.newPage({ viewport: { width: 1080, height: 1920 }, deviceScaleFactor: 1 });
  page.on('console', m => console.log('[page]', m.text())); page.on('pageerror', e => console.log('[err]', e.message));
  await page.goto(`http://localhost:${srv.address().port}/src/render.html?${process.env.Q || ''}`);
  await page.waitForFunction('window.READY === true', null, { timeout: 120000 });
  const fps = await page.evaluate('TL.fps'), total = await page.evaluate('TL.total');
  if (mode === 'stills') {
    fs.mkdirSync(path.join(ROOT, 'build/stills'), { recursive: true });
    for (const t of a.split(',').map(Number)) { await page.evaluate(t => renderAt(t), t); await page.screenshot({ path: path.join(ROOT, `build/stills/t${t.toFixed(2)}.jpg`), type: 'jpeg', quality: 85 }); }
  } else {
    const f0 = +a, f1 = Math.min(+b, Math.ceil(total * fps));
    const ff = spawn('ffmpeg', ['-y', '-v', 'error', '-f', 'image2pipe', '-framerate', String(fps), '-c:v', 'mjpeg', '-i', '-', '-c:v', 'libx264', '-preset', 'medium', '-crf', '17', '-pix_fmt', 'yuv420p', out], { stdio: ['pipe', 'inherit', 'inherit'] });
    const t0 = Date.now();
    for (let f = f0; f < f1; f++) {
      await page.evaluate(t => renderAt(t), f / fps);
      const buf = await page.screenshot({ type: 'jpeg', quality: 93 });
      if (!ff.stdin.write(buf)) await new Promise(r => ff.stdin.once('drain', r));
      if ((f - f0) % 60 === 0) console.log(`${out}: ${f - f0}/${f1 - f0}  ${((Date.now() - t0) / Math.max(1, f - f0)).toFixed(0)} ms/kare`);
    }
    ff.stdin.end(); await new Promise(r => ff.on('close', r));
  }
  await browser.close(); srv.close();
})();
