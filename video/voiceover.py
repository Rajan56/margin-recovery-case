"""
voiceover.py
------------
Generates a scene-by-scene voiceover for the 80-second walkthrough with an
offline neural text-to-speech model (Kokoro, voice "bm_george"), fits each line
into its scene window and mixes one narration track (voiceover.wav).

Needs: pip install kokoro-onnx soundfile ; the model files kokoro-v1.0.onnx and
voices-v1.0.bin (github.com/thewh1teagle/kokoro-onnx releases) ; ffmpeg.
Run:   python voiceover.py <model_dir>
"""
import json
import subprocess
import sys
from pathlib import Path

import numpy as np
import soundfile as sf
from kokoro_onnx import Kokoro

MODEL = Path(sys.argv[1] if len(sys.argv) > 1 else ".")
OUT = Path(__file__).resolve().parent
VOICE, LANG, SR = "bm_george", "en-gb", 24000
DUR = 80.0

# (start s, latest end s, spoken line) -- windows follow the scenes in animation_src.html
HOOK = 8.0   # opening hook runs at animation time -8 to 0
LINES = [
    (-7.6, -0.5, "Imagine your sales are growing, but your profit is quietly shrinking. Often, it only shows up months later, in the monthly report."),
    (0.5, 3.1, "Here is how I would find out why, on a fictional company."),
    (3.4, 8.1, "Sales grew two percent, yet EBITDA fell by seventeen point six million. Where did the margin go?"),
    (8.5, 13.1, "First, I bring sales, cost, energy, logistics and currency data into one model."),
    (13.3, 18.2, "Then I check the numbers three ways, before trusting any chart."),
    (18.6, 27.0, "Next, a driver-based bridge, built customer by customer, in constant currency."),
    (27.2, 31.1, "Fifteen million is the market: fibre, energy, and a weaker krona."),
    (31.3, 35.3, "But price we can control. Fixed contracts lost nine million, while indexed ones gained."),
    (35.6, 41.1, "Then I rank every customer by profit, after the real cost of serving them."),
    (41.3, 47.2, "Twenty-nine accounts lose money. Small accounts cost seven times more to serve, per tonne."),
    (47.6, 53.1, "For energy, each plant is compared, week by week, with its own seasonal baseline."),
    (53.3, 58.2, "A weekly rule catches the drift in six weeks. The monthly report showed only four percent."),
    (58.6, 63.1, "An AI agent drafts the monthly commentary, from verified facts only."),
    (63.3, 68.2, "Every number is checked against the data, and a controller signs off."),
    (68.6, 75.3, "Five initiatives, worth about eight million euros a year, each with a KPI and an owner."),
    (75.8, 79.8, "The full case, with the code and Power B I, is at the link. Thanks for watching."),
]

k = Kokoro(str(MODEL / "kokoro-v1.0.onnx"), str(MODEL / "voices-v1.0.bin"))


def speak(text, speed):
    ph = k.tokenizer.phonemize(text, LANG)
    ph = ph.replace("ˈɛbɪtdə", "iːbˈɪtdɑː")          # EBITDA as "ee-BIT-dah"
    audio, sr = k.create(ph, voice=VOICE, speed=speed, lang=LANG, is_phonemes=True)
    assert sr == SR
    return audio


SPEED, PAD = 1.1, 0.3
clips = [speak(text, SPEED) for _, _, text in LINES]

# Time map: gaps between lines keep their length; each line's window stretches
# to fit its clip. Pairs (video time, animation time) are written for render.js.
tmap = [(0.0, -HOOK)]
T, prev_end = 0.0, -HOOK
report = []
for (start, end, text), clip in zip(LINES, clips):
    T += start - prev_end                      # gap before this line
    tmap.append((round(T, 3), start))
    seg = max(end - start, len(clip) / SR + PAD)
    report.append({"video_start": round(T, 2), "voice_s": round(len(clip) / SR, 2),
                   "segment_s": round(seg, 2), "stretch": round(seg / (end - start), 2), "text": text})
    T += seg
    tmap.append((round(T, 3), end))
    prev_end = end
T += DUR - prev_end
tmap.append((round(T, 3), DUR))
total = T

track = np.zeros(int(total * SR) + SR, dtype=np.float32)
for r, clip in zip(report, clips):
    i0 = int(r["video_start"] * SR)
    track[i0 : i0 + len(clip)] += clip
track = track[: int(total * SR)]
track = track / float(np.abs(track).max()) * 0.89
sf.write(OUT / "voiceover.wav", track, SR)
(OUT / "timemap.json").write_text(json.dumps({"total": round(total, 3), "points": tmap}, indent=0))
(OUT / "voiceover_timing.json").write_text(json.dumps(report, indent=1))
print("total video length", round(total, 1), "s")
for r in report:
    print(f"{r['video_start']:5.1f}s  voice {r['voice_s']:4.1f}s  stretch x{r['stretch']:.2f}  {r['text'][:55]}")
