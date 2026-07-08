import re

def validate_name(name: str) -> bool:
    if not name:
        return False
    name = name.strip()
    if len(name) < 2 or len(name) > 60:
        return False
    if not re.match(r'^[A-Za-zА-Яа-яЁё\s]+$', name):
        return False
    return True

def validate_and_clean_phone(phone: str) -> str:
    if not phone:
        return ""
    cleaned = re.sub(r'\D', '', phone)
    
    if len(cleaned) == 11 and (cleaned.startswith('7') or cleaned.startswith('8')):
        if cleaned.startswith('8'):
            cleaned = '7' + cleaned[1:]
        return '+' + cleaned
    
    return ""
