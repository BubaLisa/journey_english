from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse, Http404, JsonResponse
from django.urls import reverse
from django.utils.html import format_html
from django.utils.text import slugify
from django.db import IntegrityError

from .models import Location, Levels, LevelQuestion, Answer, Word, LevelProgress, Boss, BossWord, Achievements
from .forms import CustomUserCreationForm
from .utils import add_resources
from .services import toss_coin

import re
import math
import random
from functools import wraps


def get_previous_level(level):
    """Возвращает ближайший предыдущий уровень в той же локации."""
    return (
        Levels.objects
        .filter(location=level.location, order__lt=level.order)
        .order_by("-order")
        .first()
    )

def require_prev_level_passed(view):
    @wraps(view)
    def wrapper(request, *args, **kwargs):
        slug = kwargs.get("slug")
        level = get_object_or_404(Levels, slug=slug)
        prev_level = get_previous_level(level)

        if prev_level:
            if request.user.is_authenticated:
                # проверка через модель
                if not LevelProgress.objects.filter(user=request.user, level=prev_level, passed=True).exists():
                    messages.error(request, "Вы должны пройти предыдущий уровень, прежде чем начать этот.")
                    return redirect("index")
            else:
                # проверка через сессию
                passed = request.session.get("passed_levels", [])
                if prev_level.slug not in passed:
                    messages.error(request, "Вы должны пройти предыдущий уровень, прежде чем начать этот.")
                    return redirect("index")

        return view(request, *args, **kwargs)
    return wrapper



def index(request):
    first_location = Location.objects.first()
    if not first_location:
        return HttpResponse("<h2>Нет доступных локаций</h2>")

    return render(request, "app/location_map.html", {
        "location": first_location,
        "levels": first_location.levels.all()
    })


# === РЕГИСТРАЦИЯ ===
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.exp = 0
                user.coins = 0
                user.save()
            except IntegrityError:
                login_url = reverse('login')
                msg = format_html(
                    'Пользователь с такой почтой уже существует. Попробуйте <a href="{}">войти</a>.', login_url
                )
                form.add_error('email', msg)
            else:
                auth_login(request, user)

                # ⬇️ ПЕРЕНОС ПРОГРЕССА ИЗ СЕССИИ В БД
                from .models import Levels, LevelProgress
                passed_levels = request.session.get('passed_levels', [])
                for slug in passed_levels:
                    level = Levels.objects.filter(slug=slug).first()
                    if level:
                        progress, _ = LevelProgress.objects.get_or_create(user=user, level=level)
                        progress.passed = True
                        if not progress.completed_steps:
                            steps = request.session.get(f'completed_steps_{slug}', [])
                            progress.completed_steps = steps
                        progress.save()

                return redirect('index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'app/register.html', {'form': form})


# === ЛОГИН ===
def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)

            # ⬇️ ПЕРЕНОС ПРОГРЕССА ИЗ СЕССИИ В БД
            from .models import Levels, LevelProgress
            passed_levels = request.session.get('passed_levels', [])
            for slug in passed_levels:
                level = Levels.objects.filter(slug=slug).first()
                if level:
                    progress, _ = LevelProgress.objects.get_or_create(user=user, level=level)
                    progress.passed = True
                    if not progress.completed_steps:
                        steps = request.session.get(f'completed_steps_{slug}', [])
                        progress.completed_steps = steps
                    progress.save()

            return redirect('index')
    else:
        form = AuthenticationForm(request)
    return render(request, 'app/login.html', {'form': form})



def logout_view(request):
    logout(request)
    return redirect('index')





