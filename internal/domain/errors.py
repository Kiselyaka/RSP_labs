class RepositoryError(Exception):
    """Storage error exposed to the application layer."""


class ErrNotFound(RepositoryError):
    pass


class ErrAlreadyExists(RepositoryError):
    pass


class ErrConflict(RepositoryError):
    pass


class ErrInvalidInput(RepositoryError):
    pass


class ErrServiceUnavailable(RepositoryError):
    pass
