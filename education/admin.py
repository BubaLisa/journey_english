from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Location, Levels, Question, Answer, Boss, Word, QuestionImage, AnswerImage, LevelQuestion, QuestionPhrase

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

class QuestionImageInline(admin.TabularInline):
    model = QuestionImage
    extra = 1

class QuestionPhraseInline(admin.TabularInline):
    model = QuestionPhrase
    extra = 1

class AnswerInline(admin.TabularInline):
    model  = Answer
    extra  = 1

class AnswerImageInline(admin.TabularInline):
    model = AnswerImage
    extra = 1

class LevelQuestionInline(admin.TabularInline):
    model = LevelQuestion
    extra = 1
    autocomplete_fields = ['question']
    ordering = ['order']
    fields = ['question', 'order']





class AnswerAdmin(admin.ModelAdmin):
    inlines = [AnswerImageInline]

class LocationAdmin(admin.ModelAdmin):
    prepopulated_fields = {"slug": ("title",)}

class QuestionAdmin(admin.ModelAdmin):
    inlines = [QuestionImageInline, QuestionPhraseInline, AnswerInline]
    search_fields = [
        'phrases__text',
        'phrases__translation',
    ]
class LevelsAdmin(admin.ModelAdmin):
    list_display = ['title', 'location', 'type', 'order']
    prepopulated_fields = {"slug": ("title",)}
    inlines = [LevelQuestionInline]
    ordering = ['order']


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Levels, LevelsAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer, AnswerAdmin)
admin.site.register(Boss)
admin.site.register(Word)

