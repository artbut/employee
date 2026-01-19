from django.db.models import Q


def apply_employee_filters_and_ordering(queryset, search_query, order_param):
    """
    Применяет фильтрацию по поисковому запросу и сортировку к queryset сотрудников.

    :param queryset: исходный QuerySet модели Employee (уже с select_related)
    :param search_query: строка поиска (например, "Иван")
    :param order_param: параметр сортировки из GET-запроса (например, "position", "-location__code")
    :return: отфильтрованный и отсортированный QuerySet
    """
    # === 1. Фильтрация по поиску ===
    if search_query:
        queryset = queryset.filter(
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query) |
            Q(second_name__icontains=search_query) |
            Q(login__icontains=search_query)
        )

    # === 2. Сортировка ===
    # Белый список разрешённых полей для сортировки (защита от инъекций!)
    valid_order_fields = {
        'position': 'position__name',
        '-position': '-position__name',
        'location__code': 'location__code',
        '-location__code': '-location__code',
    }

    # Если order_param есть в белом списке — используем его, иначе сортируем по умолчанию
    order_field = valid_order_fields.get(order_param, 'last_name')

    # Всегда добавляем 'first_name' как вторичную сортировку для стабильности
    return queryset.order_by(order_field, 'first_name')