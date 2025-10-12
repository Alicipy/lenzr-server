from typing import Protocol, TypeVar

T = TypeVar("T", contravariant=True)

class FileStorage(Protocol[T]):
    def add_file(self, search_params: T, upload_content: bytes) -> None:
        pass

    def get_file_content(self, search_params: T) -> bytes:
        pass
