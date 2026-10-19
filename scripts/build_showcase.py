"""从核验后的实车记录生成中文展示资料；源实验文件保持只读。"""
from __future__ import annotations

import argparse
import csv
import hashlib
import html
import json
import shutil
import subprocess
import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
REPO_URL = "https://github.com/FishSafe1896/ProG-RRT"
SITE_URL = "https://fishsafe1896.github.io/ProG-RRT/"
TITLE = "面向采样式路径规划的渐进点云引导与惰性验证"
METHODS = [
    ("rrt_star", "RRT*", "rrt-star", 1),
    ("need_n_rrt_star", "N-RRT*", "n-rrt-star", 6),
    ("nirrt_pointnet2_bfs", "NIRRT*", "nirrt-star", 2),
    ("ipn_rrt_star", "IPN-RRT*", "ipn-rrt-star", 3),
    ("ours_absolute_lff_5stage", "ProG-RRT*", "prog-rrt-star", 4),
    ("prog_rrt_lazy", "ProG-RRT*-Lazy", "prog-rrt-star-lazy", 5),
]
COLORS = ["#777F86", "#89929B", "#54839B", "#678A79", "#BF827F", "#994F50"]


def dump(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write_csv(path, rows, fields):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({key: row.get(key, "") for key in fields} for row in rows)


def read_xy(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return np.array([[float(row["x"]), float(row["y"])] for row in csv.DictReader(stream)])


def export_figure(fig, name, audit_dir=None):
    if audit_dir:
        sys.path.insert(0, str(audit_dir))
        from audit_panel_alignment import require_matplotlib_panel_alignment
        require_matplotlib_panel_alignment(
            fig, json_out=str(ROOT / ".local" / f"{name}.alignment.json"),
            strict=True, tolerance_pt=1.5,
        )
    fig.savefig(ROOT / "docs" / "images" / f"{name}.png", dpi=300)
    fig.savefig(ROOT / "docs" / "images" / f"{name}.pdf")
    fig.savefig(ROOT / "docs" / "images" / f"{name}.svg")
    plt.close(fig)


def draw_results(rows, audit_dir):
    """每场景只展示原始单次记录，不计算显著性或绘制误差棒。"""
    plt.rcParams.update({"font.family": "sans-serif", "font.sans-serif": ["Microsoft YaHei", "DejaVu Sans"],
                         "font.size": 9, "pdf.fonttype": 42, "svg.fonttype": "none",
                         "axes.spines.top": False, "axes.spines.right": False})
    for scene in (1, 2):
        group = [row for row in rows if row["scene"] == f"场景 {scene}"]
        # 统一轴区域宽高；地图只裁取共同路径附近区域，不修改原始地图。
        fig, axes = plt.subplots(2, 3, figsize=(10.8, 6.6))
        fig.subplots_adjust(left=.07, right=.985, bottom=.09, top=.91, wspace=.36, hspace=.30)
        map_image = np.asarray(Image.open(ROOT / "data" / "maps" / f"scene{scene}.pgm"))
        all_xy = np.concatenate([read_xy(ROOT / row["evidence_directory"] / "planned_path.csv") for row in group])
        low, high = all_xy.min(axis=0) - .45, all_xy.max(axis=0) + .45
        for ax, row in zip(axes.flat, group):
            folder = ROOT / row["evidence_directory"]
            planned = read_xy(folder / "planned_path.csv")
            ax.imshow(map_image, cmap="gray", vmin=0, vmax=255, origin="upper", interpolation="nearest",
                      extent=[-10, 9.2, -10, 9.2])
            tracking = folder / "recorded_trajectory.csv"
            if tracking.exists():
                xy = read_xy(tracking)
                ax.plot(xy[:, 0], xy[:, 1], lw=1.3, color="#C58C55", label="定位记录轨迹", zorder=3)
            else:
                ax.text(.03, .03, "实车轨迹日志缺失", transform=ax.transAxes, color="#994F50", fontsize=8)
            ax.plot(planned[:, 0], planned[:, 1], color="#4E8CB8", lw=1.3, label="规划路径", zorder=4)
            ax.scatter(*planned[0], s=18, color="#548A72", label="起点", zorder=5)
            ax.scatter(*planned[-1], s=50, marker="*", color="#A85959", label="终点", zorder=5)
            ax.set_xlim(low[0], high[0]); ax.set_ylim(low[1], high[1]); ax.set_aspect("equal")
            ax.set_title(row["method"], fontsize=10, pad=7)
            ax.set_xlabel("地图 x 坐标（米）"); ax.set_ylabel("地图 y 坐标（米）")
        # 使用共同图例，单图标题不列时间，数值集中在结果表。
        handles, labels = axes.flat[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc="upper center", bbox_to_anchor=(.5, .998), ncol=4, frameon=False)
        export_figure(fig, f"scene{scene}-trajectories", audit_dir)

        for field, label, digits in (("planned_length_m", "规划路径长度（米）", 4),
                                      ("planning_time_s", "规划时间（秒）", 4),
                                      ("iterations", "规划迭代次数", 0)):
            values = [float(row[field]) for row in group]
            fig, ax = plt.subplots(figsize=(7.2, 3.55))
            fig.subplots_adjust(left=.25, right=.86, top=.94, bottom=.18)
            y = np.arange(len(group))
            ax.barh(y, values, color=COLORS, height=.56, linewidth=0)
            ax.set_yticks(y, [row["method"] for row in group]); ax.invert_yaxis()
            maximum = max(values); ax.set_xlim(0, maximum * 1.22)
            for pos, val in zip(y, values):
                ax.text(val + maximum * .025, pos, f"{val:.{digits}f}", va="center", fontsize=9)
            ax.set_xlabel(label); ax.spines[["top", "right", "left"]].set_visible(False)
            ax.tick_params(axis="y", length=0)
            export_figure(fig, f"scene{scene}-{field}", audit_dir)


def make_table(rows, markdown=False):
    if markdown:
        lines = ["| 算法 | 规划路径长度（米）↓ | 规划时间（秒）↓ | 迭代次数↓ |",
                 "| --- | ---: | ---: | ---: |"]
        for row in rows:
            lines.append(f'| {row["method"]} | {float(row["planned_length_m"]):.4f} | {float(row["planning_time_s"]):.4f} | {row["iterations"]} |')
        return "\n".join(lines)
    best = {field: min(float(row[field]) for row in rows) for field in ("planned_length_m", "planning_time_s", "iterations")}
    parts = ['<div class="table-scroll"><table><thead><tr><th scope="col">算法</th><th scope="col">路径长度 / 米 ↓</th><th scope="col">规划时间 / 秒 ↓</th><th scope="col">迭代次数 ↓</th></tr></thead><tbody>']
    for row in rows:
        parts.append(f'<tr><th scope="row">{html.escape(row["method"])}</th>')
        for field in best:
            value = float(row[field]); text = str(int(value)) if field == "iterations" else f"{value:.4f}"
            parts.append(f'<td>{"<strong>" + text + "</strong>" if value == best[field] else text}</td>')
        parts.append("</tr>")
    return "".join(parts) + "</tbody></table></div>"


def make_pages(rows, videos):
    parts = []
    for scene in (1, 2):
        group = [row for row in rows if row["scene"] == f"场景 {scene}"]
        cards = []
        for row in group:
            clip = next(v for v in videos if v["scene_number"] == scene and v["method"] == row["method"] and v["primary"])
            name = clip["preview_file"]; poster = clip["poster_file"]
            cards.append(f'''<article class="video-card"><h4>{html.escape(row['method'])}</h4>
<video controls playsinline preload="none" poster="{poster}"><source src="{name}" type="video/mp4">浏览器无法播放，请使用下方链接下载。</video>
<p class="video-metrics">{float(row['planned_length_m']):.4f} 米 · {float(row['planning_time_s']):.4f} 秒 · {row['iterations']} 次迭代</p>
<div class="card-links"><a href="{name}" download>下载播放版</a><a href="{clip['original_url']}">下载原始视频</a></div></article>''')
        parts.append(f'''<section id="scene{scene}" class="scene"><div class="section-top"><span class="eyebrow">真实场景 {scene:02d}</span><h2>场景 {scene}</h2></div>
<p>六种算法在同一张实车场景栅格地图上生成路径，并交由相同的车辆跟踪流程执行。以下为各算法本次部署对应的规划记录。</p>
{make_table(group)}
<details><summary>查看三项指标的独立对比图</summary><div class="metrics-grid">
{''.join(f'<a href="images/scene{scene}-{field}.pdf"><img loading="lazy" src="images/scene{scene}-{field}.png" alt="场景{scene}{label}对比"></a>' for field,label in [('planned_length_m','路径长度'),('planning_time_s','规划时间'),('iterations','迭代次数')])}</div></details>
<h3>实车视频</h3><div class="video-grid">{''.join(cards)}</div>
<h3>规划与实车定位轨迹</h3><a href="images/scene{scene}-trajectories.pdf"><img class="trajectory" loading="lazy" src="images/scene{scene}-trajectories.png" alt="场景{scene}六种算法的规划路径与定位轨迹对比"></a>
<p class="caption">蓝色线为规划路径，橙色线为实车定位记录轨迹；绿色圆点为起点，红色星号为终点。定位轨迹来自机器人自身定位估计。{'场景 1 的 NIRRT* 尚缺实车轨迹日志，图中只展示规划路径，视频独立保留。' if scene == 1 else ''}</p></section>''')
    template = (ROOT / "scripts" / "page_template.html").read_text(encoding="utf-8")
    (ROOT / "docs" / "index.html").write_text(template.replace("@@TITLE@@", TITLE).replace("@@SCENES@@", "\n".join(parts)), encoding="utf-8")
    intro = f'''# {TITLE}

本仓库是 ProG-RRT* 与 ProG-RRT*-Lazy 的论文补充材料，展示两张真实场景地图上的规划对比、实车视频、路径图和可核对数据。

- [打开中文展示网页]({SITE_URL})：直接播放 12 段主视频、查看逐场景结果。
- [下载原始视频]({REPO_URL}/releases/tag/robot-validation-v1)：14 个原始文件，包含 12 段主视频和 2 段补充短剪辑。
- [下载三项规划指标完整数据](data/planning_comparison.csv)。
- [数据口径与复现说明](数据说明.md)。

## 方法介绍

ProGNet 对自由空间点云输出引导概率和五个路径阶段；ProG-RRT* 根据搜索树进度调节阶段采样偏好，初解后结合引导点与知情子集继续优化。ProG-RRT*-Lazy 增加阶段锚点和惰性图边验证，推迟候选连接的碰撞检查。两种方法每次规划只需一次 ProGNet 推理，实际可行性始终由几何碰撞检测决定。

对比方法名称与论文保持一致：RRT*、N-RRT*、NIRRT*、IPN-RRT*、ProG-RRT*、ProG-RRT*-Lazy。

## 实车规划对比

三项指标越小越好。表格显示精确数据的四位小数，CSV 保留源文件的数值精度。每个场景、每种算法为一条部署规划记录。

'''
    for scene in (1, 2):
        intro += f'### 场景 {scene}\n\n' + make_table([r for r in rows if r["scene"] == f"场景 {scene}"], True)
        intro += f'\n\n![场景 {scene} 规划与定位轨迹](docs/images/scene{scene}-trajectories.png)\n\n'
        intro += f'[查看场景 {scene} 的六种算法视频]({SITE_URL}#scene{scene})\n\n'
    intro += '''## 数据含义

`planned_length_m` 是导出规划折线的长度，单位米；`planning_time_s` 是离线规划调用时间，单位秒，不包含模型加载、A* 参考计算、绘图或传输；`iterations` 是实际规划迭代数。规划在内部路径代价达到栅格 A* 参考的 1.03 倍阈值，或达到 10,000 次迭代时停止。

模型和规划运行于 Windows 端，机器人接收导出的路径并使用统一跟踪控制器执行。规划时间与实车行驶时间分别记录，视频播放时长也不等于这两项时间。本次材料中有 12 条规划记录和 11 份实车轨迹日志；场景 1 的 NIRRT* 日志缺失，不能将缺失日志当作算法失败。逐方法单次展示不构成重复试验统计比较。

## 文件索引

```text
docs/                       中文展示网页、图片和播放版视频
data/planning_comparison.csv 三项规划指标及原始方法键名
data/run_records.json       扩展记录与实车日志完整性标记
data/evidence/              原始路径、定位轨迹、所需规划元数据
data/maps/                  两张原始栅格地图及相对路径配置
data/video_manifest.json    原视频/播放版校验值和对应关系
scripts/                   数据核验和展示页生成脚本
```

原始视频通过仓库发布附件提供；播放版保留所提供视频的时长，只调整分辨率、帧率和编码参数。所有源实验文件均保留在原项目中，仓库展示使用副本。资料尚未包含模型源码和权重发布，不将其描述为完整算法代码开源。
'''
    (ROOT / "README.md").write_text(intro, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="现有实车数据包目录，仅在首次导入时需要")
    parser.add_argument("--video-root", type=Path, help="包含 map1-1 等目录的源视频根目录")
    parser.add_argument("--audit-dir", type=Path, help="本机绘图几何审计工具目录")
    args = parser.parse_args()
    for folder in ("data/evidence", "data/maps", "docs/images", "docs/videos", ".local"):
        (ROOT / folder).mkdir(parents=True, exist_ok=True)
    if args.source:
        source = args.source.resolve()
        original = json.loads((source / "tables" / "all_runs.json").read_text(encoding="utf-8-sig"))
        csv_rows = list(csv.DictReader((source / "tables" / "all_runs.csv").open(encoding="utf-8-sig")))
        assert len(original) == len(csv_rows) == 12
        normalized = []
        for scene in (1, 2):
            for key, label, slug, _ in METHODS:
                row = next(r for r in original if r["scene"] == f"scene_260930_0{scene}" and r["method"] == key)
                row_csv = next(r for r in csv_rows if r["scene"] == row["scene"] and r["method"] == key)
                folder = source / row["source_directory"]
                metrics = json.loads((folder / "planning_metrics.json").read_text(encoding="utf-8-sig"))
                assert float(row["planned_length_m"]) == float(row_csv["planned_length_m"]) == float(metrics["path_length_m"])
                assert float(row["planning_time_s"]) == float(row_csv["planning_time_s"]) == float(metrics["planning_time_sec"])
                assert int(row["iterations"]) == int(row_csv["iterations"]) == int(metrics["sample_calls"])
                destination = ROOT / "data/evidence" / f"scene{scene}" / slug
                destination.mkdir(parents=True, exist_ok=True)
                shutil.copy2(folder / "planned_path.csv", destination / "planned_path.csv")
                trajectories = list(folder.glob("robot*/odom_trajectory.csv"))
                assert len(trajectories) <= 1
                if trajectories:
                    shutil.copy2(trajectories[0], destination / "recorded_trajectory.csv")
                # 发布数值与实验参数；省去机器绝对路径和环境操作日志。
                safe = {k: v for k, v in metrics.items() if not isinstance(v, str) or not (":\\" in v or v.startswith("/home/"))}
                safe.pop("weights", None)
                safe["algorithm_label"] = label
                dump(destination / "planning_metadata.json", safe)
                output = dict(row)
                output.update(scene=f"场景 {scene}", scene_id=row["scene"], method=label, method_key=key,
                              evidence_directory=destination.relative_to(ROOT).as_posix())
                output.pop("label", None); output.pop("source_directory", None)
                normalized.append(output)
        for scene in (1, 2):
            shutil.copy2(source / "maps" / f"scene_260930_0{scene}.pgm", ROOT / "data/maps" / f"scene{scene}.pgm")
            map_yaml = (source / "maps" / f"scene_260930_0{scene}.yaml").read_text(encoding="utf-8")
            (ROOT / "data/maps" / f"scene{scene}.yaml").write_text("image: scene%d.pgm\n" % scene + "\n".join(map_yaml.splitlines()[1:]) + "\n", encoding="utf-8")
        dump(ROOT / "data/run_records.json", normalized)
        write_csv(ROOT / "data/planning_comparison.csv", normalized,
                  ["scene", "method", "method_key", "planned_length_m", "planning_time_s", "iterations"])
    rows = json.loads((ROOT / "data/run_records.json").read_text(encoding="utf-8"))
    draw_results(rows, args.audit_dir)
    manifest = []
    if args.video_root:
        import cv2
        import imageio_ffmpeg
        ffmpeg = imageio_ffmpeg.get_ffmpeg_exe()
        for scene in (1, 2):
            for key, label, slug, index in METHODS:
                slot = f"map{scene}-{index}"
                sources = list((args.video_root / slot).rglob("*.mp4"))
                # 主视频保留该算法目录里时长最长的版本，其他版本作为独立补充附件。
                clips = []
                for source_video in sources:
                    cap = cv2.VideoCapture(str(source_video)); fps = cap.get(cv2.CAP_PROP_FPS)
                    clips.append((cap.get(cv2.CAP_PROP_FRAME_COUNT) / fps, source_video)); cap.release()
                assert clips, slot
                for num, (duration, source_video) in enumerate(sorted(clips, reverse=True)):
                    primary = num == 0
                    name = f"scene{scene}-{slug}" + ("" if primary else f"-补充剪辑{num}")
                    original_name = name + "-原始.mp4"
                    item = dict(scene_number=scene, method=label, source_slot=slot, primary=primary,
                                source_sha256=sha(source_video), source_bytes=source_video.stat().st_size,
                                duration_s=duration, release_asset=original_name,
                                original_url=f"{REPO_URL}/releases/download/robot-validation-v1/{original_name}")
                    if primary:
                        target = ROOT / "docs/videos" / f"{name}.mp4"
                        subprocess.run([ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(source_video),
                                        "-map", "0:v:0", "-map", "0:a?", "-vf", "scale=1280:-2", "-r", "30",
                                        "-c:v", "libx264", "-preset", "fast", "-crf", "24", "-pix_fmt", "yuv420p",
                                        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(target)], check=True)
                        cap = cv2.VideoCapture(str(target)); out_fps = cap.get(cv2.CAP_PROP_FPS)
                        out_duration = cap.get(cv2.CAP_PROP_FRAME_COUNT) / out_fps
                        assert abs(duration - out_duration) <= .08
                        cap.set(cv2.CAP_PROP_POS_MSEC, duration * 300)
                        ok, frame = cap.read(); cap.release(); assert ok
                        poster = ROOT / "docs/images" / f"{name}-poster.jpg"
                        Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)).save(poster, quality=86)
                        item.update(preview_file=f"videos/{target.name}", poster_file=f"images/{poster.name}",
                                    preview_sha256=sha(target), preview_bytes=target.stat().st_size, preview_duration_s=out_duration,
                                    transformation="缩放至1280像素宽、30帧每秒、H.264编码；不裁剪、不变速")
                        print(f"播放版完成：场景 {scene} / {label}", flush=True)
                    manifest.append(item)
        dump(ROOT / "data/video_manifest.json", manifest)
    else:
        manifest = json.loads((ROOT / "data/video_manifest.json").read_text(encoding="utf-8"))
    make_pages(rows, manifest)
    files = []
    for folder in (ROOT / "data", ROOT / "docs"):
        for path in sorted(folder.rglob("*")):
            if path.is_file(): files.append(dict(file=path.relative_to(ROOT).as_posix(), sha256=sha(path), bytes=path.stat().st_size))
    dump(ROOT / "checksums.json", files)
    print(f"核验完成：{len(rows)} 条规划记录，{sum(bool(r['robot_record_present']) for r in rows)} 份实车日志，{len(manifest)} 个原视频。")


if __name__ == "__main__":
    main()
