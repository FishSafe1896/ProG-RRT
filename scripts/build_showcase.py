"""Rebuild the English supplement from its published, audited measurements."""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
TITLE = "Progressive Point-Cloud Guidance with Lazy Validation for Sampling-Based Path Planning"
REPO = "https://github.com/FishSafe1896/ProG-RRT"
METHODS = ["RRT*", "N-RRT*", "NIRRT*", "IPN-RRT*", "ProG-RRT*", "ProG-RRT*-Lazy"]
SLUGS = ["rrt-star", "n-rrt-star", "nirrt-star", "ipn-rrt-star", "prog-rrt-star", "prog-rrt-star-lazy"]
COLORS = ["#777F86", "#89929B", "#54839B", "#678A79", "#BF827F", "#994F50"]
FIELDS = [("planned_length_m", "Planned path length (m)", 4),
          ("planning_time_s", "Planning time (s)", 4), ("iterations", "Planning iterations", 0)]


def save_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def xy(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return np.array([[float(r["x"]), float(r["y"])] for r in csv.DictReader(stream)])


def export(fig, name, audit_dir):
    if audit_dir:
        sys.path.insert(0, str(audit_dir))
        from audit_panel_alignment import require_matplotlib_panel_alignment
        require_matplotlib_panel_alignment(fig, json_out=str(ROOT / ".local" / f"{name}.alignment.json"),
                                          strict=True, tolerance_pt=1.5)
    path = ROOT / "docs/images" / name
    fig.savefig(path.with_suffix(".png"), dpi=300)
    fig.savefig(path.with_suffix(".pdf"))
    fig.savefig(path.with_suffix(".svg"))
    plt.close(fig)


def plot_scene(scene, rows, audit_dir):
    # All panels share the same spatial extent and preserve the map aspect ratio.
    fig, axes = plt.subplots(2, 3, figsize=(10.8, 6.6))
    fig.subplots_adjust(left=.07, right=.985, bottom=.09, top=.91, wspace=.36, hspace=.30)
    image = np.asarray(Image.open(ROOT / "data/maps" / f"scene{scene}.pgm"))
    paths = [xy(ROOT / r["evidence_directory"] / "planned_path.csv") for r in rows]
    low, high = np.concatenate(paths).min(axis=0) - .45, np.concatenate(paths).max(axis=0) + .45
    for ax, row, planned in zip(axes.flat, rows, paths):
        ax.imshow(image, cmap="gray", vmin=0, vmax=255, origin="upper", interpolation="nearest", extent=[-10, 9.2, -10, 9.2])
        trajectory = ROOT / row["evidence_directory"] / "recorded_trajectory.csv"
        if trajectory.is_file():
            recorded = xy(trajectory)
            ax.plot(recorded[:, 0], recorded[:, 1], lw=1.3, color="#C58C55", label="Recorded localization", zorder=3)
        else:
            ax.text(.03, .03, "Robot trajectory log unavailable", transform=ax.transAxes, color="#994F50", fontsize=8)
        ax.plot(planned[:, 0], planned[:, 1], color="#4E8CB8", lw=1.3, label="Planned path", zorder=4)
        ax.scatter(*planned[0], s=18, color="#548A72", label="Start", zorder=5)
        ax.scatter(*planned[-1], s=50, marker="*", color="#A85959", label="Goal", zorder=5)
        ax.set_xlim(low[0], high[0]); ax.set_ylim(low[1], high[1]); ax.set_aspect("equal")
        ax.set_title(row["method"], fontsize=10, pad=7)
        ax.set_xlabel("Map x (m)"); ax.set_ylabel("Map y (m)")
    handles, labels = axes.flat[0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(.5, .998), ncol=4, frameon=False)
    export(fig, f"scene{scene}-trajectories", audit_dir)
    # Each bar is one deployment record, not an aggregate over repeated trials.
    for field, label, digits in FIELDS:
        values = [float(r[field]) for r in rows]
        fig, ax = plt.subplots(figsize=(7.2, 3.55))
        fig.subplots_adjust(left=.25, right=.86, top=.94, bottom=.18)
        y = np.arange(len(rows)); maximum = max(values)
        ax.barh(y, values, color=COLORS, height=.56, linewidth=0)
        ax.set_yticks(y, [r["method"] for r in rows]); ax.invert_yaxis()
        ax.set_xlim(0, maximum * 1.22)
        for index, value in zip(y, values):
            ax.text(value + maximum * .025, index, f"{value:.{digits}f}", va="center", fontsize=9)
        ax.set_xlabel(label); ax.spines[["top", "right", "left"]].set_visible(False)
        ax.tick_params(axis="y", length=0)
        export(fig, f"scene{scene}-{field}", audit_dir)


def table(rows, markdown=False):
    if markdown:
        lines = ["| Method | Planned length (m) ↓ | Planning time (s) ↓ | Iterations ↓ |", "| --- | ---: | ---: | ---: |"]
        lines += [f'| {r["method"]} | {float(r["planned_length_m"]):.4f} | {float(r["planning_time_s"]):.4f} | {r["iterations"]} |' for r in rows]
        return "\n".join(lines)
    best = {field: min(float(r[field]) for r in rows) for field, _, _ in FIELDS}
    parts = ['<div class="table-scroll"><table><thead><tr><th scope="col">Method</th><th scope="col">Path length (m) ↓</th><th scope="col">Planning time (s) ↓</th><th scope="col">Iterations ↓</th></tr></thead><tbody>']
    for r in rows:
        parts.append(f'<tr><th scope="row">{html.escape(r["method"])}</th>')
        for field, _, digits in FIELDS:
            value = float(r[field]); text = f"{value:.{digits}f}"
            parts.append(f'<td>{"<strong>" + text + "</strong>" if value == best[field] else text}</td>')
        parts.append("</tr>")
    return "".join(parts) + "</tbody></table></div>"


def video_cards(scene, rows, videos):
    cards = []
    for row in rows:
        clip = next(v for v in videos if v["scene_number"] == scene and v["method"] == row["method"] and v["primary"])
        cards.append(f'''<article class="video-card"><h4>{html.escape(row['method'])}</h4>
<video controls playsinline preload="none" poster="{clip['poster_file']}"><source src="{clip['preview_file']}" type="video/mp4">Your browser does not support this video. Use the download links below.</video>
<p class="video-metrics">{float(row['planned_length_m']):.4f} m · {float(row['planning_time_s']):.4f} s · {row['iterations']} iterations</p>
<div class="card-links"><a href="{clip['preview_file']}" download>Download video</a>{f'<a href="{clip["original_url"]}">Original file</a>' if clip.get('original_url') else ''}</div></article>''')
    return "".join(cards)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--audit-dir", type=Path, help="Optional local figure-geometry audit tools")
    args = parser.parse_args()
    (ROOT / ".local").mkdir(exist_ok=True)
    rows = json.loads((ROOT / "data/run_records.json").read_text(encoding="utf-8"))
    for row in rows:
        row["scene"] = "Scene " + row["scene_id"][-1]
    save_json(ROOT / "data/run_records.json", rows)
    with (ROOT / "data/planning_comparison.csv").open("w", encoding="utf-8-sig", newline="") as stream:
        keys = ["scene", "method", "method_key", "planned_length_m", "planning_time_s", "iterations"]
        writer = csv.DictWriter(stream, fieldnames=keys); writer.writeheader()
        writer.writerows({k: r[k] for k in keys} for r in rows)
    videos = json.loads((ROOT / "data/video_manifest.json").read_text(encoding="utf-8"))
    for video in videos:
        slug = SLUGS[METHODS.index(video["method"])]
        video["release_asset"] = f'scene{video["scene_number"]}-{slug}' + ("" if video["primary"] else "-additional-edit1") + "-original.mp4"
        available = video["scene_number"] == 1 and video["primary"] and video["method"] in ("NIRRT*", "IPN-RRT*")
        video["source_file_published"] = available
        if available:
            video["original_url"] = f'{REPO}/releases/download/robot-validation-v1/{video["release_asset"]}'
        else:
            video.pop("original_url", None)
        if video["primary"]:
            video["transformation"] = "1280-pixel width, 30 fps, H.264; no temporal crop or speed change"
    save_json(ROOT / "data/video_manifest.json", videos)
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Arial", "DejaVu Sans"],
                         "font.size": 9, "pdf.fonttype": 42, "svg.fonttype": "none",
                         "axes.spines.top": False, "axes.spines.right": False})
    page = (ROOT / "scripts/page_template.html").read_text(encoding="utf-8").replace("@@TITLE@@", TITLE)
    readme = (ROOT / "scripts/readme_template.md").read_text(encoding="utf-8").replace("@@TITLE@@", TITLE)
    for scene in (1, 2):
        group = [r for r in rows if r["scene"] == f"Scene {scene}"]
        assert len(group) == 6 and [r["method"] for r in group] == METHODS
        plot_scene(scene, group, args.audit_dir)
        page = page.replace(f"@@TABLE{scene}@@", table(group)).replace(f"@@VIDEOS{scene}@@", video_cards(scene, group, videos))
        readme = readme.replace(f"@@TABLE{scene}@@", table(group, markdown=True))
    (ROOT / "docs/index.html").write_text(page, encoding="utf-8")
    (ROOT / "README.md").write_text(readme, encoding="utf-8")
    files = []
    for folder in (ROOT / "data", ROOT / "docs"):
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                files.append(dict(file=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size))
    save_json(ROOT / "checksums.json", files)
    print("Rebuilt English supplement: 12 planning records, 11 trajectory logs, 12 main clips, and 2 additional edits.")


if __name__ == "__main__":
    main()
