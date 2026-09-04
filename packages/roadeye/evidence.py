from hashlib import sha256
from pathlib import Path


class LocalEvidenceStore:
    def __init__(self, root: Path):
        self.root = root.resolve()

    def read(self, key: str) -> bytes:
        candidate = self.root / key
        if not key or Path(key).is_absolute() or ".." in Path(key).parts:
            raise ValueError("Unsafe evidence key")
        path = candidate.resolve()
        if not path.is_relative_to(self.root) or path.is_symlink():
            raise ValueError("Evidence key escapes store")
        content = path.read_bytes()
        if len(content) > 1_000_000:
            raise ValueError("Evidence exceeds local demo size limit")
        return content


def digest(content: bytes) -> str:
    return sha256(content).hexdigest()
