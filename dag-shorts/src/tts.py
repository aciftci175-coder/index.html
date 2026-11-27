import json, subprocess, sys, os
from gtts import gTTS
D = json.load(open(sys.argv[1])); out = sys.argv[2]; os.makedirs(out, exist_ok=True)
segs = [("intro", D["intro"])] + [(f"m{m['rank']:02d}", m) for m in D["mountains"]] + [("outro", D["outro"])]
meta = []
for key, s in segs:
    raw = f"{out}/{key}_raw.mp3"; wav = f"{out}/{key}.wav"
    if not os.path.exists(raw): gTTS(s["tts"], lang="tr").save(raw)
    # biraz hızlandır, sessizlikleri kırp, normalize et
    subprocess.run(["ffmpeg","-y","-v","error","-i",raw,"-af",
      "silenceremove=start_periods=1:start_threshold=-45dB,areverse,silenceremove=start_periods=1:start_threshold=-45dB,areverse,atempo=1.25,highpass=f=80,acompressor=threshold=-18dB:ratio=3,loudnorm=I=-16",
      "-ar","44100","-ac","1",wav], check=True)
    d = float(subprocess.check_output(["ffprobe","-v","error","-show_entries","format=duration","-of","csv=p=0",wav]))
    meta.append({"key":key,"dur":round(d,3),"text":s["text"]}); print(key, round(d,2))
json.dump(meta, open(f"{out}/voice.json","w"), ensure_ascii=False, indent=1)
print("toplam", round(sum(m["dur"] for m in meta),2))
