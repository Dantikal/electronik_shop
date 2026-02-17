from django import template
from django.utils.html import urlencode

register = template.Library()

@register.simple_tag
def telegram_order_message(order):
    """Формирует сообщение для Telegram с товарами заказа"""
    items_text = ""
    for item in order.items.all():
        items_text += f"• {item.product.name} x{item.quantity} = {item.total_price} сом\n"
    
    message = f"""Здравствуйте! Я хочу оплатить заказ #{order.id}

📦 Товары:
{items_text}
💰 Итого: {order.total_price} сом
👤 Имя: {order.first_name} {order.last_name}
📞 Тел: {order.phone}
📍 Адрес: {order.address}, {order.city}"""
    
    # Кодируем для URL
    return message.replace('\n', '%0A').replace(' ', '%20')

@register.simple_tag
def telegram_simple_message(order):
    """Формирует простое сообщение для Telegram с названиями товаров"""
    product_lines = []
    for item in order.items.all():
        product_lines.append(f"{item.product.name} {item.quantity} шт.")
    
    products_text = "\n".join(product_lines) if product_lines else "нет товаров"
    message = f"Я хочу оплатить заказ #{order.id}: {products_text}"
    
    # Кодируем для URL только пробелы и спецсимволы, оставляем \n как есть
    from urllib.parse import quote
    return quote(message, safe='\n')
