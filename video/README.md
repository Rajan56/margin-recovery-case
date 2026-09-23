# Walkthrough video source

The narrated walkthrough (`../docs/margin_recovery_case_narrated.mp4`, about 100 s) is generated from code.

- `animation_src.html`: every frame is drawn as SVG by `render(t)`, a pure function of time. The case numbers come from `data/case_results.json`, so the video and the page always agree. Time below zero is the opening hook.
- `build.py`: embeds the case data and writes `animation.html`. Open that file in a browser to watch the animation loop live.
- `voiceover.py`: one narration line per scene, spoken by an offline neural text-to-speech model (Kokoro, voice `bm_george`). Each scene is stretched so the picture waits for its line. Writes `voiceover.wav`, `timemap.json` (video time to animation time) and `voiceover_timing.json`.
- `render.js`: renders the frames with Playwright, follows the time map, and encodes H.264 video with AAC voice via ffmpeg.

```bash
pip install kokoro-onnx soundfile        # model files: github.com/thewh1teagle/kokoro-onnx releases
python build.py
python voiceover.py <kokoro_model_dir>
node render.js margin_recovery_case_narrated.mp4 timemap.json voiceover.wav
node render.js silent_80s.mp4            # silent cut, original timing
```

Northfold Packaging is a fictional company and every number is synthetic.
