from django.shortcuts import render, get_object_or_404
from django.core.paginator import Paginator
from .models import Employee, Department

def department_list(request):
    """Отображает список подразделений с количеством сотрудников"""
    departments = Department.objects.prefetch_related('employees').all()
    dept_list = []
    for dept in departments:
        dept.employee_count = dept.employees.count()
        dept_list.append(dept)

    context = {
        'departments': dept_list
    }
    return render(request, 'department_list.html', context)


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


def employee_list(request):
    """Отображает всех сотрудников"""
    employee_list = Employee.objects.select_related(
        'department', 'position', 'location'
    ).all().order_by('last_name', 'first_name')

    paginator = Paginator(employee_list, 12)
    page_number = request.GET.get('page')
    employees = paginator.get_page(page_number)

    context = {
        'employees': employees
    }
    return render(request, 'employee_list.html', context)


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