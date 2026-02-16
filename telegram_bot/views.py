import json
import logging
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods
from telegram import Update
from telegram.ext import CallbackContext
from shop.models import Order
from .bot import telegram_bot
from django.conf import settings

logger = logging.getLogger(__name__)

@csrf_exempt
@require_http_methods(["POST"])
def telegram_webhook(request):
    """Обработка webhook от Telegram бота"""
    try:
        data = json.loads(request.body)
        print(f"Получены данные от Telegram: {data}")  # Отладка
        
        # Проверяем структуру данных
        if 'callback_query' in data:
            callback_query_data = data['callback_query']
            print(f"Получен callback_query: {callback_query_data}")  # Отладка
            handle_callback_query(callback_query_data)
        else:
            print(f"Получен другой тип данных: {list(data.keys())}")  # Отладка
        
        return JsonResponse({'status': 'ok'})
        
    except Exception as e:
        logger.error(f"Ошибка обработки webhook: {e}")
        print(f"Ошибка webhook: {e}")  # Отладка
        return JsonResponse({'status': 'error'}, status=500)

def handle_callback_query(callback_query):
    """Обработка нажатий на inline кнопки"""
    try:
        data = callback_query.get('data', '')
        message = callback_query.get('message', {})
        chat_id = message.get('chat', {}).get('id')
        callback_id = callback_query.get('id')
        
        print(f"Обработка callback data: {data}, chat_id: {chat_id}, callback_id: {callback_id}")  # Отладка
        
        if data.startswith('confirm_payment_'):
            order_id = data.split('_')[-1]
            print(f"Подтверждение оплаты заказа #{order_id}")  # Отладка
            confirm_order_payment(order_id, chat_id, callback_query)
            
        elif data.startswith('reject_payment_'):
            order_id = data.split('_')[-1]
            print(f"Отклонение оплаты заказа #{order_id}")  # Отладка
            reject_order_payment(order_id, chat_id, callback_query)
            
    except Exception as e:
        logger.error(f"Ошибка обработки callback query: {e}")
        print(f"Ошибка callback: {e}")  # Отладка

# Для совместимости с polling
async def handle_callback_query_async(update, context):
    """Асинхронная обертка для polling"""
    await handle_callback_query(update.callback_query)

def confirm_order_payment(order_id, chat_id, callback_query):
    """Подтверждение оплаты заказа"""
    try:
        print(f"Начало подтверждения оплаты заказа #{order_id}")  # Отладка
        order = Order.objects.get(id=order_id)
        print(f"Найден заказ: статус={order.status}, paid={order.paid}")  # Отладка
        
        order.paid = True
        order.status = 'confirmed'
        order.save()
        print(f"Заказ обновлен: статус={order.status}, paid={order.paid}")  # Отладка
        
        # Отправляем уведомления клиенту
        try:
            from shop.notifications import NotificationService
            NotificationService.send_order_status_notification(order)
            print("Уведомление клиенту отправлено")  # Отладка
        except Exception as e:
            logger.error(f"Ошибка отправки уведомлений клиенту: {e}")
            print(f"Ошибка уведомлений: {e}")  # Отладка
        
        # Обновляем сообщение с кнопками
        try:
            # Для webhook используем requests
            import requests
            token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
            if token:
                url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
                data = {
                    'callback_query_id': callback_query.get('id'),
                    'text': '✅ Оплата подтверждена администратором.',
                    'show_alert': False
                }
                response = requests.post(url, data=data)
                print(f"Callback answer отправлен: {response.status_code}")  # Отладка
        except Exception as e:
            print(f"Ошибка отправки callback answer: {e}")  # Отладка
        
        logger.info(f"Администратор подтвердил оплату заказа #{order_id}")
        print(f"Подтверждение заказа #{order_id} завершено успешно")  # Отладка
        
    except Order.DoesNotExist:
        print(f"Заказ #{order_id} не найден")  # Отладка
        # Отправляем ответ об ошибке
        try:
            import requests
            token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
            if token:
                url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
                data = {
                    'callback_query_id': callback_query.get('id'),
                    'text': 'Заказ не найден',
                    'show_alert': True
                }
                requests.post(url, data=data)
        except:
            pass
    except Exception as e:
        logger.error(f"Ошибка подтверждения оплаты: {e}")
        print(f"Ошибка подтверждения: {e}")  # Отладка
        # Отправляем ответ об ошибке
        try:
            import requests
            token = getattr(settings, 'TELEGRAM_BOT_TOKEN', None)
            if token:
                url = f"https://api.telegram.org/bot{token}/answerCallbackQuery"
                data = {
                    'callback_query_id': callback_query.get('id'),
                    'text': 'Ошибка подтверждения оплаты',
                    'show_alert': True
                }
                requests.post(url, data=data)
        except:
            pass

def reject_order_payment(order_id, chat_id, callback_query):
    """Отклонение оплаты заказа"""
    try:
        order = Order.objects.get(id=order_id)
        order.status = 'cancelled'
        order.save()
        
        # Обновляем сообщение с кнопками
        callback_query.edit_message_text(
            text=f"❌ Оплата заказа #{order.id} отклонена администратором.",
            reply_markup=None
        )
        
        logger.info(f"Администратор отклонил оплату заказа #{order_id}")
        
    except Order.DoesNotExist:
        callback_query.answer("Заказ не найден", show_alert=True)
    except Exception as e:
        logger.error(f"Ошибка отклонения оплаты: {e}")
        callback_query.answer("Ошибка отклонения оплаты", show_alert=True)
