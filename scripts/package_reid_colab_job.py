"""Package only the code/config needed by the private Colab training job."""

from __future__ import annotations

import json
import zipfile

from roadeye.phase2 import ROOT
from roadeye.tracklets import sha256, write_json

FILES = [
    "pyproject.toml",
    "requirements-training.txt",
    "configs/reid-training.json",
    "scripts/train_reid_portable.py",
    "src/roadeye/__init__.py",
    "src/roadeye/reid_training.py",
    "src/roadeye/tracklets.py",
    "src/roadeye/vehicle_encoder.py",
    "third_party/fastreid/LICENSE",
    "third_party/fastreid/NOTICE.md",
]


def main() -> None:
    output = ROOT / "artifacts/reid-training/roadeye-reid-colab-job.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    source_hashes = {
        relative: sha256(ROOT / relative)
        for relative in FILES
        if (ROOT / relative).is_file()
    }
    missing = sorted(set(FILES) - set(source_hashes))
    if missing:
        raise FileNotFoundError(f"Missing job sources: {missing}")
    internal_manifest = {
        "schema_version": 1,
        "purpose": "private_RoadEye_CityFlow_ReID_training_job",
        "source_sha256": source_hashes,
        "contains_data": False,
        "contains_weights": False,
        "contains_credentials": False,
    }
    with zipfile.ZipFile(output, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        for relative in FILES:
            path = ROOT / relative
            archive.write(path, relative)
        archive.writestr(
            "job-manifest.json",
            json.dumps(internal_manifest, indent=2, sort_keys=True) + "\n",
        )
    report = {
        "status": "PASS",
        "archive": output.as_posix(),
        "archive_bytes": output.stat().st_size,
        "archive_sha256": sha256(output),
        "source_sha256": source_hashes,
        **{
            key: internal_manifest[key]
            for key in ("contains_data", "contains_weights", "contains_credentials")
        },
    }
    write_json(output.parent / "job-build.json", report)
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
