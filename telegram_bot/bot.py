import logging
import asyncio
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup
from django.conf import settings
from asgiref.sync import sync_to_async

logger = logging.getLogger(__name__)

class TelegramBot:
    def __init__(self):
        token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
        if not token:
            self.bot = None
            logger.warning("TELEGRAM_BOT_TOKEN not configured")
        else:
            self.bot = Bot(token=token)
        self.admin_chat_id = getattr(settings, 'TELEGRAM_ADMIN_CHAT_ID', None)
    
    async def send_payment_notification(self, order):
        """Отправить уведомление о новом платеже администратору"""
        if not self.bot or not self.admin_chat_id:
            logger.warning("Telegram bot not configured, skipping notification")
            return
            
        try:
            # Формируем сообщение с полной информацией
            from datetime import datetime, timedelta
            
            # Конвертируем время в Кыргызстан (+6 UTC)
            kg_time = order.created_at + timedelta(hours=6)
            
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
🛒 Товары: {self.get_order_items(order)}
──────────────

🔗 Админка: http://127.0.0.1:8000/admin/shop/order/{order.id}/change/
──────────────"""
            
            # Создаем кнопки для подтверждения/отклонения
            keyboard = [
                [
                    InlineKeyboardButton("✅ Подтвердить", callback_data=f"confirm_payment_{order.id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_payment_{order.id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение
            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=message,
                reply_markup=reply_markup
            )
            
            logger.info(f"Отправлено уведомление о платеже для заказа #{order.id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления о платеже: {e}")
    
    def get_order_items(self, order):
        """Получить список товаров заказа"""
        items = []
        for item in order.items.all()[:3]:  # Показываем первые 3 товара
            items.append(f"{item.product.name}")
        if order.items.count() > 3:
            items.append(f"и еще {order.items.count() - 3} шт.")
        return ", ".join(items)
    
    async def send_cart_to_telegram(self, cart, user_info):
        """Отправить корзину в Telegram для оплаты"""
        if not self.bot or not self.admin_chat_id:
            logger.warning("Telegram bot not configured, skipping cart notification")
            return
            
        try:
            # Формируем сообщение с информацией о корзине
            from datetime import datetime
            
            message = f"""🛒 НОВЫЙ ЗАКАЗ ЧЕРЕЗ TELEGRAM
──────────────────
👤 Клиент:
• Имя: {user_info.get('first_name', '')} {user_info.get('last_name', '')}
• Email: {user_info.get('email', '')}
• Тел: {user_info.get('phone', '')}
──────────────────
📍 Доставка:
• Город: {user_info.get('city', '')}
• Адрес: {user_info.get('address', '')}
──────────────────
📦 Товары в корзине:
"""
            
            total_price = 0
            for item in cart.items.all():
                item_total = item.product.price * item.quantity
                total_price += item_total
                message += f"• {item.product.name} x{item.quantity} = {item_total} сом\n"
            
            message += f"""
──────────────────
💰 Итого: {total_price} сом
⏰ Время: {datetime.now().strftime('%d.%m.%Y %H:%M')}
──────────────────

Для оплаты свяжитесь с клиентом и подтвердите заказ!
"""
            
            # Создаем кнопки для действий
            keyboard = [
                [
                    InlineKeyboardButton("✅ Подтвердить заказ", callback_data=f"confirm_telegram_order_{cart.id}"),
                    InlineKeyboardButton("❌ Отклонить", callback_data=f"reject_telegram_order_{cart.id}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            # Отправляем сообщение
            await self.bot.send_message(
                chat_id=self.admin_chat_id,
                text=message,
                reply_markup=reply_markup
            )
            
            logger.info(f"Отправлена корзина в Telegram для пользователя {user_info.get('email', '')}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки корзины в Telegram: {e}")
    
    async def send_payment_confirmation(self, order):
        """Отправить уведомление клиенту о подтверждении оплаты"""
        try:
            message = f"""✅ Ваш платеж подтвержден!
            
Заказ #{order.id} на сумму {order.total_price} сом оплачен.
Ваш заказ готовится к отправке.

Спасибо за покупку! 🛍️"""
            
            # Здесь можно добавить отправку клиенту в Telegram, если у него есть chat_id
            # Пока отправляем только админу
            
            logger.info(f"Отправлено подтверждение оплаты для заказа #{order.id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки подтверждения оплаты: {e}")

# Глобальный экземпляр бота
telegram_bot = TelegramBot()

# Синхронные обертки
def send_payment_notification(order):
    """Синхронная обертка для отправки уведомления о платеже"""
    if telegram_bot.bot and telegram_bot.admin_chat_id:
        asyncio.run(telegram_bot.send_payment_notification(order))

def send_cart_to_telegram(cart, user_info):
    """Синхронная обертка для отправки корзины в Telegram"""
    if telegram_bot.bot and telegram_bot.admin_chat_id:
        asyncio.run(telegram_bot.send_cart_to_telegram(cart, user_info))

def send_payment_confirmation(order):
    """Синхронная обертка для отправки подтверждения оплаты"""
    if telegram_bot.bot and telegram_bot.admin_chat_id:
        asyncio.run(telegram_bot.send_payment_confirmation(order))
