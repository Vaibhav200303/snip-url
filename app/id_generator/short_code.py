from app.id_generator.base62 import encode
from app.id_generator.snowflake import SnowflakeGenerator


class ShortCodeGenerator:
    def __init__(self, snowflake: SnowflakeGenerator):
        self.snowflake = snowflake

    def generate(self) -> str:
        snowflake_id = self.snowflake.generate()

        return encode(snowflake_id)