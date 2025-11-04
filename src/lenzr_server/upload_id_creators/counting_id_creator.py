from lenzr_server.types import UploadID
from lenzr_server.upload_id_creators.id_creator import IDCreator


class CountingIdCreator(IDCreator):
    def __init__(self):
        self.id = 0
        self.memory = {}

    def create_upload_id(self, content: bytes) -> UploadID:
        if content not in self.memory:
            self.id += 1
            self.memory[content] = self.id

        content_id = self.memory[content]
        upload_id = UploadID(content_id)
        return upload_id

    def reset(self):
        self.__init__()
