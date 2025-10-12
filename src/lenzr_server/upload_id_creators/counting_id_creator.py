from lenzr_server.types import UploadID
from lenzr_server.upload_id_creators.id_creator import IDCreator


class CountingIdCreator(IDCreator):
    def __init__(self):
        self.id = 0

    def create_upload_id(self, content: bytes) -> UploadID:
        self.id += 1
        upload_id = UploadID(self.id)
        return upload_id

