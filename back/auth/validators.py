from email_validator import validate_email, EmailNotValidError 

def validate_full_name(full_name: str) -> tuple[bool, str]:
    """Валидация ФИО: длина от 2 до 100 символов."""
    full_name = full_name.strip()
    if len(full_name) < 4:
        return False, "ФИО должно содержать минимум 4 символа"
    if len(full_name) > 100:
        return False, "ФИО не может быть длиннее 100 символов"
    return True, ""

def normalize_and_validated_email(email: str):
    try:
        validated = validate_email(email)
        return validated.email
    except EmailNotValidError:
        return None