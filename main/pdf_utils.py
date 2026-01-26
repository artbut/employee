from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.lib.fonts import addMapping
import os


def register_russian_fonts():
    """Регистрация шрифтов с поддержкой кириллицы"""
    try:
        # Проверим доступные шрифты
        possible_fonts = [
            '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',  # Linux
            '/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf',  # Linux
            'C:/Windows/Fonts/arial.ttf',  # Windows
            'C:/Windows/Fonts/times.ttf',  # Windows
            os.path.join(os.path.dirname(__file__), 'fonts', 'arial.ttf'),  # Локальный
        ]

        font_path = None
        for font in possible_fonts:
            if os.path.exists(font):
                font_path = font
                print(f"Найден шрифт: {font_path}")
                break

        if not font_path:
            print("Русские шрифты не найдены, используем стандартные")
            return False

        # Регистрируем шрифты
        pdfmetrics.registerFont(TTFont('RussianFont', font_path))
        pdfmetrics.registerFont(TTFont('RussianFont-Bold', font_path))

        # Настраиваем маппинг
        addMapping('RussianFont', 0, 0, 'RussianFont')
        addMapping('RussianFont', 1, 0, 'RussianFont-Bold')

        print("Русские шрифты успешно зарегистрированы")
        return True
    except Exception as e:
        print(f"Ошибка регистрации шрифтов: {e}")
        return False