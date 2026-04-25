import os
import pathlib

from lenzr_server.file_storages.file_storage import FileID, FileStorage


class OnDiskFileStorage(FileStorage):
    def __init__(self, base_path: pathlib.Path | str):
        self._base_path = pathlib.Path(base_path)

        self._base_path.mkdir(parents=True, exist_ok=True)
        self._resolved_base_path = self._base_path.resolve()

    def add_file(self, file_id: FileID, content: bytes):
        file_path = self._resolve(file_id)
        with open(file_path, "wb") as f:
            f.write(content)

    def get_file_content(self, file_id: FileID) -> bytes:
        file_path = self._resolve(file_id)
        with open(file_path, "rb") as f:
            return f.read()

    def delete_file_content(self, file_id: FileID) -> None:
        file_path = self._resolve(file_id)
        file_path.unlink()

    def _resolve(self, file_id: FileID) -> pathlib.Path:
        # FileID is just a string newtype; without validation a caller could
        # pass "../../etc/passwd" and escape the storage directory.
        if not file_id or os.sep in file_id or (os.altsep and os.altsep in file_id):
            raise ValueError(f"Invalid file_id: {file_id!r}")
        candidate = (self._base_path / file_id).resolve()
        if candidate == self._resolved_base_path or not candidate.is_relative_to(
            self._resolved_base_path
        ):
            raise ValueError(f"Invalid file_id: {file_id!r}")
        return candidate
