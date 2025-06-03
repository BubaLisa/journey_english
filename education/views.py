from django.shortcuts import render, get_object_or_404
from .models import Location, Levels
from django.http import HttpResponse

def index(request):
    first_location = Location.objects.first()
    if not first_location:
        return HttpResponse("<h2>Нет доступных локаций</h2>")

    return render(request, "app/location_map.html", {
        "location": first_location,
        "levels": first_location.levels.all()
    })

def location_map(request, slug):
    location = get_object_or_404(Location.objects.prefetch_related('levels'), slug=slug)
    return render(request, "app/location_map.html", {"location": location})

def location_detail(request, slug):
    location = get_object_or_404(Location, slug=slug)
    return render(request, "app/location_detail.html", {"location": location})

def level_detail(request, slug):
    level = get_object_or_404(Levels, slug=slug)
    return render(request, "app/level_detail.html", {"level": level})