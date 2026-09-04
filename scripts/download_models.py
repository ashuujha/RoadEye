"""Download only pinned inference weights, verifying SHA256 before atomic installation."""

import json
import os
import urllib.request
from hashlib import sha256
from pathlib import Path


def main():
    root = Path("models")
    root.mkdir(exist_ok=True)
    for name, item in json.loads(Path("packages/roadeye/recorded/models.json").read_text()).items():
        path = root / f"{name}.onnx"
        if path.exists() and sha256(path.read_bytes()).hexdigest() == item["sha256"]:
            print(f"{name}: verified existing weights")
            continue
        with urllib.request.urlopen(item["url"], timeout=120) as response:
            content = response.read(item["size"] + 1)
        if len(content) != item["size"] or sha256(content).hexdigest() != item["sha256"]:
            raise ValueError(f"{name}: download digest/size mismatch")
        temporary = path.with_suffix(".download")
        temporary.write_bytes(content)
        os.replace(temporary, path)
        print(f"{name}: downloaded and verified ({item['license']})")


if __name__ == "__main__":
    main()