'''@login_required
def achievements_view(request):
    user_achievements_qs = request.user.achievements.select_related('achievement')
    unlocked_ids = set(user_ach.achievement.id for user_ach in user_achievements_qs)
    all_achievements = Achievements.objects.all()

    return render(request, 'app/achievements.html', {
        'all_achievements': all_achievements,
        'unlocked_ids': unlocked_ids,
    })



def check_and_award_achievements(user, request=None):
    achievements = Achievements.objects.all()

    for achievement in achievements:
        if UserAchievements.objects.filter(user=user, achievement=achievement).exists():
            continue  # Уже получено

        condition = achievement.condition_json
        if not condition or not isinstance(condition, dict):
            continue  # Условие не задано или некорректное

        condition_type = condition.get("type")

        if condition_type == "level_passed":
            # Условие: пройти уровень с указанным slug
            slug = condition.get("slug")
            if slug and LevelProgress.objects.filter(user=user, level__slug=slug, passed=True).exists():
                UserAchievements.objects.create(user=user, achievement=achievement)
                if request:
                    from django.contrib import messages
                    messages.success(
                        request,
                        f' Новое достижение: {achievement.title}!',
                        extra_tags='achievement-popup'
                    )

        elif condition_type == "words_learned":
            # Условие: выучить N слов
            required_count = condition.get("count", 0)
            if hasattr(user, "words_learned") and user.words_learned >= required_count:
                UserAchievements.objects.create(user=user, achievement=achievement)
                if request:
                    from django.contrib import messages
                    messages.success(
                        request,
                        f' Новое достижение: {achievement.title}!',
                        extra_tags='achievement-popup'
                    )'''



# === ЛОКАЦИЯ ===
def location_map(request, slug):
    location = get_object_or_404(Location.objects.prefetch_related('levels'), slug=slug)
    passed_levels = request.session.get('passed_levels', [])

    levels_with_access = []

    for level in location.levels.all().order_by('order'):
        previous_level = get_previous_level(level)
        access = not previous_level or previous_level.slug in passed_levels

        # Награды — уменьшаем опыт, если уровень уже пройден
        if level.slug in passed_levels:
            exp_reward_display = math.floor(level.exp_reward / 2)
            coins_reward_display = 0
        else:
            exp_reward_display = level.exp_reward
            coins_reward_display = level.coins_reward

        levels_with_access.append({
            'level': level,
            'access': access,
            'exp_reward_display': exp_reward_display,
            'coins_reward_display': coins_reward_display,
        })

    return render(request, "app/location_map.html", {
        "location": location,
        "levels_with_access": levels_with_access,
    })

def location_detail(request, slug):
    location = get_object_or_404(Location, slug=slug)
    return render(request, "app/location_detail.html", {"location": location})


@login_required
def well_toss_view(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "Только POST"}, status=400)

    result = toss_coin(request.user)
    status = 200 if result["success"] else 400
    return JsonResponse(result, status=status)
    

MAX_ATTEMPTS = 3   

def normalise(txt: str) -> str:
    return slugify(txt.strip().lower())


# === ТЕОРИЯ ===
@require_prev_level_passed
def level_detail(request, slug, step=0):
    level = get_object_or_404(
        Levels.objects.prefetch_related('level_questions__question__answers', 'level_questions__question__images'),
        slug=slug
    )
    level_questions = list(level.level_questions.all().order_by('id'))
    total_questions = len(level_questions)

    if level.type == Levels.LevelType.TRIAL:
        return redirect("level_trial", slug=slug, step=step)
    elif level.type == Levels.LevelType.BOSS:
        return redirect("level_boss", slug=slug)

    if not level_questions:
        return render(request, "app/level_empty.html", {"level": level})

    # Получаем прогресс
    if request.user.is_authenticated:
        progress, _ = LevelProgress.objects.get_or_create(user=request.user, level=level)
        completed_steps = progress.completed_steps
        is_repeat = progress.passed
    else:
        completed_steps = request.session.get(f"completed_steps_{slug}", [])
        passed_levels = request.session.get("passed_levels", [])
        is_repeat = level.slug in passed_levels

    # Завершение
    if step >= total_questions:
        if not is_repeat:
            exp_to_add = level.exp_reward
            coins_to_add = level.coins_reward

            if request.user.is_authenticated:
                progress.passed = True
                progress.save()
                # check_and_award_achievements(request.user, request)
            else:
                passed_levels.append(level.slug)
                request.session["passed_levels"] = passed_levels
                request.session.modified = True
        else:
            exp_to_add = math.floor(level.exp_reward / 2)
            coins_to_add = 0

        add_resources(request, exp=exp_to_add, coins=coins_to_add)

        return render(request, "app/level_completed.html", {
            "level": level,
            "exp": exp_to_add,
            "coins": coins_to_add,
        })

    current_question = level_questions[step].question
    answers = current_question.answers.all()
    error = None

    if request.method == 'POST':
        if answers.exists():
            answer_id = int(request.POST.get("answer", 0))
            answer = get_object_or_404(Answer, id=answer_id)
            if answer.is_correct:
                if step not in completed_steps:
                    completed_steps.append(step)
                    if request.user.is_authenticated:
                        progress.completed_steps = completed_steps
                        progress.save()
                    else:
                        request.session[f"completed_steps_{slug}"] = completed_steps
                        request.session.modified = True
                return redirect("level_detail_step", slug=slug, step=step + 1)
            else:
                error = "Ответ неправильный. Попробуйте ещё раз."
        else:
            if step not in completed_steps:
                completed_steps.append(step)
                if request.user.is_authenticated:
                    progress.completed_steps = completed_steps
                    progress.save()
                else:
                    request.session[f"completed_steps_{slug}"] = completed_steps
                    request.session.modified = True
            return redirect("level_detail_step", slug=slug, step=step + 1)

    completed_ids = [
        level_questions[s].id
        for s in completed_steps
        if s < len(level_questions)
    ]

    return render(request, "app/level_details.html", {
        "level": level,
        "level_questions": level_questions,
        "current_question": current_question,
        "answers": answers,
        "step": step,
        "completed_ids": completed_ids,
        "total_questions": total_questions,
        "completed_steps": completed_steps,
        "error": error,
    })


