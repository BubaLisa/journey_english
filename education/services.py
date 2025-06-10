from django.db import transaction
from .well_phrases import get_random_phrase

def toss_coin(user, cost: int = 1) -> dict:
    """
    Пытается снять `cost` монет у пользователя и вернуть фразу.
    Возвращает словарь для фронта.
    """
    if user.coins < cost:
        return {"success": False, "error": "Недостаточно монет"}

    with transaction.atomic():
        user.coins -= cost
        user.save(update_fields=["coins"])

    return {"success": True, "phrase": get_random_phrase(), "coins": user.coins}