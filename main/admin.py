import os
from django.utils.html import format_html
from django.contrib import admin
from django.core.files.storage import default_storage
from django.utils.safestring import mark_safe
from .models import Organization, Location, Department, Position, Employee, EmployeeHistory, EquipmentType, \
    Manufacturer, Equipment, Document, DocumentType, LinuxCategory, LinuxCommand, LinuxCheatsheet


@admin.register(Organization)
class OrganizationAdmin(admin.ModelAdmin):
    list_display = ('name', 'inn', 'is_head', 'address', 'created', 'updated')
    list_filter = ('is_head', 'created', 'updated')
    search_fields = ('name', 'inn')
    ordering = ['name']
    fieldsets = (
        (None, {
            'fields': ('name', 'inn', 'address')
        }),
        ('Настройки', {
            'fields': ('is_head',)
        }),
    )
    readonly_fields = ('created', 'updated')

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.order_by('name')

    def save_model(self, request, obj, form, change):
        if obj.is_head:
            # Снимаем флаг is_head с других организаций
            Organization.objects.filter(is_head=True).exclude(pk=obj.pk).update(is_head=False)
        super().save_model(request, obj, form, change)


@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ('code', 'address', 'created', 'updated')
    list_filter = ('created', 'updated')
    search_fields = ('code', 'address')
    ordering = ['code']


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ('name', 'organization', 'created', 'updated')
    list_filter = ('organization', 'created', 'updated')
    search_fields = ('name', 'organization__name')
    ordering = ['name']


@admin.register(Position)
class PositionAdmin(admin.ModelAdmin):
    list_display = ('name', 'created', 'updated')
    search_fields = ('name',)
    ordering = ['name']


@admin.register(EmployeeHistory)
class EmployeeHistoryAdmin(admin.ModelAdmin):
    list_display = (
        'employee_short',
        'department',
        'position',
        'location_code',
        'start_date',
        'end_date',
        'is_active',
        'reason'
    )
    list_filter = ('is_active', 'department', 'position', 'start_date')
    search_fields = (
        'employee__last_name',
        'employee__first_name',
        'employee__login',
        'reason'
    )
    autocomplete_fields = ('employee', 'department', 'position', 'location')
    readonly_fields = ('created', 'updated')
    ordering = ('-start_date',)

    def employee_short(self, obj):
        emp = obj.employee
        second_initial = f"{emp.second_name[0]}." if emp.second_name else ""
        return f"{emp.last_name} {emp.first_name[0]}.{second_initial}"
    employee_short.short_description = 'Сотрудник'
    employee_short.admin_order_field = 'employee__last_name'

    def location_code(self, obj):
        return obj.location.code if obj.location else "-"
    location_code.short_description = 'Код объекта'

    fieldsets = (
        ('Основное', {
            'fields': (
                'employee',
                ('department', 'position', 'location'),
                ('start_date', 'end_date'),
                'is_active',
                'reason'
            )
        }),
        ('Служебное', {
            'fields': ('created', 'updated'),
            'classes': ('collapse',)
        }),
    )

    def save_model(self, request, obj, form, change):
        obj.full_clean()  # активирует вашу валидацию (is_active, даты и т.д.)
        super().save_model(request, obj, form, change)


# Inline для истории внутри карточки сотрудника
class EmployeeHistoryInline(admin.TabularInline):
    model = EmployeeHistory
    extra = 0
    fields = ('department', 'position', 'location', 'start_date', 'end_date', 'is_active', 'reason')
    autocomplete_fields = ('department', 'position', 'location')
    readonly_fields = ('created', 'updated')
    show_change_link = True  # позволяет перейти к полной записи

    # Опционально: подсветка активной записи
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('department', 'position', 'location')


# Обновите EmployeeAdmin: добавьте inline
@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = ('post_photo','last_name', 'first_name', 'second_name', 'login', 'department', 'position', 'organization', 'kabinet', 'phone', 'location_code', 'available', 'created')
    list_filter = ('available', 'department', 'position', 'department__organization', 'created', 'updated')
    search_fields = ('first_name', 'last_name', 'login', 'department__name', 'position__name')
    list_select_related = ('department', 'department__organization', 'position')
    ordering = ['-created']
    fieldsets = (
        ('Персональные данные', {
            'fields': ('post_photo','last_name', 'first_name', 'second_name', 'email', 'image')
        }),
        ('Учётные данные', {
            'fields': ('login',)
        }),
        ('Место работы', {
            'fields': ('department', 'position', 'location', 'kabinet', 'phone')
        }),
        ('Статус', {
            'fields': ('available',)
        }),
    )
    readonly_fields = ('created', 'updated', 'post_photo')
    inlines = [EmployeeHistoryInline]

    def organization(self, obj):
        return obj.department.organization.name if obj.department.organization else '-'
    organization.short_description = 'Организация'
    organization.admin_order_field = 'department__organization__name'

    def location_code(self, obj):
        """Возвращает код объекта из связанной модели Location"""
        return obj.location.code if obj.location else '-'

    location_code.short_description = 'Код объекта'  # Заголовок колонки в админке

    @admin.display(description="Изображение")
    def post_photo(self, employee):
        if employee.image:
            return mark_safe(f"<img src='{employee.image.url}' width=50 height=50 style='object-fit: cover; border-radius: 10px; border: 1px solid #cccccc;' />")
        return "Без фото"

    def save_model(self, request, obj, form, change):
        # Если объект уже существует и изображение было изменено
        if change:
            old_image = Employee.objects.filter(pk=obj.pk).first()
            if old_image and old_image.image and obj.image and old_image.image != obj.image:
                if default_storage.exists(old_image.image.path):
                    default_storage.delete(old_image.image.path)
        super().save_model(request, obj, form, change)

    def delete_model(self, request, obj):
        # Удаление изображения с диска при удалении сотрудника
        if obj.image and default_storage.exists(obj.image.path):
            default_storage.delete(obj.image.path)
        super().delete_model(request, obj)


