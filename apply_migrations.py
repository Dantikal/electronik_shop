#!/usr/bin/env python
"""Скрипт для применения миграций на Render"""

import os
import django
from django.core.management import execute_from_command_line

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constr_store.settings')
django.setup()

def apply_migrations():
    """Применяет миграции"""
    try:
        execute_from_command_line(['manage.py', 'migrate'])
        print("✅ Миграции успешно применены")
        return True
    except Exception as e:
        print(f"❌ Ошибка применения миграций: {e}")
        return False

if __name__ == '__main__':
    apply_migrations()
