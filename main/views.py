from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.utils import timezone

from .models import Employee, Department, Equipment, EquipmentType, LinuxCategory, LinuxCommand, LinuxCheatsheet
from django.db.models import Q, Count
from .utils import apply_employee_filters_and_ordering
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.conf import settings
from barcode import Code128
from barcode.writer import ImageWriter
import base64
from collections import defaultdict
import os
from django.http import HttpResponse, FileResponse
from django.shortcuts import get_object_or_404
from django.template.loader import render_to_string
from reportlab.lib.pagesizes import letter, A4
from reportlab.pdfgen import canvas
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib import colors
import tempfile
from io import BytesIO
import markdown

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

    # Поиск
    search = request.GET.get('search')
    if search:
        cheatsheets = cheatsheets.filter(
            Q(title__icontains=search) |
            Q(description__icontains=search) |
            Q(content__icontains=search)
        )

    return render(request, 'linux_cheatsheets.html', {
        'cheatsheets': cheatsheets,
        'categories': LinuxCategory.objects.all(),
    })


def download_cheatsheet(request, cheatsheet_id, format_type='pdf'):
    """Скачать шпаргалку в указанном формате"""
    cheatsheet = get_object_or_404(LinuxCheatsheet, id=cheatsheet_id, is_published=True)

    # Увеличиваем счетчик скачиваний
    cheatsheet.download_count += 1
    cheatsheet.save(update_fields=['download_count'])

    # Если файл уже существует, отдаем его
    if cheatsheet.has_file(format_type):
        file_field = getattr(cheatsheet, f'file_{format_type}')
        response = FileResponse(file_field.open(), as_attachment=True)
        response['Content-Disposition'] = f'attachment; filename="{cheatsheet.title}.{format_type}"'
        return response

    # Иначе генерируем файл на лету
    if format_type == 'pdf':
        return generate_pdf_cheatsheet(request, cheatsheet)
    elif format_type == 'txt':
        return generate_text_cheatsheet(request, cheatsheet)
    elif format_type == 'md':
        return generate_markdown_cheatsheet(request, cheatsheet)
    elif format_type == 'html':
        return generate_html_cheatsheet(request, cheatsheet)
    else:
        return HttpResponse("Unsupported format", status=400)


def generate_pdf_cheatsheet(request, cheatsheet):
    """Генерация PDF шпаргалки"""
    response = HttpResponse(content_type='application/pdf')
    filename = f"{cheatsheet.title.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    # Создаем PDF документ
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=72, leftMargin=72, topMargin=72, bottomMargin=18)

    # Стили
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        textColor=colors.HexColor('#2c3e50')
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=12,
        textColor=colors.HexColor('#34495e')
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )

    # Содержимое
    story = []

    # Заголовок
    story.append(Paragraph(cheatsheet.title, title_style))
    story.append(Spacer(1, 12))

    # Описание
    if cheatsheet.description:
        story.append(Paragraph(cheatsheet.description, normal_style))
        story.append(Spacer(1, 20))

    # Категории
    if cheatsheet.categories.exists():
        categories_text = "Категории: " + ", ".join([cat.name for cat in cheatsheet.categories.all()])
        story.append(Paragraph(categories_text, normal_style))
        story.append(Spacer(1, 20))

    # Команды
    if cheatsheet.commands.exists():
        story.append(Paragraph("Команды:", heading_style))

        # Создаем таблицу для команд
        data = [["Команда", "Описание", "Сложность"]]

        for command in cheatsheet.commands.all().order_by('order'):
            data.append([
                command.command,
                command.description[:100] + "..." if len(command.description) > 100 else command.description,
                command.get_difficulty_display()
            ])

        table = Table(data, colWidths=[100, 300, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(table)
        story.append(Spacer(1, 30))

    # Детальное описание команд
    if cheatsheet.commands.exists():
        story.append(Paragraph("Детальная информация по командам:", heading_style))
        story.append(Spacer(1, 15))

        for i, command in enumerate(cheatsheet.commands.all().order_by('order'), 1):
            # Заголовок команды
            command_title = f"{i}. {command.command}"
            story.append(Paragraph(command_title, ParagraphStyle(
                'CommandTitle',
                parent=styles['Heading3'],
                fontSize=11,
                textColor=colors.HexColor('#2980b9'),
                spaceAfter=6
            )))

            # Описание
            story.append(Paragraph(command.description, normal_style))

            # Использование
            if command.usage:
                story.append(Paragraph(f"Использование: <font face='Courier'>{command.usage}</font>", normal_style))

            # Примеры
            if command.examples:
                examples = command.examples.split('\n')
                for example in examples[:3]:  # Берем только первые 3 примера
                    if example.strip():
                        story.append(Paragraph(f"<font face='Courier'>{example.strip()}</font>",
                                               ParagraphStyle('Code', parent=normal_style,
                                                              backColor=colors.HexColor('#f8f9fa'),
                                                              leftIndent=20)))

            story.append(Spacer(1, 15))

    # Футер
    footer_text = f"Сгенерировано {timezone.now().strftime('%d.%m.%Y %H:%M')} | Скачиваний: {cheatsheet.download_count}"
    story.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1  # Центрирование
    )))

    # Собираем документ
    doc.build(story)

    # Получаем PDF из буфера
    pdf = buffer.getvalue()
    buffer.close()

    response.write(pdf)
    return response


