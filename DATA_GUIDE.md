# Data definitions and reproduction

## Scope

The supplement contains two physical environments and six planners, with one supplied deployment planning record per scene–method pair: 12 planning records, 12 main video clips, two additional short edits, and 11 available robot localization logs.

Display names follow the manuscript:

| Source method key | Manuscript name |
| --- | --- |
| `rrt_star` | RRT* |
| `need_n_rrt_star` | N-RRT* |
| `nirrt_pointnet2_bfs` | NIRRT* |
| `ipn_rrt_star` | IPN-RRT* |
| `ours_absolute_lff_5stage` | ProG-RRT* |
| `prog_rrt_lazy` | ProG-RRT*-Lazy |

NIRRT* uses PointNet++ with the original Neural Connect breadth-first search. N-RRT* is the project's NEED-driven reproduction. Source method keys remain in the data for traceability; display-name changes do not alter measurements.

## Main planning measurements

`data/planning_comparison.csv` contains all 12 records. Web and README tables round to four decimal places; the CSV preserves source precision.

| Field | Definition | Source planning field |
| --- | --- | --- |
| `planned_length_m` | Length of the exported planned polyline, in metres | `path_length_m` |
| `planning_time_s` | Offline planning-call time, in seconds | `planning_time_sec` |
| `iterations` | Actual planning iterations | `sample_calls` |

Each value is checked against both the archived summary and its per-run planning metadata. Iterations are not tree vertices: unsuccessful extensions also consume sampling iterations. ProG-RRT*-Lazy can insert validated anchor vertices during initialization, outside the ordinary iteration loop; a small iteration count does not mean equally little geometric work.

The timer uses `perf_counter` around the planning call. It excludes model loading, A* reference computation, plotting, output writing, and path transfer. These are host-side offline timings, distinct from robot-side inference, navigation time, and video duration.

Planning stops at the internal threshold of 1.03 times the inflated-grid A* reference length or the 10,000-iteration limit. Exported metric paths may include endpoint processing, so their length need not equal the internal pixel cost times map resolution. The A* value is a reference for the specified grid and inflation, not the continuous-space global optimum.

## Maps and execution

- Occupancy maps: 384 × 384 pixels, 0.05 m/cell, origin `[-10, -10, 0]`.
- Planning step: 0.10 m; point-cloud size: 2,048; oversampling factor: 64.
- Nominal robot radius: 0.09 m; safety margin: 0.02 m. The discrete implementation rounds up to a three-cell inflation disk and treats unknown cells as occupied.
- Planning and neural inference run on a Windows host. The robot receives exported paths and follows them through the same tracking pipeline for all methods.
- Archived commands specify maximum linear/angular speeds of 0.13 m/s and 0.50 rad/s, a 0.30 m lookahead, and a 0.20 m arrival tolerance. These are command settings, not a complete runtime parameter dump.

`data/run_records.json` retains the source random configurations, planning-success flags, model calls, robot-log availability, and recorded tracking measurements. Runs are individual demonstrations, not paired repeated-trial comparisons. No pooled two-scene superiority statistic is reported.

## Videos

The data provider confirmed the same source numbering for both scenes:

| Source slot | Method |
| --- | --- |
| 1 | RRT* |
| 2 | NIRRT* |
| 3 | IPN-RRT* |
| 4 | ProG-RRT* |
| 5 | ProG-RRT*-Lazy |
| 6 | N-RRT* |

The longest supplied file in each directory is the main clip. Scene 1 also has shorter versions for ProG-RRT*-Lazy and N-RRT*; these remain separate supplementary edits. Videos are the provided edited materials, not evidence that playback duration equals complete navigation time.

Web copies use 1,280-pixel width, 30 fps, and H.264 encoding without further temporal cropping or speed changes. `data/video_manifest.json` records original and playback byte counts, durations, SHA-256 hashes, and original download links. The `original-videos` branch stores byte-identical copies of the supplied videos with descriptive filenames; keeping these on a separate branch allows a lightweight single-branch download of the main supplement.

## Log availability and interpretation

Scene 1 lacks the NIRRT* localization trajectory and corresponding robot metrics. Its planning record and video remain available. The trajectory panel therefore shows only its planned path. A missing log is not counted as a planning failure.

Localization trajectories are estimates in the robot's map frame, not external ground truth. The 11 recovered logs record estimated positions entering the 0.20 m goal tolerance. They do not establish 12/12 verified physical arrivals or a collision-free execution rate.

The original audit found differences of one or two samples between some robot JSON summaries and CSV trajectories. Arrival times, path lengths, goal errors, and maximum cross-track errors recompute within the archived tolerance; small mean cross-track differences remain. Localization CSVs are retained unchanged. The three main planning measurements do not depend on these tracking summaries.

Historical planning metadata did not store a hash of the map content. Maps are linked by scene archive; checksums generated for this release do not retroactively establish a historical runtime map binding.

## Reproduce the page and verify files

Use Python 3.12:

```bash
python -m pip install -r requirements.txt
python scripts/verify_data.py
python scripts/build_showcase.py
python -m http.server 8000 --directory docs
```

Open `http://localhost:8000` for a local preview.

Publication transformations: planned-path and localization CSVs are copied unchanged; map PGM files are copied unchanged; YAML image paths are made relative; public planning metadata omits machine-specific paths and weight-path lists; legacy display names are mapped to manuscript names. Measurements remain unchanged. Environment-operation logs, network addresses, training assets, and the full algorithm code are outside this supplementary release.

Please cite the associated manuscript when referencing these materials. This supplementary release does not relicense third-party algorithms, models, or datasets.