# === ИСПЫТАНИЕ ===
@require_prev_level_passed
def level_trial(request, slug, step=0):
    level = get_object_or_404(
        Levels.objects.prefetch_related(
            "level_questions__question__answers",
            "level_questions__question__images",
        ),
        slug=slug,
        type=Levels.LevelType.TRIAL,
    )
    level_questions = list(level.level_questions.all().order_by('id'))
    total_questions = len(level_questions)

    if not total_questions:
        return render(request, "app/level_empty.html", {"level": level})

    if request.user.is_authenticated:
        progress, _ = LevelProgress.objects.get_or_create(user=request.user, level=level)
        completed_steps = progress.completed_steps
        is_repeat = progress.passed
    else:
        session_key = f"level_progress_{slug}"
        session_progress = request.session.get(session_key, {'completed_steps': [], 'passed': False})
        completed_steps = session_progress['completed_steps']
        is_repeat = session_progress['passed']

    if is_repeat and not completed_steps:
        completed_steps = list(range(total_questions))
        if request.user.is_authenticated:
            progress.completed_steps = completed_steps
            progress.save()
        else:
            session_progress['completed_steps'] = completed_steps
            request.session[session_key] = session_progress
            request.session.modified = True

    if step >= total_questions:
        if is_repeat:
            exp_to_add = math.floor(level.exp_reward / 2)
            coins_to_add = 0
        else:
            exp_to_add = level.exp_reward
            coins_to_add = level.coins_reward
            if request.user.is_authenticated:
                progress.passed = True
                progress.save()
                # check_and_award_achievements(request.user, request)
            else:
                session_progress['passed'] = True
                request.session[session_key] = session_progress

                # Обновляем список пройденных уровней в сессии
                passed_levels = request.session.get("passed_levels", [])
                if slug not in passed_levels:
                    passed_levels.append(slug)
                    request.session["passed_levels"] = passed_levels

                request.session.modified = True

        add_resources(request, exp=exp_to_add, coins=coins_to_add)

        return render(request, "app/level_completed.html", {
            "level": level,
            "exp": exp_to_add,
            "coins": coins_to_add,
        })

    current_question = level_questions[step].question
    correct_answers = {
        normalise(ans.text)
        for ans in current_question.answers.filter(is_correct=True)
    }

    attempts_key = f"trial_attempts_{slug}_{step}"
    attempts = request.session.get(attempts_key, 0)
    result = None

    if request.method == "POST":
        user_answer = normalise(request.POST.get("user_answer", ""))
        if user_answer in correct_answers:
            result = "success"
            request.session.pop(attempts_key, None)

            if step not in completed_steps:
                completed_steps.append(step)
                if request.user.is_authenticated:
                    progress.completed_steps = completed_steps
                    progress.save()
                else:
                    session_progress['completed_steps'] = completed_steps
                    request.session[session_key] = session_progress
                    request.session.modified = True
        else:
            attempts += 1
            request.session[attempts_key] = attempts
            if attempts >= MAX_ATTEMPTS:
                result = "fail"
                request.session.pop(attempts_key, None)
            else:
                result = "wrong"

    completed_ids = [
        level_questions[s].id
        for s in completed_steps
        if s < len(level_questions)
    ]

    return render(request, "app/level_trial.html", {
        "level": level,
        "level_questions": level_questions,
        "question": current_question,
        "step": step,
        "result": result,
        "total_questions": total_questions,
        "completed_steps": completed_steps,
        "completed_ids": completed_ids,
        "current_question": current_question,
        "attempts_left": MAX_ATTEMPTS - attempts,
        "next_url": reverse("level_trial", kwargs={"slug": slug, "step": step + 1}),
        "fail_url": reverse("level_fail", kwargs={"slug": slug}),
    })




