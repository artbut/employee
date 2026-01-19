from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from .models import Employee, Department
from django.db.models import Q, Count
from .utils import apply_employee_filters_and_ordering

def department_list(request):
    departments = Department.objects.annotate(
        employee_count=Count('emp')  # ← 'emp', а не 'employees'
    ).order_by('name')
    return render(request, 'department_list.html', {'departments': departments})


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