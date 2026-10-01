from app.id_generator.short_code import ShortCodeGenerator


class FakeSnowflake:
    def __init__(self):
        self.calls = 0

    def generate(self) -> int:
        self.calls += 1
        return 125


def test_generates_short_code():
    snowflake = FakeSnowflake()

    generator = ShortCodeGenerator(snowflake)

    assert generator.generate() == "21"


def test_short_code_generator_uses_snowflake():
    snowflake = FakeSnowflake()

    generator = ShortCodeGenerator(snowflake)

    generator.generate()

    assert snowflake.calls == 1