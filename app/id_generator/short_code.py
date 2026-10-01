import hashlib
import hmac

from app.id_generator.base62 import encode
from app.id_generator.snowflake import SnowflakeGenerator


class ShortCodeGenerator:
    def __init__(self, snowflake: SnowflakeGenerator, secret: str = ""):
        self.snowflake = snowflake
        self.secret = secret.encode()

    def generate(self) -> str:
        snowflake_id = self.snowflake.generate()

        if not self.secret:
            return encode(snowflake_id)
        digest = hmac.new(
            self.secret,
            snowflake_id.to_bytes(8, byteorder="big", signed=False),
            hashlib.sha256,
        ).digest()
        return encode(int.from_bytes(digest[:9], byteorder="big"))
