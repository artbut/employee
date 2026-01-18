from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from django.contrib.auth.decorators import login_required
from .models import Employee, Department
from django.db.models import Q, Count

def department_list(request):
    departments = Department.objects.annotate(
        employee_count=Count('emp')  # ← 'emp', а не 'employees'
    ).order_by('name')
    return render(request, 'department_list.html', {'departments': departments})


@login_required
def employees_by_department(request, id):
    """Отображает сотрудников выбранного подразделения"""
    department = get_object_or_404(Department, id=id)
    employee_list = Employee.objects.select_related(
        'position', 'location'
    ).filter(department=department).order_by('last_name', 'first_name')

    paginator = Paginator(employee_list, 12)
    page_number = request.GET.get('page')
    employees = paginator.get_page(page_number)

    context = {
        'employees': employees,
        'department': department
    }
    return render(request, 'employee_list.html', context)


@login_required
def employee_list(request):
    """Отображает всех сотрудников с возможностью поиска"""
    # Начинаем с полного списка
    employee_list = Employee.objects.select_related(
        'department', 'position', 'location'
    ).all().order_by('last_name', 'first_name')

    # Получаем поисковый запрос из GET-параметров
    search_query = request.GET.get('search', '').strip()

    # Если есть запрос — фильтруем
    if search_query:
        employee_list = employee_list.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(second_name__icontains=search_query) |
            Q(login__icontains=search_query)
        )

    # Пагинация
    paginator = Paginator(employee_list, 12)  # 12 сотрудников на странице
    page_number = request.GET.get('page')
    employees = paginator.get_page(page_number)

    # Контекст
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