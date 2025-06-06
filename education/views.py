from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .models import Location, Levels, LevelQuestion, Answer
from .forms import CustomUserCreationForm
from django.http import HttpResponse, Http404

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
            user = form.save(commit=False)
            user.exp = 0  # Устанавливаем опыт по умолчанию
            user.coins = 0  # Устанавливаем монеты по умолчанию
            user.save()
            login(request, user)
            return redirect('index')  # Замените 'index' на ваш URL
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'app/register.html', {'form': form})

def location_map(request, slug):
    location = get_object_or_404(Location.objects.prefetch_related('levels'), slug=slug)
    return render(request, "app/location_map.html", {"location": location})

def location_detail(request, slug):
    location = get_object_or_404(Location, slug=slug)
    return render(request, "app/location_detail.html", {"location": location})



def level_detail(request, slug, step=0):
    level = get_object_or_404(Levels.objects.prefetch_related('level_questions__question__answers', 'level_questions__question__images'), slug=slug)
    level_questions = list(level.level_questions.all().order_by('id'))  # Можно добавить поле `order`, если нужно

    if not level_questions:
        return render(request, "app/level_empty.html", {"level": level})

    total_questions = len(level_questions)

    # Если шаг вышел за пределы, показываем финальную страницу
    if step >= total_questions:
        return render(request, "app/level_completed.html", {
            "level": level,
            "exp": level.exp_reward,
            "coins": level.coins_reward,
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

    completed_ids = [level_questions[step].question.id for step in completed_steps if step < len(level_questions)]

    return render(request, "app/level_details.html", {
        "level": level,
        "current_question": current_question,
        "answers": answers,
        "step": step,
        "completed_ids": completed_ids,
        "total_questions": total_questions,
        "completed_steps": completed_steps,
        "error": error,
    })
