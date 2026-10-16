from __future__ import annotations

import csv
import io
import json
import tempfile
from pathlib import Path
from urllib.request import Request, urlopen

from .embeddings import Identity, parse_embedding


class WhitelistStore:
    def __init__(self, cache_path: str | Path):
        self.cache_path = Path(cache_path)
        self.identities: list[Identity] = []

    def load_cache(self) -> int:
        if not self.cache_path.exists():
            self.identities = []
            return 0
        raw = json.loads(self.cache_path.read_text(encoding="utf-8"))
        self.identities = [Identity(str(row["person_id"]), str(row["name"]), parse_embedding(row["embedding"]), bool(row.get("active", True))) for row in raw]
        return len(self.identities)

    def refresh(self, source: str) -> int:
        if not source:
            return self.load_cache()
        if source.startswith("http://") or source.startswith("https://"):
            request = Request(source, headers={"User-Agent": "Comunito-Facial/0.1"})
            content = urlopen(request, timeout=15).read().decode("utf-8-sig")
        else:
            content = Path(source).read_text(encoding="utf-8-sig")
        identities = []
        for row in csv.DictReader(io.StringIO(content)):
            if not row.get("embedding") or row.get("active", "true").lower() in {"0", "false", "no", "inactivo"}:
                continue
            identities.append({"person_id": row.get("person_id") or row.get("id") or row.get("codigo") or "", "name": row.get("name") or row.get("nombre") or "", "embedding": parse_embedding(row["embedding"]).tolist(), "active": True})
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=self.cache_path.parent, delete=False) as tmp:
            json.dump(identities, tmp, ensure_ascii=False)
            tmp_path = Path(tmp.name)
        tmp_path.replace(self.cache_path)
        return self.load_cache()

    def match(self, feature, similarity) -> tuple[Identity | None, float]:
        best, score = None, -1.0
        for identity in self.identities:
            current = similarity(feature, identity.embedding)
            if current > score:
                best, score = identity, current
        return best, score
