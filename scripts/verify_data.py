"""核对公开表格、逐次规划元数据、文件哈希和视频对应关系。"""
import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
rows = json.loads((ROOT / "data/run_records.json").read_text(encoding="utf-8"))
csv_rows = list(csv.DictReader((ROOT / "data/planning_comparison.csv").open(encoding="utf-8-sig")))
assert len(rows) == len(csv_rows) == 12
assert len({(r["scene"], r["method"]) for r in rows}) == 12
for row in rows:
    other = next(r for r in csv_rows if r["scene"] == row["scene"] and r["method"] == row["method"])
    path = ROOT / row["evidence_directory"] / "planning_metadata.json"
    metrics = json.loads(path.read_text(encoding="utf-8"))
    for public, raw in (("planned_length_m", "path_length_m"), ("planning_time_s", "planning_time_sec"), ("iterations", "sample_calls")):
        assert float(row[public]) == float(other[public]) == float(metrics[raw]), (row["scene"], row["method"], public)
    present = (path.parent / "recorded_trajectory.csv").exists()
    assert present == bool(row["robot_record_present"])
assert sum(bool(r["robot_record_present"]) for r in rows) == 11
videos = json.loads((ROOT / "data/video_manifest.json").read_text(encoding="utf-8"))
assert len(videos) == 14 and sum(v["primary"] for v in videos) == 12
for video in videos:
    if video["primary"]:
        assert abs(video["duration_s"] - video["preview_duration_s"]) <= .08
        assert (ROOT / "docs" / video["preview_file"]).is_file()
checksums = json.loads((ROOT / "checksums.json").read_text(encoding="utf-8"))
for item in checksums:
    path = ROOT / item["file"]
    with path.open("rb") as stream:
        assert hashlib.file_digest(stream, "sha256").hexdigest() == item["sha256"], item["file"]
    assert path.stat().st_size == item["bytes"]
print("核验通过：12 条规划记录、11 份定位轨迹、12 段主视频及 2 段补充剪辑；所有文件校验值一致。")
