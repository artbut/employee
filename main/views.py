from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from .models import Employee, Department, Equipment
from django.db.models import Q, Count
from .utils import apply_employee_filters_and_ordering
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
import os

def department_list(request):
    departments = Department.objects.annotate(
        employee_count=Count('emp')  # ← 'emp', а не 'employees'
    ).order_by('name')
    return render(request, 'department_list.html', {'departments': departments})

def get_equipment_queryset():
    return Equipment.objects.select_related(
        'type', 'manufacturer', 'location', 'responsible__department'
    ).order_by('-created')


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
    """Отображает детальную информацию о сотруднике"""
    employee = get_object_or_404(
        Employee.objects.select_related('department', 'position', 'location'),
        id=id
    )

    context = {
        'employee': employee
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


@login_required
def equipment_list(request):
    query = request.GET.get('q', '').strip()

    equipment_list = get_equipment_queryset()

    if query:
        equipment_list = equipment_list.filter(
            Q(serial_number__icontains=query) |
            Q(inventory_number__icontains=query) |
            Q(model__icontains=query) |
            Q(network_name__icontains=query) |
            Q(manufacturer__name__icontains=query)
        )

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
    """Отображает HTML-этикетку для печати"""
    equipment = get_object_or_404(
        Equipment.objects.select_related('type', 'manufacturer', 'location'),
        id=id
    )

    context = {
        'equip': equipment,
        'company_name': 'ООО "ТехноЛайн"',  # или из settings
    }
    return render(request, 'labels/equipment_label.html', context)