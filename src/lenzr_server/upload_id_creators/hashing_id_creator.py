import base64
import hashlib

from lenzr_server.types import UploadID
from lenzr_server.upload_id_creators.id_creator import IDCreator


class HashingIDCreator(IDCreator):

    def __init__(self, seed: int):
        self._seed = seed

    def create_upload_id(self, content: bytes) -> UploadID:
        sha256hashlib = hashlib.sha3_256()
        sha256hashlib.update(self._seed.to_bytes(32, 'big'))
        sha256hashlib.update(content)

        id_restricted = base64.encodebytes(sha256hashlib.digest()).decode('utf-8')[:32]
        upload_id = UploadID(id_restricted)
        return upload_id