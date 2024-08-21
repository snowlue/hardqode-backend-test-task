from decimal import Decimal

from courses.models import Course, Group
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.db import models


class CustomUser(AbstractUser):
    """Кастомная модель пользователя - студента."""

    email = models.EmailField(verbose_name='Адрес электронной почты', max_length=250, unique=True)
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = (
        'username',
        'first_name',
        'last_name',
        'password',
    )

    group = models.ManyToManyField(Group)

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
        ordering = ('-id',)

    def save(self, *args, **kwargs):
        if not self.pk:
            super().save(*args, **kwargs)
            return create_user_balance(self)
        super().save(*args, **kwargs)

    def __str__(self):
        return self.get_full_name()


class Balance(models.Model):
    """Модель баланса пользователя."""

    user = models.OneToOneField(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='balance',
        verbose_name='Пользователь',
    )

    amount = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=Decimal('1000.00'),
        verbose_name='Баланс',
    )

    class Meta:
        verbose_name = 'Баланс'
        verbose_name_plural = 'Балансы'
        ordering = ('-id',)

    def clean(self):
        if self.amount < 0:
            raise ValidationError('Баланс не может быть отрицательным')

    def save(self, *args, **kwargs):
        self.full_clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.user.username} - {self.amount}'


def create_user_balance(user: CustomUser):
    return Balance.objects.create(user=user)


class Subscription(models.Model):
    """Модель подписки пользователя на курс."""

    user = models.ForeignKey(
        CustomUser,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Пользователь',
    )

    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='subscriptions',
        verbose_name='Курс',
    )

    start_date = models.DateTimeField(
        auto_now_add=True,
        verbose_name='Дата начала подписки',
    )

    class Meta:
        verbose_name = 'Подписка'
        verbose_name_plural = 'Подписки'
        ordering = ('-id',)
        unique_together = ('user', 'course')

    def __str__(self):
        return f'{self.user.username} - {self.course.title}'
