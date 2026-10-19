# @@TITLE@@

Supplementary materials for ProG-RRT* and ProG-RRT*-Lazy: robot demonstrations, planned paths, recorded localization trajectories, and traceable planning measurements in two physical environments.

**Yuan Huang · Rongwei Chen**

- [Project page and videos](https://fishsafe1896.github.io/ProG-RRT/): 12 main demonstrations and scene-specific comparisons.
- [Original video files](https://github.com/FishSafe1896/ProG-RRT/tree/original-videos): 12 main recordings and two additional short edits.
- [Planning measurements](data/planning_comparison.csv): full-precision values for all 12 runs.
- [Data definitions and reproduction](DATA_GUIDE.md).

## Method

The Progressive Guidance Network (ProGNet) predicts guidance probabilities and five start-to-goal stages from free-space point clouds. ProG-RRT* adapts stage sampling to tree progress before the first solution, then combines cached guidance with informed sampling. ProG-RRT*-Lazy adds stage anchors and deferred graph-edge validation. Both variants use one ProGNet forward pass per planning query; geometric collision checking determines path feasibility.

Method names follow the manuscript: RRT*, N-RRT*, NIRRT*, IPN-RRT*, ProG-RRT*, and ProG-RRT*-Lazy.

## Planning results for the robot demonstrations

Lower is better for all three metrics. Tables round to four decimal places; the CSV preserves source precision. Each method has one deployment planning record per scene.

### Scene 1

@@TABLE1@@

![Scene 1: planned paths and recorded localization](docs/images/scene1-trajectories.png)

[Watch all six methods in Scene 1](https://fishsafe1896.github.io/ProG-RRT/#scene1)

### Scene 2

@@TABLE2@@

![Scene 2: planned paths and recorded localization](docs/images/scene2-trajectories.png)

[Watch all six methods in Scene 2](https://fishsafe1896.github.io/ProG-RRT/#scene2)

## Measurement definitions

`planned_length_m` is the exported planned polyline length in metres. `planning_time_s` is offline planning-call time in seconds, excluding model loading, A* reference computation, plotting, and transfer. `iterations` is the actual planning iteration count. Planning stops at the internal threshold of 1.03 times the grid-A* reference cost or the 10,000-iteration limit.

Models and planning run on a Windows host; the robot follows exported paths with a shared tracking controller. Planning time, navigation time, and edited-video duration are distinct. The archive contains 12 planning records and 11 robot trajectory logs. The Scene 1 NIRRT* trajectory log is missing; this is not counted as an algorithm failure. These individual deployments do not constitute a repeated-trial statistical comparison.

## Repository contents

```text
docs/                       Project page, figures, and playback videos
data/planning_comparison.csv Three planning metrics and source method keys
data/run_records.json       Extended records and trajectory-log availability
data/evidence/              Path CSVs, localization CSVs, and planning metadata
data/maps/                  Occupancy maps and portable map configurations
data/video_manifest.json    Video correspondence, durations, and SHA-256 hashes
scripts/                    Verification and page-generation scripts
```

Original videos are stored on the separate `original-videos` branch. Playback copies preserve the supplied duration, changing only resolution, frame rate, and encoding. Source experiment files remain unchanged. This repository distributes supplementary evidence; algorithm source and model weights are outside this release.

For a lightweight clone that excludes the original-video branch:

```bash
git clone --single-branch --branch main --depth 1 https://github.com/FishSafe1896/ProG-RRT.git
```
