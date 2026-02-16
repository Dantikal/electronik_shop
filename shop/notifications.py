import logging
from django.core.mail import send_mail
from django.conf import settings
from django.template.loader import render_to_string

logger = logging.getLogger(__name__)

class NotificationService:
    """Сервис для отправки уведомлений клиентам"""
    
    @staticmethod
    def send_payment_confirmation_email(order):
        """Отправить email о подтверждении оплаты"""
        try:
            subject = f'Ваш заказ #{order.id} оплачен!'
            
            context = {
                'order': order,
                'customer_name': order.user.get_full_name() or order.user.username,
            }
            
            # HTML сообщение
            html_message = render_to_string('shop/email/payment_confirmation.html', context)
            
            # Текстовое сообщение
            text_message = f"""
            Уважаемый(ая) {context['customer_name']},
            
            Ваш заказ #{order.id} на сумму {order.total_price} сом успешно оплачен!
            
            Статус заказа: {order.get_status_display()}
            
            Спасибо за покупку!
            
            С уважением,
            Команда KG Style
            """
            
            send_mail(
                subject=subject,
                message=text_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[order.user.email],
                html_message=html_message,
                fail_silently=False,
            )
            
            logger.info(f"Отправлено email подтверждения оплаты для заказа #{order.id}")
            
        except Exception as e:
            logger.error(f"Ошибка отправки email подтверждения оплаты: {e}")
    
    @staticmethod
    def send_payment_confirmation_sms(order):
        """Отправить SMS о подтверждении оплаты (заглушка)"""
        try:
            # Здесь можно интегрировать любой SMS сервис
            # Например: sms.kg, MegaSMS, Twilio и т.д.
            
            message = f"KG Style: Ваш заказ #{order.id} оплачен! Готов к выдаче. Тел: +996555123456"
            
            # Заглушка для отправки SMS
            logger.info(f"SMS отправлено на {order.phone}: {message}")
            
            # Пример интеграции с SMS сервисом:
            # import requests
            # response = requests.post(
            #     'https://sms.kg/api/send',
            #     data={
            #         'phone': order.phone,
            #         'message': message,
            #         'api_key': settings.SMS_API_KEY
            #     }
            # )
            
        except Exception as e:
            logger.error(f"Ошибка отправки SMS: {e}")
    
    @staticmethod
    def send_order_status_notification(order):
        """Отправить уведомление об изменении статуса заказа"""
        try:
            if order.paid and order.status == 'confirmed':
                # Отправляем email
                NotificationService.send_payment_confirmation_email(order)
                
                # Отправляем SMS
                NotificationService.send_payment_confirmation_sms(order)
                
        except Exception as e:
            logger.error(f"Ошибка отправки уведомлений о статусе заказа: {e}")