@admin.register(EquipmentType)
class EquipmentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'created', 'updated')
    search_fields = ('name',)


@admin.register(Manufacturer)
class ManufacturerAdmin(admin.ModelAdmin):
    list_display = ('name', 'created', 'updated')
    search_fields = ('name',)


@admin.register(Equipment)
class EquipmentAdmin(admin.ModelAdmin):
    list_display = (
        'type', 'manufacturer', 'model', 'serial_number',
        'inventory_number', 'status', 'location', 'responsible',
        'warranty_until', 'created'
    )
    list_filter = (
        'type', 'manufacturer', 'status', 'year_of_release',
        'warranty_until', 'location', 'created'
    )
    search_fields = (
        'model', 'serial_number', 'inventory_number',
        'network_name', 'comment'
    )
    readonly_fields = ('created', 'updated', 'photo_preview')  # ← добавлено photo_preview
    fieldsets = (
        ('Общее', {
            'fields': ('type', 'manufacturer', 'model', 'serial_number', 'inventory_number', 'photo')  # ← добавлено photo
        }),
        ('Гарантия и дата', {
            'fields': ('year_of_release', 'warranty_until')
        }),
        ('Статус и местоположение', {
            'fields': ('status', 'location', 'responsible', 'network_name')
        }),
        ('Комментарий', {
            'fields': ('comment',)
        }),
    )
    autocomplete_fields = ('responsible', 'location')

    def photo_preview(self, obj):
        if obj.photo:
            return mark_safe(
                f'<img src="{obj.photo.url}" '
                f'style="max-width: 300px; max-height: 300px; border: 1px solid #ddd; border-radius: 4px;">'
            )
        return "Нет фотографии"
    photo_preview.short_description = "Фотография оборудования"


@admin.register(DocumentType)
class DocumentTypeAdmin(admin.ModelAdmin):
    list_display = ('name', 'created')
    search_fields = ('name',)
    ordering = ['name']


@admin.register(Document)
class DocumentAdmin(admin.ModelAdmin):
    list_display = ('name', 'employee_short', 'type', 'file_link', 'is_active', 'created')
    list_filter = ('type', 'is_active', 'created')
    search_fields = ('name', 'employee__last_name', 'employee__first_name')
    autocomplete_fields = ('employee', 'type')

    def employee_short(self, obj):
        return f"{obj.employee.last_name} {obj.employee.first_name[0]}."
    employee_short.short_description = 'Сотрудник'

    def file_link(self, obj):
        if obj.file:
            return mark_safe(f'<a href="{obj.file.url}" target="_blank">📄 Открыть</a>')
        return "—"
    file_link.short_description = 'Файл'


class LinuxCommandInline(admin.TabularInline):
    model = LinuxCommand
    extra = 1
    fields = ('command', 'description', 'difficulty', 'order')
    ordering = ('order',)


@admin.register(LinuxCategory)
class LinuxCategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'icon', 'order', 'command_count', 'created')
    list_editable = ('order',)
    search_fields = ('name', 'description')
    inlines = [LinuxCommandInline]

    def command_count(self, obj):
        return obj.commands.count()

    command_count.short_description = 'Количество команд'


@admin.register(LinuxCommand)
class LinuxCommandAdmin(admin.ModelAdmin):
    list_display = ('command', 'category', 'difficulty_display', 'is_favorite', 'views', 'order')
    list_filter = ('category', 'difficulty', 'is_favorite', 'created')
    search_fields = ('command', 'description', 'tags')
    list_editable = ('order', 'is_favorite')
    fieldsets = (
        ('Основное', {
            'fields': ('command', 'description', 'category', 'difficulty', 'tags')
        }),
        ('Детали', {
            'fields': ('usage', 'options', 'examples'),
            'classes': ('collapse',)
        }),
        ('Дополнительно', {
            'fields': ('is_favorite', 'order', 'views')
        })
    )

    def difficulty_display(self, obj):
        colors = {
            'beginner': 'green',
            'intermediate': 'orange',
            'advanced': 'red'
        }
        color = colors.get(obj.difficulty, 'gray')
        return format_html(
            '<span style="color: {}; font-weight: bold;">{}</span>',
            color,
            obj.get_difficulty_display()
        )

    difficulty_display.short_description = 'Сложность'


@admin.register(LinuxCheatsheet)
class LinuxCheatsheetAdmin(admin.ModelAdmin):
    list_display = ('title', 'is_published', 'views', 'download_count', 'created')
    list_filter = ('is_published', 'created', 'categories')
    search_fields = ('title', 'description', 'content')
    filter_horizontal = ('categories', 'commands')
    fieldsets = (
        ('Основное', {
            'fields': ('title', 'description', 'content', 'is_published')
        }),
        ('Связи', {
            'fields': ('categories', 'commands'),
            'classes': ('collapse',)
        }),
        ('Статистика', {
            'fields': ('views', 'download_count')
        })
    )