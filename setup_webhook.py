#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constr_store.settings')
django.setup()

from django.conf import settings
import requests

def setup_webhook():
    """Установка webhook для Telegram бота"""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не настроен!")
        return False
    
    # URL webhook на Render
    webhook_url = "https://neznaika-kg.onrender.com/telegram/webhook/"
    
    # Удаляем старый webhook
    delete_url = f"https://api.telegram.org/bot{token}/deleteWebhook"
    response = requests.get(delete_url)
    print(f"Удаление старого webhook: {response.json()}")
    
    # Устанавливаем новый webhook
    set_url = f"https://api.telegram.org/bot{token}/setWebhook"
    data = {
        'url': webhook_url,
        'allowed_updates': ['callback_query']  # Только callback_query для кнопок
    }
    
    response = requests.post(set_url, json=data)
    result = response.json()
    
    if result.get('ok'):
        print(f"✅ Webhook успешно установлен: {webhook_url}")
        print(f"📝 Инфо: {result.get('description', 'OK')}")
        return True
    else:
        print(f"❌ Ошибка установки webhook: {result}")
        return False

def get_webhook_info():
    """Получение информации о webhook"""
    token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
    
    if not token:
        print("❌ TELEGRAM_BOT_TOKEN не настроен!")
        return
    
    info_url = f"https://api.telegram.org/bot{token}/getWebhookInfo"
    response = requests.get(info_url)
    result = response.json()
    
    if result.get('ok'):
        webhook_info = result.get('result', {})
        print(f"📋 Текущий webhook:")
        print(f"   URL: {webhook_info.get('url', 'Не установлен')}")
        print(f"   Ошибок: {webhook_info.get('pending_update_count', 0)}")
        print(f"   Последняя ошибка: {webhook_info.get('last_error_message', 'Нет')}")
    else:
        print(f"❌ Ошибка получения информации: {result}")

if __name__ == '__main__':
    print("🔧 Настройка Telegram Webhook")
    print("=" * 50)
    
    # Показываем текущий статус
    get_webhook_info()
    print()
    
    # Устанавливаем webhook
    setup_webhook()
    print()
    
    # Показываем новый статус
    get_webhook_info()
