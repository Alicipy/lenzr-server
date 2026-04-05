import pathlib

from lenzr_server.file_storages.file_storage import FileID, FileStorage


class OnDiskFileStorage(FileStorage):
    def __init__(self, base_path: pathlib.Path | str):
        self._base_path = pathlib.Path(base_path)

        self._base_path.mkdir(parents=True, exist_ok=True)

    def add_file(self, file_id: FileID, content: bytes):
        file_path = self._base_path / file_id
        with open(file_path, "wb") as f:
            f.write(content)

    def get_file_content(self, file_id: FileID) -> bytes:
        file_path = self._base_path / file_id
        with open(file_path, "rb") as f:
            return f.read()

    def delete_file_content(self, file_id: FileID) -> None:
        file_path = self._base_path / file_id
        file_path.unlink()
