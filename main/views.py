from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from .models import Employee, Department, Equipment, EquipmentType, LinuxCategory, LinuxCommand, LinuxCheatsheet
from django.db.models import Q, Count
from .utils import apply_employee_filters_and_ordering
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
import os
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from barcode import Code128
from barcode.writer import ImageWriter
from io import BytesIO
import base64
from collections import defaultdict


def get_equipment_queryset():
    return Equipment.objects.select_related(
        'type', 'manufacturer', 'location', 'responsible__department'
    ).order_by('-created')


def department_list(request):
    departments = Department.objects.select_related('organization').annotate(
        employee_count=Count('emp')
    ).order_by('name')

    equipment_types = EquipmentType.objects.all().order_by('name')

    return render(request, 'department_list.html', {
        'departments': departments,
        'equipment_types': equipment_types
    })


def equipment_main(request):
    equipment_types = EquipmentType.objects.all().order_by('name')
    return render(request, 'equipment_main.html', {'equipment_types': equipment_types})


@login_required
def employees_by_department(request, id):
    department = get_object_or_404(Department, id=id)

    # Только сотрудники этого подразделения
    employee_list = Employee.objects.select_related('position', 'location').filter(department=department)

    # Параметры из запроса
    search_query = request.GET.get('search', '').strip()
    order_param = request.GET.get('order', '')

    # Применяем фильтрацию и сортировку
    employee_list = apply_employee_filters_and_ordering(employee_list, search_query, order_param)

    # Пагинация
    paginator = Paginator(employee_list, 12)
    page_number = request.GET.get('page')
    employees = paginator.get_page(page_number)

    context = {
        'employees': employees,
        'department': department,
        'search': search_query,
    }
    return render(request, 'employee_list.html', context)


@login_required
def employee_list(request):
    # Начинаем с полного списка сотрудников
    employee_list = Employee.objects.select_related('department', 'position', 'location')

    # Получаем параметры из запроса
    search_query = request.GET.get('search', '').strip()
    order_param = request.GET.get('order', '')

    # Применяем фильтрацию и сортировку
    employee_list = apply_employee_filters_and_ordering(employee_list, search_query, order_param)

    # Пагинация
    paginator = Paginator(employee_list, 12)
    page_number = request.GET.get('page')
    employees = paginator.get_page(page_number)

    context = {
        'employees': employees,
        'search': search_query,
    }
    return render(request, 'employee_list.html', context)


@login_required
def employee_detail(request, id):
    employee = get_object_or_404(
        Employee.objects.select_related('department', 'position', 'location'),
        id=id
    )

    # === Документы ===
    documents = employee.documents.filter(is_active=True).select_related('type').order_by('type__name', '-created')
    grouped_docs = defaultdict(list)
    no_type_docs = []

    for doc in documents:
        if doc.type:
            grouped_docs[doc.type].append(doc)
        else:
            no_type_docs.append(doc)

    sorted_groups = sorted(grouped_docs.items(), key=lambda x: x[0].name)

    # === Оборудование ===
    equipment = Equipment.objects.filter(
        responsible=employee,
        status__in=['assigned', 'temporary']  # только активные назначения
    ).select_related('type', 'manufacturer', 'location').order_by('-created')

    context = {
        'employee': employee,
        'grouped_docs': sorted_groups,
        'no_type_docs': no_type_docs,
        'equipment': equipment,  # ← добавлено
    }
    return render(request, 'employee_detail.html', context)

@login_required
def employee_history(request, id):
    employee = get_object_or_404(Employee, id=id)
    history_records = employee.history_records.select_related(
        'department', 'position', 'location'
    ).order_by('-start_date')

    context = {
        'employee': employee,
        'history_records': history_records,
    }
    return render(request, 'employee_history.html', context)


def equipment_list(request):
    query = request.GET.get('q', '').strip()
    type_id = request.GET.get('type')

    equipment_list = Equipment.objects.select_related(
        'type', 'manufacturer', 'location', 'responsible'
    ).order_by('-created')

    if type_id:
        equipment_list = equipment_list.filter(type_id=type_id)
    if query:
        equipment_list = equipment_list.filter(...)

    paginator = Paginator(equipment_list, 10)
    page_number = request.GET.get('page')
    equipment = paginator.get_page(page_number)

    return render(request, 'equipment_list.html', {
        'equipment': equipment,
        'query': query
    })


@login_required
def equipment_detail(request, id):
    equip = get_object_or_404(get_equipment_queryset(), id=id)
    return render(request, 'equipment_detail.html', {'equip': equip})


