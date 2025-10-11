from lenzr_server.upload_id_creators.id_creator import IDCreator


class CountingIdCreator(IDCreator):
    def __init__(self):
        self.id = 0

    def create_upload_id(self, content: bytes) -> str:
        self.id += 1
        return str(self.id)

