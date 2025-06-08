from django.contrib.auth import user_logged_in
from .utils import SESSION_EXP_KEY, SESSION_COINS_KEY

def merge_guest_resources(sender, request, user, **kwargs):
    exp = request.session.pop(SESSION_EXP_KEY, 0)
    coins = request.session.pop(SESSION_COINS_KEY, 0)

    if exp or coins:
        user.exp += exp
        user.coins += coins
        user.save(update_fields=["exp", "coins"])
        request.session.modified = True

user_logged_in.connect(merge_guest_resources)
