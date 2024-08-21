from courses.models import Course, Group, Lesson
from django.contrib.auth import get_user_model
from django.db.models import Avg, Count
from rest_framework import serializers
from users.models import Subscription

User = get_user_model()


class LessonSerializer(serializers.ModelSerializer):
    """Список уроков."""

    course = serializers.StringRelatedField(read_only=True)

    class Meta:
        model = Lesson
        fields = ('title', 'link', 'course')


class CreateLessonSerializer(serializers.ModelSerializer):
    """Создание уроков."""

    class Meta:
        model = Lesson
        fields = ('title', 'link', 'course')


class StudentSerializer(serializers.ModelSerializer):
    """Студенты курса."""

    class Meta:
        model = User
        fields = (
            'first_name',
            'last_name',
            'email',
        )


class GroupSerializer(serializers.ModelSerializer):
    """Список групп."""

    course_title = serializers.CharField(source='course.title', read_only=True)
    user_count = serializers.SerializerMethodField()

    class Meta:
        model = Group
        fields = ('id', 'title', 'course_title', 'user_count')

    def get_user_count(self, obj):
        """Возвращает количество пользователей в группе."""
        return obj.customuser_set.count()


class CreateGroupSerializer(serializers.ModelSerializer):
    """Создание групп."""

    class Meta:
        model = Group
        fields = (
            'title',
            'course',
        )


class MiniLessonSerializer(serializers.ModelSerializer):
    """Список названий уроков для списка курсов."""

    class Meta:
        model = Lesson
        fields = ('title',)


class CourseSerializer(serializers.ModelSerializer):
    """Список курсов."""

    lessons = MiniLessonSerializer(many=True, read_only=True)
    lessons_count = serializers.SerializerMethodField(read_only=True)
    students_count = serializers.SerializerMethodField(read_only=True)
    groups_filled_percent = serializers.SerializerMethodField(read_only=True)
    demand_course_percent = serializers.SerializerMethodField(read_only=True)

    def get_lessons_count(self, obj):
        """Количество уроков в курсе."""
        return obj.lessons.count()

    def get_students_count(self, obj):
        """Общее количество студентов на курсе."""
        return Subscription.objects.filter(course=obj).count()

    def get_groups_filled_percent(self, obj):
        """Процент заполнения групп, если в группе максимум 30 чел.."""
        max_users_in_group = 30
        groups = Group.objects.filter(course=obj).annotate(student_count=Count('customuser'))
        avg_users_in_group = groups.aggregate(avg_students=Avg('student_count'))['avg_students']

        if avg_users_in_group is None:
            return 0

        return (avg_users_in_group / max_users_in_group) * 100

    def get_demand_course_percent(self, obj):
        """Процент приобретения курса."""
        total_users = User.objects.count()
        if total_users == 0:
            return 0
        subscriptions_count = Subscription.objects.filter(course=obj).count()
        return (subscriptions_count / total_users) * 100

    class Meta:
        model = Course
        fields = (
            'id',
            'author',
            'title',
            'start_date',
            'price',
            'lessons_count',
            'lessons',
            'demand_course_percent',
            'students_count',
            'groups_filled_percent',
        )


class CreateCourseSerializer(serializers.ModelSerializer):
    """Создание курсов."""

    class Meta:
        model = Course
        fields = '__all__'
