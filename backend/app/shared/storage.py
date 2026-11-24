import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from app.core.config import get_settings


class StorageProvider(ABC):
    @abstractmethod
    async def save(self, clinic_id: uuid.UUID, filename: str, content: bytes) -> str:
        """Stores the bytes and returns the key needed to read them back."""

    @abstractmethod
    async def read(self, key: str) -> bytes: ...

    @abstractmethod
    async def delete(self, key: str) -> None: ...


class LocalStorageProvider(StorageProvider):
    def __init__(self, base_path: str):
        self.base_path = Path(base_path)

    def _resolve(self, key: str) -> Path:
        path = (self.base_path / key).resolve()
        if not str(path).startswith(str(self.base_path.resolve())):
            raise ValueError("Ruta de archivo inválida")
        return path

    async def save(self, clinic_id: uuid.UUID, filename: str, content: bytes) -> str:
        suffix = Path(filename).suffix[:12]
        key = f"{clinic_id}/{uuid.uuid4().hex}{suffix}"
        path = self._resolve(key)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return key

    async def read(self, key: str) -> bytes:
        return self._resolve(key).read_bytes()

    async def delete(self, key: str) -> None:
        self._resolve(key).unlink(missing_ok=True)


def get_storage() -> StorageProvider:
    settings = get_settings()
    if settings.STORAGE_PROVIDER == "s3":
        raise NotImplementedError(
            "El proveedor S3 aún no está implementado. Use STORAGE_PROVIDER=local."
        )
    return LocalStorageProvider(settings.STORAGE_LOCAL_PATH)