# === БОСС ===
@require_prev_level_passed
def level_boss(request, slug):
    level = get_object_or_404(Levels, slug=slug, type=Levels.LevelType.BOSS)
    boss = get_object_or_404(Boss, level=level)

    boss_words_qs = BossWord.objects.filter(boss=boss).select_related('word')
    valid_words = {bw.word.word.lower() for bw in boss_words_qs}

    session_key = f"bossfight_{slug}"
    bossfight = request.session.get(session_key, {
        'boss_hp': boss.hp,
        'player_hp': 5,
        'used_words': [],
    })

    message = None

    if request.method == 'POST':
        word = request.POST.get('word_input', '').strip().lower()

        if word in bossfight['used_words']:
            messages.warning(request, "Это слово уже было использовано!")
        elif word in valid_words:
            bossfight['boss_hp'] -= 1
            bossfight['used_words'].append(word)
            messages.success(request, "Успешная атака!")
        else:
            bossfight['player_hp'] -= 1
            messages.error(request, "Промах! Вы потеряли здоровье.")

        # Победа
        if bossfight['boss_hp'] <= 0:
            del request.session[session_key]

            is_repeat = False
            if request.user.is_authenticated:
                progress, created = LevelProgress.objects.get_or_create(user=request.user, level=level)
                is_repeat = progress.passed
                progress.passed = True
                progress.save()
                # check_and_award_achievements(request.user, request)
            else:
                passed_levels = request.session.get("passed_levels", [])
                if slug not in passed_levels:
                    passed_levels.append(slug)
                    request.session["passed_levels"] = passed_levels
                request.session.modified = True
                is_repeat = slug in passed_levels

            exp_to_add = boss.reward_exp // 2 if is_repeat else boss.reward_exp
            coins_to_add = 0 if is_repeat else boss.reward_coins

            add_resources(request, exp=exp_to_add, coins=coins_to_add)

            return render(request, "app/level_completed.html", {
                "level": level,
                "exp": exp_to_add,
                "coins": coins_to_add,
            })

        # Поражение
        if bossfight['player_hp'] <= 0:
            del request.session[session_key]
            return render(request, "app/level_fail.html", {
                "level": level,
                "is_boss": True,
            })

        request.session[session_key] = bossfight
        request.session.modified = True
        return redirect(request.path)

    player_hp_segments = range(5)

    return render(request, "app/level_boss.html", {
        "level": level,
        "boss": boss,
        "boss_hp": bossfight['boss_hp'],
        "player_hp": bossfight['player_hp'],
        "player_hp_segments": player_hp_segments,
        "suppress_base_messages": True,
        "message": message,
    })



def level_fail(request, slug: str):
    
    level = get_object_or_404(Levels, slug=slug)  # убрали фильтрацию по type
    is_boss = level.type == Levels.LevelType.BOSS

    return render(request, "app/level_fail.html", {
        "level": level,
        "is_boss": is_boss,
    })


def mask_word(word):
    """Преобразует слово: заменяет несколько случайных букв на _"""
    indices = random.sample(range(len(word)), k=min(3, len(word)//2))
    return ''.join('_' if i in indices else ch for i, ch in enumerate(word))

def get_boss_hints(request):
    slug = request.GET.get("slug")
    if not slug:
        return JsonResponse({"success": False, "error": "Нет уровня"})

    try:
        level = Levels.objects.get(slug=slug)
        boss = Boss.objects.get(level=level)
        boss_words_qs = BossWord.objects.filter(boss=boss).select_related('word')
        words = [bw.word.word for bw in boss_words_qs]
        if not words:
            return JsonResponse({"success": False, "error": "Нет слов для подсказок"})

        hints = random.sample(words, min(3, len(words)))
        masked = [mask_word(w) for w in hints]
        return JsonResponse({"success": True, "hints": masked})
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})