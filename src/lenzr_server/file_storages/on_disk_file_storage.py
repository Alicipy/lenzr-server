import pathlib
from typing import TypedDict

from lenzr_server.file_storages.file_storage import FileStorage


class OnDiskSearchParameters(TypedDict):
    on_disk_filename: str


class OnDiskFileStorage(FileStorage[OnDiskSearchParameters]):
    def __init__(self, base_path: pathlib.Path | str):
        self._base_path = pathlib.Path(base_path)

        self._base_path.mkdir(parents=True, exist_ok=True)

    def add_file(self, on_disk_search_params: OnDiskSearchParameters, upload_content: bytes):
        file_path = self._base_path / on_disk_search_params["on_disk_filename"]
        with open(file_path, "wb") as f:
            f.write(upload_content)

    def get_file_content(self, on_disk_search_params: OnDiskSearchParameters) -> bytes:
        file_path = self._base_path / on_disk_search_params["on_disk_filename"]
        with open(file_path, "rb") as f:
            return f.read()

    def delete_file_content(self, on_disk_search_params: OnDiskSearchParameters):
        file_path = self._base_path / on_disk_search_params["on_disk_filename"]
        file_path.unlink()
