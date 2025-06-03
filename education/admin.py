from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Location, Levels, Question, Answer, Boss, Word

class CustomUserAdmin(UserAdmin):
    model = CustomUser
    list_display = ('email', 'name', 'is_staff', 'is_superuser')
    search_fields = ('email', 'name')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'name', 'password')}),
        ('Права доступа', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
        ('Дополнительно', {'fields': ('exp', 'coins')}),
    )

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2', 'exp', 'coins', 'is_active', 'is_staff', 'is_superuser')}
        ),
    )

class LocationAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}

class LevelsAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}

admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Levels, LevelsAdmin)
admin.site.register(Question)
admin.site.register(Answer)
admin.site.register(Boss)
admin.site.register(Word)

