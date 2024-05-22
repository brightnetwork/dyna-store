from dyna_store.main import (
    b62_decode_int,
    b62_encode_int,
)

N = 800000


def test_int_encoding_cherry_picked():
    data = [
        (0, "a"),
        (435543, "bZs3"),
    ]
    for i, o in data:
        assert b62_encode_int(i) == o


def test_int_encoding_unicity():
    s = set()
    for i in range(N):
        s.add(b62_encode_int(i))
    assert len(s) == N


def test_int_encoding_involution():
    for i in range(N):
        assert i == b62_decode_int(b62_encode_int(i))
