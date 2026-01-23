from django.core.management.base import BaseCommand
from main.models import LinuxCategory, LinuxCommand


class Command(BaseCommand):
    help = 'Загружает основные Linux команды'

    def handle(self, *args, **kwargs):
        # Создаем категории
        categories = [
            {'name': 'Файловая система', 'icon': 'fa-folder', 'order': 1},
            {'name': 'Процессы', 'icon': 'fa-microchip', 'order': 2},
            {'name': 'Сеть', 'icon': 'fa-network-wired', 'order': 3},
            {'name': 'Пользователи', 'icon': 'fa-user', 'order': 4},
            {'name': 'Поиск', 'icon': 'fa-search', 'order': 5},
            {'name': 'Архивация', 'icon': 'fa-file-archive', 'order': 6},
            {'name': 'Текст', 'icon': 'fa-file-alt', 'order': 7},
        ]

        cat_objects = {}
        for cat in categories:
            obj, created = LinuxCategory.objects.get_or_create(
                name=cat['name'],
                defaults=cat
            )
            cat_objects[cat['name']] = obj

        # Основные команды
        commands = [
            {
                'command': 'ls',
                'description': 'Просмотр содержимого директории',
                'usage': 'ls [опции] [директория]',
                'options': '-l подробный список\n-a показать скрытые файлы\n-h человекочитаемый размер',
                'examples': 'ls -la\nls -lh /home/user',
                'difficulty': 'beginner',
                'category': cat_objects['Файловая система'],
                'tags': 'файлы,директория,список',
                'is_favorite': True,
                'order': 1
            },
            {
                'command': 'cd',
                'description': 'Смена текущей директории',
                'usage': 'cd [директория]',
                'options': '.. на уровень выше\n~ домашняя директория\n- предыдущая директория',
                'examples': 'cd /var/log\ncd ..\ncd ~',
                'difficulty': 'beginner',
                'category': cat_objects['Файловая система'],
                'tags': 'навигация,директория',
                'order': 2
            },
            # Добавьте больше команд по необходимости
        ]

        for cmd in commands:
            LinuxCommand.objects.get_or_create(
                command=cmd['command'],
                category=cmd['category'],
                defaults=cmd
            )

        self.stdout.write(self.style.SUCCESS('✅ Linux команды загружены!'))