def generate_text_cheatsheet(request, cheatsheet):
    """Генерация текстовой шпаргалки"""
    content = []
    content.append(f"=== {cheatsheet.title.upper()} ===")
    content.append("")

    if cheatsheet.description:
        content.append(cheatsheet.description)
        content.append("")

    if cheatsheet.categories.exists():
        categories = ", ".join([cat.name for cat in cheatsheet.categories.all()])
        content.append(f"Категории: {categories}")
        content.append("")

    if cheatsheet.commands.exists():
        content.append("КОМАНДЫ:")
        content.append("=" * 50)

        for i, command in enumerate(cheatsheet.commands.all().order_by('order'), 1):
            content.append(f"\n{i}. {command.command}")
            content.append(f"   Описание: {command.description}")
            content.append(f"   Сложность: {command.get_difficulty_display()}")

            if command.usage:
                content.append(f"   Использование: {command.usage}")

            if command.get_options_list():
                content.append(f"   Основные опции:")
                for opt in command.get_options_list()[:5]:
                    content.append(f"     - {opt}")

            if command.get_examples_list():
                content.append(f"   Примеры:")
                for ex in command.get_examples_list()[:3]:
                    content.append(f"     $ {ex}")

            content.append("-" * 40)

    content.append(f"\n\nСгенерировано: {timezone.now().strftime('%d.%m.%Y %H:%M')}")
    content.append(f"Скачиваний: {cheatsheet.download_count}")

    response = HttpResponse("\n".join(content), content_type='text/plain; charset=utf-8')
    filename = f"{cheatsheet.title.replace(' ', '_')}.txt"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def generate_markdown_cheatsheet(request, cheatsheet):
    """Генерация Markdown шпаргалки"""
    content = []
    content.append(f"# {cheatsheet.title}")
    content.append("")

    if cheatsheet.description:
        content.append(f"**Описание:** {cheatsheet.description}")
        content.append("")

    if cheatsheet.categories.exists():
        categories = ", ".join([f"`{cat.name}`" for cat in cheatsheet.categories.all()])
        content.append(f"**Категории:** {categories}")
        content.append("")

    if cheatsheet.commands.exists():
        content.append("## Команды")
        content.append("")

        for i, command in enumerate(cheatsheet.commands.all().order_by('order'), 1):
            content.append(f"### {i}. `{command.command}`")
            content.append("")
            content.append(f"**Описание:** {command.description}")
            content.append("")
            content.append(f"**Сложность:** {command.get_difficulty_display()}")
            content.append("")

            if command.usage:
                content.append(f"**Использование:**")
                content.append(f"```bash\n{command.usage}\n```")
                content.append("")

            if command.get_options_list():
                content.append(f"**Основные опции:**")
                for opt in command.get_options_list()[:5]:
                    content.append(f"- `{opt}`")
                content.append("")

            if command.get_examples_list():
                content.append(f"**Примеры:**")
                for ex in command.get_examples_list()[:3]:
                    content.append(f"```bash\n{ex}\n```")
                content.append("")

    content.append(f"---")
    content.append(f"*Сгенерировано: {timezone.now().strftime('%d.%m.%Y %H:%M')}*  ")
    content.append(f"*Скачиваний: {cheatsheet.download_count}*")

    response = HttpResponse("\n".join(content), content_type='text/markdown; charset=utf-8')
    filename = f"{cheatsheet.title.replace(' ', '_')}.md"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def generate_html_cheatsheet(request, cheatsheet):
    """Генерация HTML шпаргалки"""
    context = {
        'cheatsheet': cheatsheet,
        'now': timezone.now(),
        'commands': cheatsheet.commands.all().order_by('order'),
    }

    html_content = render_to_string('cheatsheet_print.html', context)

    response = HttpResponse(html_content, content_type='text/html; charset=utf-8')
    filename = f"{cheatsheet.title.replace(' ', '_')}.html"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'
    return response


