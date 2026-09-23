# Walkthrough video source

The 80-second walkthrough (`../docs/margin_recovery_case_80s.mp4`) is generated from code.

- `animation_src.html`: every frame is drawn as SVG by `render(t)`, a pure function of time. The case numbers come from `data/case_results.json`, so the video and the page always agree.
- `build.py`: embeds the case data and writes `animation.html`. Open that file in a browser to watch the animation loop live.
- `render.js`: renders 2,400 frames (80 s at 30 fps) with Playwright and pipes them to ffmpeg (H.264, 1920x1080).

```bash
python build.py
node render.js margin_recovery_case_80s.mp4
```

Northfold Packaging is a fictional company and every number is synthetic.
