class SnowflakeError(Exception):
    """Base exception for Snowflake ID generation."""


class InvalidWorkerIdError(SnowflakeError):
    """Raised when the worker ID is outside the allocated range."""


class ClockRollbackError(SnowflakeError):
    """Raised when the system clock moves backward beyond tolerance."""
