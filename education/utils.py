
LEVELS = [0, 25, 75, 150, 300]  

SESSION_EXP_KEY = "guest_exp"
SESSION_COINS_KEY = "guest_coins"

def calc_level(exp: int) -> tuple[int, int | None, int]:
    current_level = 1
    for idx, threshold in enumerate(LEVELS):
        if exp >= threshold:
            current_level = idx + 1
        else:
            break

    if current_level == len(LEVELS):
        return current_level, None, 100

    prev_exp = LEVELS[current_level - 1]
    next_exp = LEVELS[current_level]
    progress = int((exp - prev_exp) / (next_exp - prev_exp) * 100)
    exp_left = next_exp - exp
    return current_level, exp_left, progress


def add_resources(request, exp=0, coins=0):
    """Добавляет ресурсы в профиль или в сессию."""
    if request.user.is_authenticated:
        request.user.exp += exp
        request.user.coins += coins
        request.user.save(update_fields=["exp", "coins"])
    else:
        request.session[SESSION_EXP_KEY] = request.session.get(SESSION_EXP_KEY, 0) + exp
        request.session[SESSION_COINS_KEY] = request.session.get(SESSION_COINS_KEY, 0) + coins
        request.session.modified = True
