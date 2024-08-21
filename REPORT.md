# Отчёт о выполненном тестовом задании
### Для составителей тестового задания
Проходим по гайду для установки на локальном компьютере и на 4 шаге сталкиваемся с тем, что при выполнении миграций возникает ошибка:
```bash
ValueError: Dependency on app with no migrations: users
```
Необходимо создать миграции для `users`, поэтому выполняем команду:
```bash
python manage.py makemigrations users
```
После этого продолжаем выполнение гайда — выполняем миграции, создаём суперпользователя и запускаем проект.

Также переход по соответствующим эндпоинтам в API приводит к ошибкам в сериализаторах — во всех сериализаторах в `api/v1/serializers` необходимо прописать `fields = '__all__'` там, где `fields` не определён.

### Построение архитектуры
Отыщем сущности в проекте. Выясняем, что модели продукта, урока и группы уже заданы в `courses/models.py`, а модели пользователя, баланса и подписки — в `users/models.py`. 
1. В модели продукта `Course` уже заданы поля создателя, названия продукта, даты и времени старта. Дополним модель полем `price`, отвечающим за стоимость продукта:
    ```python
    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name='Стоимость',
    )
    ```

2. Определять то, есть ли у пользователя доступ к продукту или нет, будет модель `Subscription`. Нам необходимо полностью её прописать — это связующая таблица между пользователями и продуктами. Определим в ней поля `user`, `course` и `start_date` (сформируем это поле предварительно на случай дальнейшей необходимости), а также в мете определим уникальность пары `user` и `course` и пропишем строковое представление:
    ```python
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
    ```

3.  В модели урока `Lesson` уже заданы поля названия и ссылки на видео. Дополним модель внешним ключём `course`, который будет связывать отношением многие-к-одному с моделью `Course`:
    ```python
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='lessons',
        verbose_name='Курс',
    )
    ```

4. У нас имеется модель `Balance`, которую необходимо дополнить соответствующими полями — внешним ключом `user` на пользователя с отношением один-к-одному и полем `amount`, отвечающим за количество бонусов на балансе, c параметром `default`. Также добавим методы `clean()` и `save()` для проверки модели на отрицательное значение баланса при создании и обновлении модели:
    ```python
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
    ```

### Реализация базового сценария оплат
1. Итак, нам необходимо добавить поле `is_available` в модель `Course`, которое будет отвечать за доступность курса для пользователя. Поле будет иметь значение по умолчанию `True`:
    ```python
    is_available = models.BooleanField(
        default=True,
        verbose_name='Доступен для покупки'
    )
    ```
    Теперь модфицируем сериализатор `CourseSerializer` в `api/v1/serializers/course_serializer.py`, заполнив функцию `get_lessons_count()`, где будем считать количество уроков в курсе, используя поле `related_name='lessons'` из внешнего ключа `course` в модели `Lesson`:
    ```python
    def get_lessons_count(self, obj):
        """Количество уроков в курсе."""
        return obj.lessons.count()
    ```
    И изменим в `api/v1/views/course_view.py` вью `CourseViewSet`, чтобы возвращались только доступные к покупке курсы:
    ```python
    queryset = Course.objects.filter(is_available=True).distinct()
    ```

2. Для реализации API оплаты продукта за бонусы, нам понадобится реализовать создание баланса вместе с созданием пользователя. Модифицируем модель `CustomUser`, переопределив в ней `save()`, срабатывающий при создании и обновлении объекта этой модели:
    ```python
    def save(self, *args, **kwargs):
        if not self.pk:
            super().save(*args, **kwargs)
            return create_user_balance(self)
        super().save(*args, **kwargs)
    ```
    Теперь создадим функцию `create_user_balance()`, которая будет создавать баланс для нового пользователя:
    ```python
    def create_user_balance(user: CustomUser):
        return Balance.objects.create(user=user)
    ```
    В `CourseViewSet` находится заглушка `pay` для оплаты курса за бонусы. Добавим в неё всю логику оплаты со списанием бонусов и созданием подписки на курс через модель `Subscription`, связывающей пользователя и курс:
    ```python
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
    ```
3. Доступ к курсу открывается, т.к. мы добавляем в `Subscription` новую запись для заданных пользователя и курса.
4. Для реализации связи пользователей и групп отношением многие-ко-многим, пропишем новое поле в модели `CustomUser`:
    ```python
    group = models.ManyToManyField(Group)
    ```
    Оформим до сих пор пустую модель `Group` в `courses/models.py` полями `course` (отношение многие-к-одному для связи групп с курсом) и `title` (название группы с её номером):
    ```python
    course = models.ForeignKey(
        Course,
        on_delete=models.CASCADE,
        related_name='groups',
        verbose_name='Курс',
    )
    title = models.CharField(
        max_length=250, 
        verbose_name='Название',
    )
    ```
    Теперь откроем `courses/signals.py` — здесь содержатся сигналы, которые срабатывают при создании и обновлении моделей. Сейчас установлен пустой сигнал на модель `Subscription` — `post_save_subscription`. Добавим в него логику распределения пользователя в группы:
    ```python
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
    ```
    Здесь же прописана логика создания групп для курса, если их нет. Таким образом при появлении новой подписки на курс пользователь распределяется в одну из групп курса `№{ID курса}{номер группы 0-9}` с наименьшим количеством человек.

### Незакрытые TODO в проекте
1. В `api/v1/serializers/user_serializer.py` необходимо реализовать сериализатор подписки (который, однако, далее нигде не используется):
    ```python
    class SubscriptionSerializer(serializers.ModelSerializer):
        """Сериализатор подписки."""

        user = CustomUserSerializer(read_only=True)
        course = CourseSerializer(read_only=True)

        class Meta:
            model = Subscription
            fields = ('course', 'user', 'start_date')
    ```
2. В `api/v1/permissions.py` отмечены три TODO — я не разобрался, что требуется сделать с ними. Из названий объектов их предназначение очевидно, но `make_payments` не вписывается в контекст permissions, а требования к реализации `IsStudentOrIsAdmin` не были обозначены в задании.
3. В `api/v1/serializers/course_serializer.py` необходимо реализовать сериализатор групп:
    ```python
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
    ```
4. В `api/v1/serializers/course_serializer.py` также необходимо реализовать API для отображения статистики по продуктам — и, судя по всему, это нужно сделать с применением `Avg` и `Count`, которые были импортированы, но не были использованы (спасибо за подсказку!):
    ```python
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
    ```

-----
Весь код был полностью отформатирован с помощью `Ruff`, с помощью которого же были отсортированы импорты. Также были добавлены комментарии к коду, где это необходимо.
