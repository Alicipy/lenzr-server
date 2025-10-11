from lenzr_server.upload_id_creators.hashing_id_creator import HashingIDCreator


def test__create_upload_id__valid_content__returns_hash():
    seed = 1234
    content = b"example content"
    creator = HashingIDCreator(seed=seed)

    upload_id = creator.create_upload_id(content)

    assert isinstance(upload_id, str)
    assert len(upload_id) == 32


def test__create_upload_id__empty_content__returns_hash():
    seed = 5678
    content = b""
    creator = HashingIDCreator(seed=seed)

    upload_id = creator.create_upload_id(content)

    assert isinstance(upload_id, str)
    assert len(upload_id) == 32


def test__create_upload_id__different_seeds_same_content__returns_different_hashes():
    content = b"same content"
    creator1 = HashingIDCreator(seed=1)
    creator2 = HashingIDCreator(seed=2)

    upload_id1 = creator1.create_upload_id(content)
    upload_id2 = creator2.create_upload_id(content)

    assert upload_id1 != upload_id2


def test__create_upload_id__same_seed_and_content__returns_same_hash():
    seed = 9999
    content = b"consistent content"
    creator1 = HashingIDCreator(seed=seed)
    creator2 = HashingIDCreator(seed=seed)

    upload_id1 = creator1.create_upload_id(content)
    upload_id2 = creator2.create_upload_id(content)

    assert upload_id1 == upload_id2
