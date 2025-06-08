from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout
from django.contrib.auth.forms import AuthenticationForm
from django.http import HttpResponse, Http404
from django.urls import reverse
from django.utils.html import format_html
from django.db import IntegrityError

from .models import Location, Levels, LevelQuestion, Answer, Word
from .forms import CustomUserCreationForm
from .utils import add_resources

import math


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
        previous_level = Levels.objects.filter(location=level.location, order=level.order - 1).first()
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



def level_detail(request, slug, step=0):
    level = get_object_or_404(Levels.objects.prefetch_related('level_questions__question__answers', 'level_questions__question__images'), slug=slug)
    level_questions = list(level.level_questions.all().order_by('id'))  # Можно добавить поле `order`, если нужно

    if step == 0:
        previous_level = Levels.objects.filter(location=level.location, order=level.order - 1).first()

        if previous_level:
            passed_levels = request.session.get('passed_levels', [])
            if previous_level.slug not in passed_levels:
                messages.error(request, "Вы должны пройти предыдущий уровень, прежде чем начать этот.")
                return redirect("index")

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

def trial_level_view(request, slug):
    level = get_object_or_404(Levels, slug=slug)
    words = list(level.words.all())

    if not words:
        return render(request, 'level_empty.html', {'level': level})

    # Получаем индекс текущего слова из сессии
    index = request.session.get(f'trial_word_index_{slug}', 0)

    idx_key   = f'trial_idx_{slug}'
    fail_key  = f'trial_fail_{slug}'      # счётчик ошибок
    index     = request.session.get(idx_key, 0)
    fails     = request.session.get(fail_key, 0)


    if index >= len(words):
        request.session.pop(idx_key, None)
        request.session.pop(fail_key, None)
        return render(request, 'trial_level_complete.html', {'level': level})

    word = words[index]
    context = {'level': level, 'word': word}

    if request.method == 'POST':
        answer = request.POST.get('answer', '').strip().lower()
        if answer == word.translation.lower():
            # успех: переходим к следующему слову
            request.session[idx_key] = index + 1
            request.session[fail_key] = 0
            context['correct'] = True
        else:
            fails += 1
            if fails >= 3:
                # неудача: показываем падение
                context['failed'] = True
                fails = 0                      # обнуляем счётчик
            else:
                context['error'] = f"Неправильно… Попыток осталось: {3 - fails}"
            request.session[fail_key] = fails

    return render(request, 'trial_level.html', context)