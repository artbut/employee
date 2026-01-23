from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.department_list, name='department_list'),
    path('department/<uuid:id>/', views.employees_by_department, name='employees_by_department'),
    path('employees/', views.employee_list, name='employee_list'),
    path('employee/<uuid:id>/', views.employee_detail, name='employee_detail'),
    path('employee/<uuid:id>/history/', views.employee_history, name='employee_history'),
    path('equipment/list/', views.equipment_list, name='equipment_list'),
    path('equipment/<uuid:id>/', views.equipment_detail, name='equipment_detail'),
    path('equipment/<uuid:id>/label/', views.print_equipment_label, name='print_equipment_label'),
    path('equipment/', views.equipment_main, name='equipment_main'),
    path('linux/', views.linux_home, name='linux_home'),
    path('linux/commands/', views.linux_commands, name='linux_commands'),
    path('linux/commands/<uuid:command_id>/', views.linux_command_detail, name='linux_command_detail'),
    path('linux/cheatsheets/', views.linux_cheatsheets, name='linux_cheatsheets'),
    path('linux/search/', views.linux_search, name='linux_search'),
    path('linux/quick-reference/', views.linux_quick_reference, name='linux_quick_reference'),
]