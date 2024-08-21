from api.v1.permissions import IsStudentOrIsAdmin, ReadOnlyOrIsAdmin
from api.v1.serializers.course_serializer import (
    CourseSerializer,
    CreateCourseSerializer,
    CreateGroupSerializer,
    CreateLessonSerializer,
    GroupSerializer,
    LessonSerializer,
)
from courses.models import Course
from django.db import transaction
from django.shortcuts import get_object_or_404
from rest_framework import permissions, status, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response
from users.models import Balance, Subscription


class LessonViewSet(viewsets.ModelViewSet):
    """Уроки."""

    permission_classes = (IsStudentOrIsAdmin,)

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return LessonSerializer
        return CreateLessonSerializer

    def perform_create(self, serializer):
        course = get_object_or_404(Course, id=self.kwargs.get('course_id'))
        serializer.save(course=course)

    def get_queryset(self):
        course = get_object_or_404(Course, id=self.kwargs.get('course_id'))
        return course.lessons.all()  # type: ignore


class GroupViewSet(viewsets.ModelViewSet):
    """Группы."""

    permission_classes = (permissions.IsAdminUser,)

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return GroupSerializer
        return CreateGroupSerializer

    def perform_create(self, serializer):
        course = get_object_or_404(Course, id=self.kwargs.get('course_id'))
        serializer.save(course=course)

    def get_queryset(self):
        course = get_object_or_404(Course, id=self.kwargs.get('course_id'))
        return course.groups.all()  # type: ignore


class CourseViewSet(viewsets.ModelViewSet):
    """Курсы"""

    queryset = Course.objects.filter(is_available=True).distinct()
    permission_classes = (ReadOnlyOrIsAdmin,)

    def get_serializer_class(self):
        if self.action in ['list', 'retrieve']:
            return CourseSerializer
        return CreateCourseSerializer

    @action(methods=['post'], detail=True, permission_classes=(permissions.IsAuthenticated,))
    def pay(self, request, pk):
        """Покупка доступа к курсу (подписка на курс)."""

        course = get_object_or_404(Course, pk=pk)
        user = request.user

        if Subscription.objects.filter(user=user, course=course).exists():
            return Response({'detail': 'Вы уже подписаны на этот курс.'}, status=status.HTTP_400_BAD_REQUEST)
        if not course.is_available:
            return Response({'detail': 'Данный курс не доступен для покупки.'}, status=status.HTTP_400_BAD_REQUEST)

        balance = get_object_or_404(Balance, user=user)
        if balance.amount < course.price:
            return Response({'detail': 'Недостаточно бонусов для покупки курса.'}, status=status.HTTP_400_BAD_REQUEST)

        # Оформление подписки и обновление баланса в одной транзакции для целостности данных
        with transaction.atomic():
            Subscription.objects.create(user=user, course=course)
            balance.amount -= course.price
            balance.save()

        return Response({'detail': 'Подписка на курс успешно оформлена.'}, status=status.HTTP_201_CREATED)
