# Cognitive CanSat Web Presentation Suite

This directory contains the complete browser-based user interface suite for the Cognitive CanSat mission control system.

## Page Directory

* **`index.html`**: CanSat Mission Overview, narrative problem statement, and interactive Three.js 3D PLA airframe component inspector.
* **`dashboard.html`**: Real-time mission control aerospace telemetry HUD, 3-column synchronized Chart.js graphs, 3D attitude digital twin, and Web Serial API hardware bridge.
* **`tinyml.html`**: TinyML edge vision deep dive, INT8 quantization benchmarks, and interactive client-side inference simulator.
* **`models.html`**: Comprehensive 6-model machine learning architecture breakdown with plain-English analogies and engineering benchmarks.
* **`analysis.html`**: Post-flight telemetry analytics, 10-scenario trajectory visualizer, 4-sensor ablation suite, live sensor dropout simulator, and 1-click batch ZIP report downloader.
* **`results.html`**: Research data viewer and scenario comparison charts.

## Directory Structure

```
frontend/
├── index.html
├── dashboard.html
├── tinyml.html
├── models.html
├── analysis.html
├── results.html
├── css/
│   └── resend-theme.css        # Clean Obsidian dark theme (Inter, Newsreader, JetBrains Mono)
└── js/
    ├── cansat-3d.js            # Three.js 3D PLA CanSat model & interactive component inspector
    ├── mission-slider.js       # Flight timeline scrubber & nadir camera simulator
    ├── results-charts.js       # Chart.js research results data visualizer
    └── tinyml-demo.js          # Interactive TinyLandingNet inference simulator
```
