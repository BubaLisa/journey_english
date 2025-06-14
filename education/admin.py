from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Location, Levels, Question, Answer, Boss, Word, QuestionImage, AnswerImage, LevelQuestion, QuestionPhrase, BossWord, Achievements, UserAchievements

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

class BossWordInline(admin.TabularInline):
    model = BossWord
    extra = 1
    autocomplete_fields = ['word']


class UserAchievementsInline(admin.TabularInline):
    model = UserAchievements
    extra = 0
    autocomplete_fields = ['user']
    readonly_fields = ['created_at', 'updated_at']
    show_change_link = True




class AchievementsAdmin(admin.ModelAdmin):
    list_display = ['title', 'desc', 'icon_preview', 'short_condition']
    search_fields = ['title', 'desc']
    inlines = [UserAchievementsInline]
    readonly_fields = ['icon_preview']
    ordering = ['title']

    def icon_preview(self, obj):
        if obj.icon_url:
            return format_html(f'<img src="{obj.icon_url}" style="height:40px;" />')
        return "—"
    icon_preview.short_description = "Иконка"

    def short_condition(self, obj):
        cond = obj.condition_json
        return str(cond) if cond else "—"
    short_condition.short_description = "Условия"


class UserAchievementsAdmin(admin.ModelAdmin):
    list_display = ['user', 'achievement', 'created_at']
    list_filter = ['achievement', 'created_at']
    autocomplete_fields = ['user', 'achievement']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-created_at']


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

class BossAdmin(admin.ModelAdmin):
    inlines = [BossWordInline]


class WordAdmin(admin.ModelAdmin):
    search_fields = ['word', 'translation', 'category']


admin.site.register(CustomUser, CustomUserAdmin)
admin.site.register(Location, LocationAdmin)
admin.site.register(Levels, LevelsAdmin)
admin.site.register(Question, QuestionAdmin)
admin.site.register(Answer, AnswerAdmin)
admin.site.register(Boss, BossAdmin)
admin.site.register(Word, WordAdmin)
admin.site.register(Achievements, AchievementsAdmin)
admin.site.register(UserAchievements, UserAchievementsAdmin)
