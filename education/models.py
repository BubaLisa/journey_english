from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.core.validators import MinValueValidator
from django.utils.text import slugify

class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email должен быть указан")
        email = self.normalize_email(email)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        return self.create_user(email, password, **extra_fields)

class CustomUser(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(
        verbose_name="Имя пользователя",
        max_length=255,
    )
    email = models.EmailField(
        verbose_name="Почта",
        unique=True,
        max_length=254
    )
    exp = models.IntegerField(
        verbose_name="Опыт пользователя",
        default=0,
        )
    coins = models.IntegerField(
        verbose_name="Монеты пользователя",
        default=0,
    )

    is_active = models.BooleanField(
        default=True,
    )
    is_staff = models.BooleanField(
        default=False,
    )

    objects = CustomUserManager()

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователь'

    def __str__(self):
        return self.email
    

class Location(models.Model):
    title = models.CharField(
        verbose_name="Локация",
        max_length=100,
        unique=True
    )
    desc = models.TextField(
        verbose_name = "Описание",
        blank=True,
    )
    slug = models.SlugField(
        "URL",
        max_length=250,
        unique=True,
        null=False,
        blank=True,
        editable=True,
    )

    class Meta:
        verbose_name = 'Локация'
        verbose_name_plural = 'Локация'

    def __str__(self):
        return self.title

class Levels(models.Model):
    class LevelType(models.TextChoices):
        THEORY = 'TH', 'Теория'
        TRIAL = 'TR', 'Испытание'
        BOSS = 'BS', 'Босс-файт'

    location = models.ForeignKey(
        'Location',
        on_delete=models.CASCADE,
        related_name='levels',
        verbose_name='Локация',
    )
    title = models.CharField(
        verbose_name="Название уровня",
        max_length=255,
    )
    desc = models.TextField(
        verbose_name='Тип уровня',
        blank=True,
    )
    type = models.CharField(
        max_length=2,
        choices=LevelType.choices,
        verbose_name='Тип уровня'
    )
    exp_reward = models.PositiveIntegerField(
        verbose_name='Награда опыта',
        default=0,
        validators=[MinValueValidator(0)],
    )
    coins_reward = models.PositiveIntegerField(
        verbose_name='Награда монет',
        default=0,
        validators=[MinValueValidator(0)],
    )
    slug = models.SlugField(
        "URL",
        max_length=250,
        unique=True,
        null=False,
        blank=True,
        editable=True,
    )
    
    class Meta:
        verbose_name = 'Уровень'
        verbose_name_plural = 'Уровни'
        ordering = ['location', 'type']
        constraints = [
            models.CheckConstraint(
                check=(models.Q(type='TH', coins_reward=0) |
                    models.Q(type__in=['TR', 'BS'], coins_reward__gte=0)) &
                    models.Q(exp_reward__gte=0),
                name='reward_constraints'
            )
        ]


    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"

    def save(self, *args, **kwargs):
        if self.type in [self.LevelType.THEORY]:
            self.coins_reward = 0
        super().save(*args, **kwargs)



class Achievements(models.Model):
    title = models.CharField(
        verbose_name="Достижения",
        max_length=100,
    )
    desc = models.TextField(
        verbose_name="Описание достижения",
    )
    icon_url = models.URLField(
        verbose_name="Ссылка на изображение",
        max_length=255,
        blank=True,
        null=True,
    )
    condition_json = models.JSONField(
        verbose_name="Условия получения",
        default=dict,
    )

    class Meta:
        verbose_name = 'Достижение'
        verbose_name_plural = 'Достижение'

    def __str__(self):
        return self.title


class UserAchievements(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='achievements')
    achievement = models.ForeignKey('Achievements', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Достижение пользователя'
        verbose_name_plural = 'Достижения пользователей'
    

class UserProgress(models.Model):
    user = models.ForeignKey('CustomUser', on_delete=models.CASCADE, related_name='progress')
    level = models.ForeignKey('Levels', on_delete=models.CASCADE)
    status = models.CharField(max_length=50)

    class Meta:
        verbose_name = 'Прогресс пользователя'
        verbose_name_plural = 'Прогресс пользователей'


class Question(models.Model):
    text = models.TextField()
    translation = models.TextField(verbose_name="Перевод", blank=True, null=True)

    class Meta:
        verbose_name = 'Вопрос'
        verbose_name_plural = 'Вопросы'

    def __str__(self):
        return self.text


class Answer(models.Model):
    question = models.ForeignKey('Question', on_delete=models.CASCADE, related_name='answers')
    text = models.TextField()
    is_correct = models.BooleanField()

    class Meta:
        verbose_name = 'Ответ'
        verbose_name_plural = 'Ответы'


class LevelQuestion(models.Model):
    level = models.ForeignKey('Levels', on_delete=models.CASCADE, related_name='level_questions')
    question = models.ForeignKey('Question', on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0, verbose_name='Порядок')

    class Meta:
        verbose_name = 'Вопрос уровня'
        verbose_name_plural = 'Вопросы уровней'
        ordering = ['order']  # порядок отображения вопросов
        unique_together = ('level', 'question')  # один и тот же вопрос — один раз на уровне
    
    def __str__(self):
        return f"{self.level.title} → {self.order + 1}. {self.question.text[:30]}"


class QuestionImage(models.Model):
    question = models.ForeignKey('Question', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='question_images/', blank=True, null=True)

    class Meta:
        verbose_name = 'Изображение к вопросу'
        verbose_name_plural = 'Изображения к вопросам'

class AnswerImage(models.Model):
    answer = models.ForeignKey('Answer', on_delete=models.CASCADE, related_name='images')
    image = models.ImageField(upload_to='answer_images/', blank=True, null=True)

    class Meta:
        verbose_name = 'Изображение к ответу'
        verbose_name_plural = 'Изображения к ответам'


class Boss(models.Model):
    level = models.ForeignKey('Levels', on_delete=models.CASCADE, related_name='boss')
    boss_name = models.CharField(max_length=100)
    desc = models.TextField(blank=True)
    image         = models.ImageField(
        upload_to='boss_images/',
        blank=True,               
        null=True,
        verbose_name='Изображение'
    )
    hp            = models.PositiveIntegerField(
        default=1,
        verbose_name='Максимальное HP'
    )
    reward_exp = models.PositiveIntegerField(default=0)
    reward_coins = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = 'Босс'
        verbose_name_plural = 'Боссы'
    
    def __str__(self):
        return self.boss_name

    # удобный генератор сегментов для шаблона
    def hp_segments(self):
        return range(self.hp)



class Word(models.Model):
    word = models.CharField(max_length=100)
    translation = models.CharField(max_length=100)
    category = models.CharField(max_length=100)

    class Meta:
        verbose_name = 'Слово'
        verbose_name_plural = 'Слова'

class BossWord(models.Model):
    boss = models.ForeignKey('Boss', on_delete=models.CASCADE)
    word = models.ForeignKey('Word', on_delete=models.CASCADE)

    class Meta:
        verbose_name = 'Слово босса'
        verbose_name_plural = 'Слова боссов'

