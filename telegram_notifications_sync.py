import requests
import json
from django.conf import settings

def send_telegram_notification_sync(order):
    """Отправить уведомление в Telegram (синхронно)"""
    try:
        token = settings.TELEGRAM_BOT_TOKEN
        chat_id = settings.TELEGRAM_ADMIN_CHAT_ID
        
        # Проверяем наличие токена и chat_id
        if not token or not chat_id:
            print(f"❌ Telegram bot not configured: token={bool(token)}, chat_id={bool(chat_id)}")
            print(f"📝 Заказ #{order.id} создан, но уведомление не отправлено")
            print(f"💰 Сумма: {order.total_price} сом")
            print(f"👤 Клиент: {order.first_name} {order.last_name}")
            return False  # Возвращаем False чтобы показать что уведомление не отправлено
        
        # Формируем сообщение с полной информацией
        from datetime import datetime, timedelta
        
        # Конвертируем время в Кыргызстан (+6 UTC)
        kg_time = order.created_at + timedelta(hours=6)
        
        # Получаем товары заказа
        items = []
        for item in order.items.all():
            items.append(f"{item.product.name} x{item.quantity}")
        items_text = ", ".join(items)
        
        # Получаем правильный URL админки
        from django.contrib.sites.shortcuts import get_current_site
        current_site = get_current_site(None)
        admin_url = f"https://{current_site.domain}/admin/shop/order/{order.id}/change/"
        order_url = f"https://{current_site.domain}/order/{order.id}/"
        
        message = f"""🤖 Бот KG Style:
──────────────
💰 НОВЫЙ ЗАКАЗ
──────────────
📦 Заказ: #{order.id}
💰 Сумма: {order.total_price} сом
🔖 Код: {order.qr_code}
──────────────
👤 Клиент:
• Имя: {order.first_name} {order.last_name}
• Email: {order.email}
• Тел: {order.phone}
──────────────
📍 Доставка:
• Город: {order.city}
• Адрес: {order.address}
• Индекс: {order.postal_code or 'Не указан'}
──────────────
⏰ Время: {kg_time.strftime('%d.%m.%Y %H:%M')} (KG)
🛒 Товары: {items_text}
──────────────

🔗 Админка: {admin_url}
🛍️ Страница заказа: {order_url}
⚠️ Вход в админку: https://{current_site.domain}/admin/
──────────────"""
        
        # Создаем кнопки
        keyboard = {
            "inline_keyboard": [
                [
                    {"text": "✅ Подтвердить", "callback_data": f"confirm_payment_{order.id}"},
                    {"text": "❌ Отклонить", "callback_data": f"reject_payment_{order.id}"}
                ]
            ]
        }
        
        # URL для отправки сообщения
        url = f"https://api.telegram.org/bot{token}/sendMessage"
        
        # Данные для запроса
        data = {
            'chat_id': chat_id,
            'text': message,
            'reply_markup': json.dumps(keyboard),
            'parse_mode': 'HTML'
        }
        
        # Отправляем запрос
        response = requests.post(url, data=data)
        
        if response.status_code == 200:
            result = response.json()
            if result.get('ok'):
                print(f"✅ Уведомление отправлено для заказа #{order.id}")
                return True
            else:
                print(f"❌ Ошибка API: {result}")
                return False
        else:
            print(f"❌ Ошибка HTTP: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Ошибка отправки: {e}")
        return False
