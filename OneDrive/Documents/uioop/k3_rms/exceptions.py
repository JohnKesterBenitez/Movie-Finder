class ApplicationError(Exception):
    """Base application exception."""


class DatabaseConfigurationError(ApplicationError):
    """Raised when required database settings are missing."""


class ReservationValidationError(ApplicationError):
    """Raised when a reservation request fails validation."""
