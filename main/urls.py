from django.urls import path
from . import views

app_name = 'main'

urlpatterns = [
    path('', views.department_list, name='department_list'),
    path('department/<uuid:id>/', views.employees_by_department, name='employees_by_department'),
    path('employees/', views.employee_list, name='employee_list'),
    path('employee/<uuid:id>/', views.employee_detail, name='employee_detail'),
]