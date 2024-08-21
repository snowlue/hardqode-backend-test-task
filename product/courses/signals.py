from django.db.models import Count
from django.db.models.signals import post_save
from django.dispatch import receiver
from users.models import Subscription

from courses.models import Group


@receiver(post_save, sender=Subscription)
def post_save_subscription(sender, instance: Subscription, created, **kwargs):
    """Распределение нового студента в группу курса."""

    if created:
        groups = Group.objects.filter(course=instance.course)

        if not groups.exists():
            for i in range(10):
                Group.objects.create(course=instance.course, title=f'Группа №{instance.course.pk}{i}')
            groups = Group.objects.filter(course=instance.course)

            best_group = Group.objects.annotate(user_count=Count('customuser')).order_by('user_count').first()

        instance.user.group.add(best_group)
        instance.user.save()
