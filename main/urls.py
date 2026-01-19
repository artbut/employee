from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.department_list, name='department_list'),
    path('department/<uuid:id>/', views.employees_by_department, name='employees_by_department'),
    path('employees/', views.employee_list, name='employee_list'),
    path('employee/<uuid:id>/', views.employee_detail, name='employee_detail'),
    path('employee/<uuid:id>/history/', views.employee_history, name='employee_history'),
    path('equipment/', views.equipment_list, name='equipment_list'),
    path('equipment/<uuid:id>/', views.equipment_detail, name='equipment_detail'),
    path('equipment/<uuid:id>/label/', views.print_equipment_label, name='print_equipment_label'),
]