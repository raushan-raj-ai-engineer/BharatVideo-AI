from pathlib import Path
from urllib.parse import urlparse

from app.core.config import get_settings


class LocalStorage:
    def __init__(self):
        settings = get_settings()
        self.root = Path(settings.local_storage_dir)
        self.root.mkdir(parents=True, exist_ok=True)
        self.base_url = settings.public_asset_base_url.rstrip("/")

    def _path(self, key: str) -> Path:
        clean = key.lstrip("/").replace("..", "_")
        path = self.root / clean
        path.parent.mkdir(parents=True, exist_ok=True)
        return path

    def absolute_path(self, key: str) -> str:
        return str(self._path(key))

    def public_url_for(self, path: Path) -> str:
        relative = path.resolve().relative_to(self.root.resolve())
        return f"{self.base_url}/{relative.as_posix()}"

    def path_from_public_url(self, url: str) -> Path:
        base_path = urlparse(self.base_url).path.rstrip("/")
        url_path = urlparse(url).path
        if not url_path.startswith(base_path + "/"):
            raise ValueError("Asset URL is outside configured local storage")
        key = url_path[len(base_path) + 1 :]
        return self._path(key)

    def write_text_asset(self, key: str, content: str) -> str:
        path = self._path(key)
        path.write_text(content, encoding="utf-8")
        return self.public_url_for(path)

    def write_bytes_asset(self, key: str, content: bytes) -> str:
        path = self._path(key)
        path.write_bytes(content)
        return self.public_url_for(path)
