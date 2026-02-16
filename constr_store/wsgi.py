"""
WSGI config for constr_store project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constr_store.settings')

# Применяем миграции при старте
if not os.environ.get('DJANGO_DEBUG'):
    try:
        import django
        from django.core.management import execute_from_command_line
        django.setup()
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Миграции применены")
    except Exception as e:
        print(f"❌ Ошибка миграций: {e}")
    
    # Конвертируем существующие изображения в Base64
    try:
        from shop.models import Product, Category
        import base64
        
        # Конвертируем товары
        products = Product.objects.filter(image__isnull=False).exclude(image='').filter(image_data__isnull=True)
        for product in products:
            try:
                if product.image and hasattr(product.image, 'path'):
                    with open(product.image.path, 'rb') as f:
                        image_data = f.read()
                    product.image_data = base64.b64encode(image_data).decode('utf-8')
                    product.save(update_fields=['image_data'])
                    print(f"✅ Обновлено изображение товара: {product.name}")
            except Exception as e:
                print(f"⚠️ Ошибка товара {product.name}: {e}")
        
        # Конвертируем категории
        categories = Category.objects.filter(image__isnull=False).exclude(image='').filter(image_data__isnull=True)
        for category in categories:
            try:
                if category.image and hasattr(category.image, 'path'):
                    with open(category.image.path, 'rb') as f:
                        image_data = f.read()
                    category.image_data = base64.b64encode(image_data).decode('utf-8')
                    category.save(update_fields=['image_data'])
                    print(f"✅ Обновлено изображение категории: {category.name}")
            except Exception as e:
                print(f"⚠️ Ошибка категории {category.name}: {e}")
                
        print("🎉 Конвертация изображений завершена!")
    except Exception as e:
        print(f"❌ Ошибка конвертации: {e}")

# Создаем media директорию при старте (без прав на /var/data)
if not os.environ.get('DJANGO_DEBUG'):
    try:
        media_dir = '/var/data/media'
        os.makedirs(media_dir, exist_ok=True)
    except PermissionError:
        # Если нет прав, используем временную папку
        media_dir = '/tmp/media'
        os.makedirs(media_dir, exist_ok=True)

application = get_wsgi_application()

# WhiteNoise для static файлов
application = WhiteNoise(
    application,
    root=os.path.join(os.path.dirname(__file__), '..', 'staticfiles'),
    prefix='/static/',
    autorefresh=True
)

# Добавляем media файлы
if not os.environ.get('DJANGO_DEBUG'):
    try:
        media_root = '/var/data/media'
        application.add_files(media_root, prefix='/media/')
    except:
        # Если нет прав, используем временную папку
        media_root = '/tmp/media'
        application.add_files(media_root, prefix='/media/')
else:
    media_root = os.path.join(os.path.dirname(__file__), '..', 'media')
    application.add_files(media_root, prefix='/media/')
