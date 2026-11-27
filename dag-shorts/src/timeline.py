"""Seslendirme sürelerinden sahne zaman çizelgesi + kelime bazlı altyazı zamanlaması üretir."""
import json, re, sys, os
E = os.environ.get
D = json.load(open(E('DATA', 'src/data.json'))); V = {v['key']: v for v in json.load(open(E('VOICE', 'build/voice') + '/voice.json'))}
LEAD, TAIL = float(E('LEAD', '0.22')), float(E('TAIL', '0.20'))
scenes, t = [], 0.0
GEO = json.load(open('build/terrain/meta.json'))

def words(text, vstart, vdur):
    toks = text.split()
    # sayılar konuşulurken çok daha uzun sürer -> ağırlık ver
    def w(tok):
        core = re.sub(r'[^\w]', '', tok)
        if re.fullmatch(r'\d[\d.]*', tok.strip('.:!,')):
            n = len(re.sub(r'\D', '', tok)); return 4 + 5 * n if n > 2 else 6
        return max(2, len(core)) + 1.5
    ws = [w(x) for x in toks]; tot = sum(ws); out, c = [], vstart
    for tok, x in zip(toks, ws):
        d = vdur * x / tot; out.append({'w': tok, 's': round(c, 3), 'e': round(c + d, 3)}); c += d
    return out

def add(kind, key, extra, data):
    global t
    v = V[key]; dur = LEAD + v['dur'] + TAIL + extra
    scenes.append({'kind': kind, 'key': key, 'start': round(t, 3), 'dur': round(dur, 3),
                   'voice': round(t + LEAD, 3), 'words': words(v['text'], t + LEAD, v['dur']), **data})
    t += dur

add("intro", "intro", float(E("INTRO_X", "0.3")), {})
for m in D['mountains']:
    add('mountain', f"m{m['rank']:02d}", 0.5 if m['rank'] == 1 else 0.0, {'m': m, 'geo': GEO.get(str(m['rank']))})
add('outro', 'outro', float(E('OUTRO_X', '2.4')), {"all": D['mountains']})
json.dump({'fps': 30, 'total': round(t, 3), 'scenes': scenes}, open(E('OUT', 'build/timeline.json'), 'w'), ensure_ascii=False, indent=1)
print('toplam süre', round(t, 2))
