from django.db import models
from django.contrib.auth.models import BaseUserManager, AbstractBaseUser, PermissionsMixin
from django.core.validators import MinValueValidator


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email должен быть указан")
        email = self.normalize_email(email)

        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(seld, email, password=None, **extra_fields):
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
        max_length='255',
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

    
    class Meta:
        verbose_name = 'Уровень'
        verbose_name_plural = 'Уровни'
        ordering = ['location', 'type']
        constraints = [
            models.CheckConstraint(
                check=models.Q(
                    # Опыт всегда >= 0
                    exp_reward__gte=0,
                    coins_reward=0 if models.Q(type__in=['TH']) else models.Q(coins_reward__gte=0)
                ),
                name='reward_constraints'
            )
        ]

    def __str__(self):
        return f"{self.title} ({self.get_type_display()})"

    def save(self, *args, **kwargs):
        # Автоматическая проверка наград при сохранении
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
    











'''class SkinType(models.TextChoices):
class Skins(models.Model):
    name = models.CharField(
        verbose_name="Название скина",
        max_length=100,
    )
    desc = models.TextField(
        verbose_name="Описание",
        blank=True,
    )
    image_url = models.URLField(
        verbose_name="Ссылка на изображение",
        max_length=255,
    )
    type()'''