def print_cheatsheet(request, cheatsheet_id):
    """Страница для печати шпаргалки"""
    cheatsheet = get_object_or_404(LinuxCheatsheet, id=cheatsheet_id, is_published=True)

    return render(request, 'cheatsheet_print.html', {
        'cheatsheet': cheatsheet,
        'commands': cheatsheet.commands.all().order_by('order'),
        'print_mode': True,
    })


def generate_custom_cheatsheet(request):
    """Генерация пользовательской шпаргалки"""
    if request.method == 'POST':
        # Получаем выбранные команды
        command_ids = request.POST.getlist('commands')
        title = request.POST.get('title', 'Моя шпаргалка Linux')
        description = request.POST.get('description', '')
        format_type = request.POST.get('format', 'pdf')

        if not command_ids:
            return HttpResponse("Выберите хотя бы одну команду", status=400)

        # Создаем временную шпаргалку
        commands = LinuxCommand.objects.filter(id__in=command_ids)

        # В зависимости от формата генерируем файл
        if format_type == 'pdf':
            return generate_custom_pdf(title, description, commands)
        elif format_type == 'txt':
            return generate_custom_text(title, description, commands)
        elif format_type == 'md':
            return generate_custom_markdown(title, description, commands)
        else:
            return HttpResponse("Неверный формат", status=400)
        
        # GET запрос - показываем форму выбора с пагинацией
    categories = LinuxCategory.objects.all()
    commands_list = LinuxCommand.objects.select_related('category').all()

        # Пагинация
    page = request.GET.get('page', 1)
    paginator = Paginator(commands_list, 20)  # 20 команд на страницу

    try:
        commands = paginator.page(page)
    except PageNotAnInteger:
        commands = paginator.page(1)
    except EmptyPage:
        commands = paginator.page(paginator.num_pages)

    return render(request, 'generate_cheatsheet.html', {
        'categories': categories,
        'commands': commands,
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


def generate_custom_pdf(title, description, commands, story=None, cheatsheet=None):
    """Генерация PDF для пользовательской шпаргалки"""
    response = HttpResponse(content_type='application/pdf')
    filename = f"{title.replace(' ', '_')}.pdf"
    response['Content-Disposition'] = f'attachment; filename="{filename}"'

    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4)

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=16,
        spaceAfter=30,
        textColor=colors.HexColor('#2c3e50')
    )

    heading_style = ParagraphStyle(
        'CustomHeading',
        parent=styles['Heading2'],
        fontSize=12,
        spaceAfter=12,
        textColor=colors.HexColor('#34495e')
    )

    normal_style = ParagraphStyle(
        'CustomNormal',
        parent=styles['Normal'],
        fontSize=10,
        spaceAfter=6
    )

    # Содержимое
    story = []

    # Заголовок
    story.append(Paragraph(cheatsheet.title, title_style))
    story.append(Spacer(1, 12))

    # Описание
    if cheatsheet.description:
        story.append(Paragraph(cheatsheet.description, normal_style))
        story.append(Spacer(1, 20))

    # Категории
    if cheatsheet.categories.exists():
        categories_text = "Категории: " + ", ".join([cat.name for cat in cheatsheet.categories.all()])
        story.append(Paragraph(categories_text, normal_style))
        story.append(Spacer(1, 20))

    # Команды
    if cheatsheet.commands.exists():
        story.append(Paragraph("Команды:", heading_style))

        # Создаем таблицу для команд
        data = [["Команда", "Описание", "Сложность"]]

        for command in cheatsheet.commands.all().order_by('order'):
            data.append([
                command.command,
                command.description[:100] + "..." if len(command.description) > 100 else command.description,
                command.get_difficulty_display()
            ])

        table = Table(data, colWidths=[100, 300, 80])
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#34495e')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 9),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))

        story.append(table)
        story.append(Spacer(1, 30))

    # Детальное описание команд
    if cheatsheet.commands.exists():
        story.append(Paragraph("Детальная информация по командам:", heading_style))
        story.append(Spacer(1, 15))

        for i, command in enumerate(cheatsheet.commands.all().order_by('order'), 1):
            # Заголовок команды
            command_title = f"{i}. {command.command}"
            story.append(Paragraph(command_title, ParagraphStyle(
                'CommandTitle',
                parent=styles['Heading3'],
                fontSize=11,
                textColor=colors.HexColor('#2980b9'),
                spaceAfter=6
            )))

            # Описание
            story.append(Paragraph(command.description, normal_style))

            # Использование
            if command.usage:
                story.append(Paragraph(f"Использование: <font face='Courier'>{command.usage}</font>", normal_style))

            # Примеры
            if command.examples:
                examples = command.examples.split('\n')
                for example in examples[:3]:  # Берем только первые 3 примера
                    if example.strip():
                        story.append(Paragraph(f"<font face='Courier'>{example.strip()}</font>",
                                               ParagraphStyle('Code', parent=normal_style,
                                                              backColor=colors.HexColor('#f8f9fa'),
                                                              leftIndent=20)))

            story.append(Spacer(1, 15))

    # Футер
    footer_text = f"Сгенерировано {timezone.now().strftime('%d.%m.%Y %H:%M')} | Скачиваний: {cheatsheet.download_count}"
    story.append(Paragraph(footer_text, ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.grey,
        alignment=1  # Центрирование
    )))

    doc.build(story)
    pdf = buffer.getvalue()
    buffer.close()

    response.write(pdf)
    return response


def generate_custom_text(title, description, commands):
    """Генерация текстовой пользовательской шпаргалки"""
    content = []
    content.append(f"=== {title.upper()} ===")
    content.append("")

    if description:
        content.append(description)
        content.append("")

    content.append("СОЗДАНО ПОЛЬЗОВАТЕЛЕМ")
    content.append("=" * 50)
    content.append("")

    for i, command in enumerate(commands, 1):
        content.append(f"{i}. {command.command}")
        content.append(f"   Описание: {command.description}")
        content.append(f"   Категория: {command.category.name}")
        content.append(f"   Сложность: {command.get_difficulty_display()}")
        content.append("")

    content.append(f"\nСгенерировано: {timezone.now().strftime('%d.%m.%Y %H:%M')}")
    content.append(f"Количество команд: {len(commands)}")

    response = HttpResponse("\n".join(content), content_type='text/plain; charset=utf-8')
    response['Content-Disposition'] = f'attachment; filename="{title.replace(" ", "_")}.txt"'
    return response