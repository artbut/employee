import os
import re
import uuid
from django.core.exceptions import ValidationError
from django.db import models


def get_employee_image_path(instance, filename):
    """Генерация пути с датой и UUID, чтобы избежать конфликтов имён файлов"""
    ext = filename.split('.')[-1]
    filename = f"{uuid.uuid4().hex}.{ext}"
    # Используем текущее время, если объект ещё не сохранён
    from django.utils import timezone
    created = instance.created or timezone.now()
    return f"employee/{created.strftime('%Y/%m/%d')}/{filename}"


def validate_image_file(value):
    # Проверка размера
    filesize = value.size
    max_size = 2 * 1024 * 1024  # 2MB
    if filesize > max_size:
        raise ValidationError(f'Размер файла не должен превышать 2 МБ. Текущий размер: {filesize / 1024 / 1024:.1f} МБ.')

    # Проверка расширения
    ext = os.path.splitext(value.name)[1].lower()
    allowed_extensions = ['.jpg', '.jpeg', '.png', '.gif', '.webp']
    if ext not in allowed_extensions:
        raise ValidationError(f'Недопустимое расширение файла: {ext}. Допустимые: {", ".join(allowed_extensions)}')


def validate_login(value):
    """Валидатор для логина в формате 0000-00-000 (всего 11 символов)"""
    if not re.match(r'^\d{4}-\d{2}-\d{3}$', value):
        raise ValidationError('Логин должен быть в формате XXXX-XX-XXX, например: 1234-56-789.')


def validate_location_code(value):
    if not re.match(r'^\d{5}$', value):
        raise ValidationError('Код объекта должен содержать ровно 5 цифр, например: 22256.')


def validate_organization_inn(value):
    if not re.match(r'^\d{10}$', value):
        raise ValidationError('ИНН содержит 10 цифр, например: 1234567890.')


class Organization(models.Model):
    """Модель головной организации"""
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(
        max_length=255,
        verbose_name='Название организации',
        help_text='Например: ООО "Ромашка"'
    )
    inn = models.CharField(
        max_length=10,
        verbose_name='ИНН',
        unique=True,
        validators=[validate_organization_inn],
        help_text='ИНН организации (10 цифр)'
    )
    address = models.TextField(
        verbose_name='Юридический адрес',
        blank=True,
        null=True
    )
    is_head = models.BooleanField(
        default=True,
        verbose_name='Головная организация',
        help_text='Отметьте, если это головная организация'
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'organization'
        verbose_name = 'Организация'
        verbose_name_plural = 'Организации'
        ordering = ['name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if self.is_head:
            Organization.objects.filter(is_head=True).exclude(pk=self.pk).update(is_head=False)
        super().save(*args, **kwargs)


class Location(models.Model):
    """Модель для хранения адресов и кодов объектов"""
    code = models.CharField(
        max_length=5,
        unique=True,
        verbose_name='Код объекта',
        validators=[validate_location_code],
        help_text='5-значный код объекта, например: 22256'
    )
    address = models.CharField(
        max_length=255,
        verbose_name='Адрес',
        help_text='Полный адрес места нахождения, например: г. Краснодар, ул. Ленина, 1'
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'location'
        verbose_name = 'Место нахождения'
        verbose_name_plural = 'Места нахождения'
        ordering = ['code']

    def __str__(self):
        return f"{self.code} — {self.address}"


class Department(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, verbose_name='Название подразделения', unique=True)
    organization = models.ForeignKey(
        Organization,
        on_delete=models.PROTECT,
        verbose_name='Организация',
        related_name='departments',
        related_query_name='dept'
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'department'
        ordering = ['name']
        verbose_name = 'Подразделение'
        verbose_name_plural = 'Подразделения'

    def __str__(self):
        return self.name


class Position(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, verbose_name='Название должности')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'position'
        ordering = ['name']
        verbose_name = 'Должность'
        verbose_name_plural = 'Должности'
        unique_together = ('name',)

    def __str__(self):
        return self.name


class Employee(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    first_name = models.CharField(max_length=100, verbose_name='Имя')
    last_name = models.CharField(max_length=100, verbose_name='Фамилия')
    second_name = models.CharField(max_length=100, verbose_name='Отчество', blank=True, default='')
    email = models.EmailField(max_length=50, unique=True)
    image = models.ImageField(upload_to=get_employee_image_path,
                              null=True,
                              blank=True,
                              validators=[validate_image_file])
    login = models.CharField(
        max_length=11,
        verbose_name='Логин',
        unique=True,
        validators=[validate_login]
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        verbose_name='Подразделение',
        related_name='employees',
        related_query_name='emp'
    )
    position = models.ForeignKey(
        Position,
        on_delete=models.PROTECT,
        verbose_name='Должность',
        related_name='employees',
        related_query_name='position_emp'
    )
    location = models.ForeignKey(
        Location,
        on_delete=models.PROTECT,
        verbose_name='Место нахождения',
        related_name='employees',
        related_query_name='loc_emp',
        help_text='Код и адрес объекта, где работает сотрудник'
    )
    available = models.BooleanField(default=True, verbose_name='Доступен')
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'employee'
        ordering = ['-created']
        verbose_name = 'Сотрудник'
        verbose_name_plural = 'Сотрудники'

    def __str__(self):
        last_initial = self.last_name[0] if self.last_name else ''
        second_initial = self.second_name[0] if self.second_name else ''
        return f'{self.first_name} {last_initial}.{second_initial}.'.strip(' .')

    def get_absolute_url(self):
        return f'/employee/{self.id}/'