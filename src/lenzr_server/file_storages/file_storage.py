from typing import NewType, Protocol

FileID = NewType("FileID", str)


class FileStorage(Protocol):
    def add_file(self, file_id: FileID, content: bytes) -> None:
        pass

    def get_file_content(self, file_id: FileID) -> bytes:
        pass

    def delete_file_content(self, file_id: FileID) -> None:
        pass
