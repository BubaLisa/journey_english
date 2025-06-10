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

from .models import Location, Levels, LevelQuestion, Answer, Word
from .forms import CustomUserCreationForm
from .utils import add_resources
from .services import toss_coin

import math
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



def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.exp = 0
                user.coins = 0
                user.save()               # здесь может упасть IntegrityError
            except IntegrityError:
                # Почта уже занята → пользователь есть
                login_url = reverse('login')  # имя URL для входа
                msg = format_html(
                    'Пользователь с такой почтой уже существует. Попробуйте <a href="{}">войти</a>.', login_url
                )
                form.add_error('email', msg)
            else:
                auth_login(request, user)
                return redirect('index')
    else:
        form = CustomUserCreationForm()
    return render(request, 'app/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            auth_login(request, user)
            return redirect('index')
    else:
        form = AuthenticationForm(request)
    return render(request, 'app/login.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('index')




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


@require_prev_level_passed
def level_detail(request, slug, step=0):
    level = get_object_or_404(Levels.objects.prefetch_related('level_questions__question__answers', 'level_questions__question__images'), slug=slug)
    level_questions = list(level.level_questions.all().order_by('id'))  # Можно добавить поле `order`, если нужно

    if level.type == Levels.LevelType.TRIAL:
        return redirect("level_trial", slug=slug, step=step)


    if not level_questions:
        return render(request, "app/level_empty.html", {"level": level})

    total_questions = len(level_questions)

    # Если шаг вышел за пределы, показываем финальную страницу
    if step >= total_questions:
        
        passed_levels = request.session.get('passed_levels', [])
        
        # Проверяем, проходили ли этот уровень ранее
        is_repeat = level.slug in passed_levels
        
        # Расчёт опыта и монет с учётом повторного прохождения
        if is_repeat:
            exp_to_add = math.floor(level.exp_reward / 2)
            coins_to_add = 0
        else:
            exp_to_add = level.exp_reward
            coins_to_add = level.coins_reward
            # Добавляем уровень в пройденные
            passed_levels.append(level.slug)
            request.session['passed_levels'] = passed_levels
            request.session.modified = True

        add_resources(request, exp=exp_to_add, coins=coins_to_add)

        
        passed_levels = request.session.get('passed_levels', [])
        if level.slug not in passed_levels:
            passed_levels.append(level.slug)
            request.session['passed_levels'] = passed_levels
            request.session.modified = True

        return render(request, "app/level_completed.html", {
            "level": level,
            "exp": exp_to_add,
            "coins": coins_to_add,
        })

    # Текущий вопрос
    current_question = level_questions[step].question
    answers = current_question.answers.all()

    # Получаем список пройденных шагов (можно улучшить, сохраняя в БД)
    completed_steps = request.session.get(f"completed_steps_{slug}", [])

    error = None

    if request.method == 'POST':
        if answers.exists():
            answer_id = int(request.POST.get("answer", 0))
            answer = get_object_or_404(Answer, id=answer_id)

            if answer.is_correct:
                if step not in completed_steps:
                    completed_steps.append(step)
                    request.session[f"completed_steps_{slug}"] = completed_steps
                return redirect("level_detail_step", slug=slug, step=step + 1)
            else:
                error = "Ответ неправильный. Попробуйте ещё раз."
        else:
            # Теоретический вопрос — переход без проверки
            if step not in completed_steps:
                completed_steps.append(step)
                request.session[f"completed_steps_{slug}"] = completed_steps
            return redirect("level_detail_step", slug=slug, step=step + 1)

    completed_ids = [
    level_questions[s].id          # ←  .id у LevelQuestion
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

    # Проверка предыдущего уровня (добавляем в начало функции)



    # Получаем или инициализируем данные о прогрессе
    session_key = f"level_progress_{slug}"
    level_progress = request.session.get(session_key, {
        'completed_steps': [],
        'passed': False
    })

    # Если уровень уже пройден, но нет completed_steps, заполняем все шаги
    if level_progress['passed'] and not level_progress['completed_steps']:
        level_progress['completed_steps'] = list(range(total_questions))
        request.session[session_key] = level_progress
        request.session.modified = True

    # Завершение уровня
    if step >= total_questions:
        is_repeat = level_progress['passed']
        
        if is_repeat:
            exp_to_add = math.floor(level.exp_reward / 2)
            coins_to_add = 0
        else:
            exp_to_add = level.exp_reward
            coins_to_add = level.coins_reward
            level_progress['passed'] = True
            request.session[session_key] = level_progress
            # Добавляем в общий список пройденных уровней
            passed_levels = request.session.get('passed_levels', [])
            if level.slug not in passed_levels:
                passed_levels.append(level.slug)
                request.session['passed_levels'] = passed_levels
            request.session.modified = True

        add_resources(request, exp=exp_to_add, coins=coins_to_add)
        return render(request, "app/level_completed.html", {
            "level": level,
            "exp": exp_to_add,
            "coins": coins_to_add,
        })
    
    # Обработка текущего вопроса
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
            if step not in level_progress['completed_steps']:
                level_progress['completed_steps'].append(step)
                request.session[session_key] = level_progress
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
        for s in level_progress['completed_steps']
        if s < len(level_questions)
    ]

    return render(request, "app/level_trial.html", {
        "level": level,
        "level_questions": level_questions,
        "question": current_question,
        "step": step,
        "result": result,
        "total_questions": total_questions,
        "completed_steps": level_progress['completed_steps'],
        "completed_ids": completed_ids,
        "result": result,
        "current_question": current_question,
        "attempts_left": MAX_ATTEMPTS - attempts,
        "next_url": reverse("level_trial", kwargs={"slug": slug, "step": step + 1}),
        "fail_url": reverse("level_fail", kwargs={"slug": slug}),
    })

def level_fail(request, slug: str):
    level = get_object_or_404(Levels, slug=slug, type=Levels.LevelType.TRIAL)
    return render(request, "app/level_fail.html", {"level": level})