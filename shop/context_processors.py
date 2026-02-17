from django.conf import settings
from .models import Category

def shop_settings(request):
    """Добавляет настройки магазина в контекст всех шаблонов"""
    return {
        'settings': {
            'SHOP_NAME': getattr(settings, 'SHOP_NAME', 'Магазин'),
            'SHOP_PHONE_1': getattr(settings, 'SHOP_PHONE_1', ''),
            'SHOP_PHONE_2': getattr(settings, 'SHOP_PHONE_2', ''),
            'SHOP_PHONE_3': getattr(settings, 'SHOP_PHONE_3', ''),
            'SHOP_INSTAGRAM': getattr(settings, 'SHOP_INSTAGRAM', '#'),
            'SHOP_ADDRESS_1': getattr(settings, 'SHOP_ADDRESS_1', ''),
            'SHOP_ADDRESS_2': getattr(settings, 'SHOP_ADDRESS_2', ''),
            'SHOP_MAP_URL': getattr(settings, 'SHOP_MAP_URL', '#'),
            'TELEGRAM_MANAGER_USERNAME': getattr(settings, 'TELEGRAM_MANAGER_USERNAME', 'your_manager_username'),
        }
    }

def tool_categories(request):
    """Context processor для добавления категорий инструментов во все шаблоны"""
    return {
        'tool_categories': Category.objects.all().order_by('name')
    }