@login_required
def print_equipment_label(request, id):
    equipment = get_object_or_404(
        Equipment.objects.select_related('type', 'manufacturer', 'location'),
        id=id
    )

    # Генерация штрихкода из serial_number (или inventory_number)
    barcode_data = equipment.serial_number or equipment.inventory_number or str(equipment.id)

    # Создаём штрихкод в памяти
    buffer = BytesIO()
    writer_options = {
        'module_width': 0.2,  # ширина модуля (мм)
        'module_height': 10.0,  # высота штрихкода (мм)
        'quiet_zone': 1.0,  # отступы по бокам
        'font_size': 8,  # размер шрифта под штрихкодом
        'text_distance': 3.0,  # расстояние текста от штрихкода
        'background': 'white',
        'foreground': 'black',
    }

    code128 = Code128(barcode_data, writer=ImageWriter())
    code128.write(buffer, options=writer_options)

    # Кодируем в base64 для вставки в HTML
    buffer.seek(0)
    barcode_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')

    context = {
        'equip': equipment,
        'company_name': 'Межрайонная ИФНС России № 2 по Ленинградской области',
        'barcode_base64': barcode_base64,
        'barcode_data': barcode_data,
    }
    return render(request, 'labels/equipment_label.html', context)


def linux_home(request):
    """Домашняя страница Linux шпаргалки"""
    categories = LinuxCategory.objects.prefetch_related('commands').all()
    popular_commands = LinuxCommand.objects.filter(is_favorite=True)[:10]
    recent_cheatsheets = LinuxCheatsheet.objects.filter(is_published=True)[:5]

    return render(request, 'linux_home.html', {
        'categories': categories,
        'popular_commands': popular_commands,
        'recent_cheatsheets': recent_cheatsheets,
    })

def linux_commands(request):
    """Список всех Linux команд с пагинацией"""
    commands = LinuxCommand.objects.select_related('category').all()

    # Фильтрация
    category_id = request.GET.get('category')
    if category_id:
        commands = commands.filter(category_id=category_id)

    difficulty = request.GET.get('difficulty')
    if difficulty:
        commands = commands.filter(difficulty=difficulty)

    search = request.GET.get('search')
    if search:
        commands = commands.filter(
            Q(command__icontains=search) |
            Q(description__icontains=search) |
            Q(tags__icontains=search)
        )

    # Сортировка
    sort = request.GET.get('sort', 'order')
    if sort == 'popular':
        commands = commands.order_by('-views')
    elif sort == 'new':
        commands = commands.order_by('-created')
    elif sort == 'favorite':
        commands = commands.filter(is_favorite=True).order_by('order')
    else:
        commands = commands.order_by('order', 'command')

    # Пагинация
    page = request.GET.get('page', 1)
    paginator = Paginator(commands, 20)  # 20 команд на страницу

    try:
        commands_page = paginator.page(page)
    except PageNotAnInteger:
        commands_page = paginator.page(1)
    except EmptyPage:
        commands_page = paginator.page(paginator.num_pages)

    categories = LinuxCategory.objects.all()

    # Сохраняем параметры фильтрации для пагинации
    query_params = request.GET.copy()
    if 'page' in query_params:
        del query_params['page']

    return render(request, 'linux_commands.html', {
        'commands': commands_page,
        'categories': categories,
        'difficulties': LinuxCommand.DIFFICULTY_CHOICES,
        'query_params': query_params.urlencode(),
        'total_commands': commands.count(),
        'current_sort': sort,
    })


def linux_command_detail(request, command_id):
    """Детальная информация о команде"""
    command = get_object_or_404(LinuxCommand, id=command_id)
    command.views += 1
    command.save(update_fields=['views'])

    similar_commands = LinuxCommand.objects.filter(
        category=command.category
    ).exclude(id=command_id).order_by('?')[:5]

    return render(request, 'linux_command_detail.html', {
        'command': command,
        'similar_commands': similar_commands,
    })


def linux_cheatsheets(request):
    """Список готовых шпаргалок"""
    cheatsheets = LinuxCheatsheet.objects.filter(is_published=True)

    category_id = request.GET.get('category')
    if category_id:
        cheatsheets = cheatsheets.filter(categories__id=category_id)

    return render(request, 'linux_cheatsheets.html', {
        'cheatsheets': cheatsheets,
        'categories': LinuxCategory.objects.all(),
    })


def linux_search(request):
    """Поиск Linux команд"""
    query = request.GET.get('q', '')
    commands = []

    if query:
        commands = LinuxCommand.objects.filter(
            Q(command__icontains=query) |
            Q(description__icontains=query) |
            Q(tags__icontains=query)
        ).select_related('category')[:50]

    return render(request, 'linux_search.html', {
        'commands': commands,
        'query': query,
    })


def linux_quick_reference(request):
    """Быстрая справка по основным командам"""
    basic_commands = LinuxCommand.objects.filter(difficulty='beginner')[:20]
    intermediate_commands = LinuxCommand.objects.filter(difficulty='intermediate')[:15]
    advanced_commands = LinuxCommand.objects.filter(difficulty='advanced')[:10]

    return render(request, 'linux_quick_reference.html', {
        'basic_commands': basic_commands,
        'intermediate_commands': intermediate_commands,
        'advanced_commands': advanced_commands,
    })