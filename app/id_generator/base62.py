ALPHABET = "0123456789abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ"
BASE = len(ALPHABET)

DECODE_MAP = {
    character: index
    for index, character in enumerate(ALPHABET)
}


def encode(number: int) -> str:
    if number < 0:
        raise ValueError("number must be non-negative")

    if number == 0:
        return ALPHABET[0]

    characters = []

    while number > 0:
        number, remainder = divmod(number, BASE)
        characters.append(ALPHABET[remainder])

    return "".join(reversed(characters))


def decode(value: str) -> int:
    if not value:
        raise ValueError("value must not be empty")

    number = 0

    for character in value:
        if character not in DECODE_MAP:
            raise ValueError(
                f"Invalid Base62 character: {character!r}"
            )

        number = number * BASE + DECODE_MAP[character]

    return number
