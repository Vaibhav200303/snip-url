import pytest

from app.id_generator.base62 import decode, encode


def test_encode_zero():
    assert encode(0) == "0"


def test_encode_small_number():
    assert encode(125) == "21"


def test_decode_small_number():
    assert decode("21") == 125


def test_encode_decode_round_trip():
    numbers = [
        0,
        1,
        61,
        62,
        12345,
        879527915232342016,
    ]

    for number in numbers:
        assert decode(encode(number)) == number



def test_encode_rejects_negative_number():
    with pytest.raises(ValueError):
        encode(-1)


def test_decode_rejects_empty_string():
    with pytest.raises(ValueError):
        decode("")


def test_decode_rejects_invalid_character():
    with pytest.raises(ValueError):
        decode("abc!")
