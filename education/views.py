from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from .models import Location, Levels
from .forms import CustomUserCreationForm
from django.http import HttpResponse

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

def level_detail(request, slug):
    level = get_object_or_404(Levels, slug=slug)
    return render(request, "app/level_detail.html", {"level": level})