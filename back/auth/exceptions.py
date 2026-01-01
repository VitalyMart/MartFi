class AuthException(Exception):
    """Базовое исключение для аутентификации"""

    pass


class RateLimitException(AuthException):
    """Превышен лимит запросов"""

    pass


class InvalidCredentialsException(AuthException):
    """Неверные учетные данные"""

    pass


class UserAlreadyExistsException(AuthException):
    """Пользователь уже существует"""

    pass


class ValidationException(AuthException):
    """Ошибка валидации"""

    pass
