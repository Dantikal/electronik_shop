#!/usr/bin/env python
"""Скрипт для обновления существующих изображений в Base64"""

import os
import django
import base64
from django.core.files.base import ContentFile

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constr_store.settings')
django.setup()

from shop.models import Product, Category

def update_existing_images():
    """Обновляет существующие изображения в Base64"""
    
    # Обновляем товары
    products = Product.objects.filter(image__isnull=False).exclude(image='')
    for product in products:
        try:
            if product.image and hasattr(product.image, 'path'):
                # Читаем файл изображения
                with open(product.image.path, 'rb') as f:
                    image_data = f.read()
                
                # Конвертируем в Base64
                product.image_data = base64.b64encode(image_data).decode('utf-8')
                product.save(update_fields=['image_data'])
                print(f"✅ Обновлено изображение товара: {product.name}")
        except Exception as e:
            print(f"❌ Ошибка обновления товара {product.name}: {e}")
    
    # Обновляем категории
    categories = Category.objects.filter(image__isnull=False).exclude(image='')
    for category in categories:
        try:
            if category.image and hasattr(category.image, 'path'):
                # Читаем файл изображения
                with open(category.image.path, 'rb') as f:
                    image_data = f.read()
                
                # Конвертируем в Base64
                category.image_data = base64.b64encode(image_data).decode('utf-8')
                category.save(update_fields=['image_data'])
                print(f"✅ Обновлено изображение категории: {category.name}")
        except Exception as e:
            print(f"❌ Ошибка обновления категории {category.name}: {e}")
    
    print("🎉 Обновление изображений завершено!")

if __name__ == '__main__':
    update_existing_images()
