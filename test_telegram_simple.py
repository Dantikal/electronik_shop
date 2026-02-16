#!/usr/bin/env python
import os
import sys
import django

# Настройка Django
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constr_store.settings')
django.setup()

from django.conf import settings
from telegram_bot.bot import send_payment_notification
from shop.models import Order

def test_telegram():
    print("🔧 Тестирование Telegram бота...")
    
    # Проверяем настройки
    print(f"🔧 Token: {settings.TELEGRAM_BOT_TOKEN[:20] if settings.TELEGRAM_BOT_TOKEN else 'None'}...")
    print(f"🔧 Chat ID: {settings.TELEGRAM_ADMIN_CHAT_ID}")
    
    if not settings.TELEGRAM_BOT_TOKEN:
        print("❌ TELEGRAM_BOT_TOKEN не настроен!")
        return False
    
    if not settings.TELEGRAM_ADMIN_CHAT_ID:
        print("❌ TELEGRAM_ADMIN_CHAT_ID не настроен!")
        return False
    
    # Находим последний заказ
    try:
        order = Order.objects.last()
        if not order:
            print("❌ Нет заказов в базе данных!")
            return False
        
        print(f"📦 Найден заказ #{order.id}")
        
        # Отправляем уведомление
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(send_payment_notification(order))
            print(f"✅ Результат: {result}")
            return result
        finally:
            loop.close()
            
    except Exception as e:
        print(f"❌ Ошибка: {e}")
        return False

if __name__ == "__main__":
    test_telegram()
