from api.v1.serializers.course_serializer import CourseSerializer
from django.contrib.auth import get_user_model
from djoser.serializers import UserSerializer
from rest_framework import serializers
from users.models import Subscription

User = get_user_model()


class CustomUserSerializer(UserSerializer):
    """Сериализатор пользователей."""

    class Meta:
        model = User
        fields = ('id', 'username', 'email', 'first_name', 'last_name')


class SubscriptionSerializer(serializers.ModelSerializer):
    """Сериализатор подписки."""

    user = CustomUserSerializer(read_only=True)
    course = CourseSerializer(read_only=True)

    class Meta:
        model = Subscription
        fields = ('course', 'user', 'start_date')
