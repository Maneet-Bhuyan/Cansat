# TinyML Flight Test Video Library

This directory contains verified, high-resolution aerial and drone flight test videos for benchmarking and validating the onboard TinyLandingNet edge computer vision model and spatial hazard avoidance algorithms.

---

## Directory Structure

### `01_farmland_and_pasture/`
* **File**: `aerial_hemp_field_descent.webm` (29.3 MB)
* **Terrain Category**: Agricultural Farmland, Pasture & Dirt Access Trails
* **Primary Classes**: `SAFE_LZ`, `AGRICULTURE`
* **Characteristics**: Overhead nadir descent perspective showcasing open green agricultural rows, high vegetative chroma (VARI > +0.15), and dirt perimeter access roads.
* **Evaluation Purpose**: Validates positive identification of safe, low-risk drop zones (`SAFE_LZ`) and tests stability of confidence scores over uniform vegetative canopies.

---

### `02_urban_roads_and_buildings/`
* **File**: `aerial_village_roads_and_rooftops.webm` (22.4 MB)
* **Terrain Category**: Urban Settlement, Industrial Rooftops, Vehicles & Asphalt Highways
* **Primary Classes**: `CRITICAL_HAZARD`, `HIGHWAY`, `BUILDINGS`
* **Characteristics**: Overhead flight passing directly above a church spire, dark commercial rooftops, vehicles in a parking area, and paved roads transitioning into open ground.
* **Evaluation Purpose**: Tests edge density triggers, structural shadow detection, and real-time generation of evasion advisory vectors (`EVADE theta`) steering away from hazardous man-made obstacles toward open periphery sectors.

---

### `03_water_hazards_and_canopy/`
* **File 1**: `aerial_beaverhead_river_canopy.webm` (5.9 MB)
  * **Terrain Category**: River Meanders, Water Surface & Dense Shrub/Tree Canopy
  * **Primary Classes**: `WATER_HAZARD`, `OBSTACLE_CANOPY`
  * **Characteristics**: Overhead drone flight tracking a meandering river flanked by dense willow/tree thickets and surrounding foothills.
  * **Evaluation Purpose**: Benchmarks discrimination between safe low-lying grass and hazardous tall obstacle canopies (`OBSTACLE_CANOPY`), while testing specular water reflection hazard triggers.

* **File 2**: `aerial_rocky_coastline_waves.mp4` (1.3 MB)
  * **Terrain Category**: Marine Water Surface, Surf Foam & Rocky Coastline
  * **Primary Classes**: `WATER_HAZARD`, `CRITICAL_HAZARD`
  * **Characteristics**: True nadir (straight-down) perspective over coastal rocks and breaking ocean surf.
  * **Evaluation Purpose**: Tests water immersion hazard classification and rapid avoidance vector calculation when approaching dangerous shorelines.

---

## How to Test in the Web Simulator

1. Start the mission control server:
   ```bash
   .\.venv\Scripts\python.exe backend/app.py
   ```
2. Navigate to `http://localhost:8000/tinyml.html` in your browser.
3. Scroll to **Section 4: Video Replay & FPS Simulator**.
4. Select any preset video from the **Preset Flight Video** dropdown, or use the file picker to select a specific `.webm` / `.mp4` file directly from this directory.
5. Select the simulation frame rate (5 FPS for airborne CanSat rate, 10 FPS for high-rate downlink, or 30 FPS for native rate).
6. Click **PLAY** to observe real-time 3x3 sector hazard classification, safe zone highlighting, and evasion vector overlays.
