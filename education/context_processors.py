from .utils import calc_level, SESSION_EXP_KEY, SESSION_COINS_KEY

def user_resources(request):
    if request.user.is_authenticated:
        exp = request.user.exp
        coins = request.user.coins
    else:
        exp = request.session.get(SESSION_EXP_KEY, 0)
        coins = request.session.get(SESSION_COINS_KEY, 0)

    level, left, progress = calc_level(exp)

    if left is None:
        next_level_exp = exp
    else:
        next_level_exp = exp + left

    tooltip = (
        "Вы набрали максимальный уровень"
        if left is None else f"{exp}/{next_level_exp} exp"
    )

    return {
        "user_level": level,
        "user_exp": exp,
        "next_level_exp": next_level_exp,
        "level_progress": progress,
        "level_tooltip": tooltip,
        "user_coins": coins,
        "guest_mode": not request.user.is_authenticated,
    }

