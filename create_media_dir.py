#!/usr/bin/env python
"""Создает папку для media файлов в постоянном хранилище Render"""

import os

def create_media_directory():
    """Создает папку /var/data/media если она не существует"""
    media_dir = '/var/data/media'
    
    try:
        os.makedirs(media_dir, exist_ok=True)
        print(f"✅ Media директория создана: {media_dir}")
        return True
    except Exception as e:
        print(f"❌ Ошибка создания media директории: {e}")
        return False

if __name__ == '__main__':
    create_media_directory()
