from django.shortcuts import render
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db.models import Sum, Count, Avg, F, Q
from django.db.models.functions import TruncDay, TruncMonth, TruncYear
from django.utils import timezone
from datetime import timedelta, datetime
from shop.models import Order, OrderItem, Product
from django.http import JsonResponse, HttpResponse
import json
import pandas as pd
import openpyxl
from io import BytesIO

def is_admin(user):
    return user.is_authenticated and (user.is_staff or user.is_superuser)

@login_required
@user_passes_test(is_admin)
def dashboard_home(request):
    """Главная страница дашборда с аналитикой"""
    
    # Базовая статистика
    today = timezone.now().date()
    last_7_days = today - timedelta(days=7)
    last_30_days = today - timedelta(days=30)
    
    # Общие показатели
    total_orders = Order.objects.count()
    total_revenue = Order.objects.aggregate(total=Sum('total_price'))['total'] or 0
    total_products_sold = OrderItem.objects.aggregate(total=Sum('quantity'))['total'] or 0
    total_customers = Order.objects.values('user').distinct().count()
    
    # Средний чек
    avg_order_value = Order.objects.aggregate(avg=Avg('total_price'))['avg'] or 0
    
    # Показатели за сегодня
    today_orders = Order.objects.filter(created_at__date=today).count()
    today_revenue = Order.objects.filter(created_at__date=today).aggregate(total=Sum('total_price'))['total'] or 0
    
    # Показатели за последние 7 дней
    week_orders = Order.objects.filter(created_at__date__gte=last_7_days).count()
    week_revenue = Order.objects.filter(created_at__date__gte=last_7_days).aggregate(total=Sum('total_price'))['total'] or 0
    
    # Показатели за последние 30 дней
    month_orders = Order.objects.filter(created_at__date__gte=last_30_days).count()
    month_revenue = Order.objects.filter(created_at__date__gte=last_30_days).aggregate(total=Sum('total_price'))['total'] or 0
    
    # Топ товары
    top_products = OrderItem.objects.values(
        'product__name', 'product__id'
    ).annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('price'))
    ).order_by('-total_sold')[:10]
    
    # Последние заказы
    recent_orders = Order.objects.select_related('user').order_by('-created_at')[:10]
    
    # График продаж за последние 30 дней
    sales_chart_data = []
    for i in range(30):
        date = today - timedelta(days=i)
        daily_orders = Order.objects.filter(created_at__date=date).count()
        daily_revenue = Order.objects.filter(created_at__date=date).aggregate(total=Sum('total_price'))['total'] or 0
        sales_chart_data.append({
            'date': date.strftime('%d.%m'),
            'orders': daily_orders,
            'revenue': float(daily_revenue)
        })
    sales_chart_data.reverse()
    
    # Статусы заказов
    order_status_stats = Order.objects.values('status').annotate(
        count=Count('id')
    ).order_by('status')
    
    # Методы оплаты
    payment_method_stats = Order.objects.values('payment_method').annotate(
        count=Count('id'),
        total=Sum('total_price')
    ).order_by('-total')
    
    # Новые клиенты (за последние 30 дней)
    new_customers = Order.objects.filter(
        created_at__date__gte=last_30_days
    ).values('user').distinct().count()
    
    # Постоянные клиенты (больше 1 заказа)
    returning_customers = Order.objects.values('user').annotate(
        order_count=Count('id')
    ).filter(order_count__gt=1).count()
    
    # LTV (Lifetime Value) - средняя выручка с клиента
    customer_ltv = total_revenue / total_customers if total_customers > 0 else 0
    
    # Остатки на складе
    inventory_stats = Product.objects.aggregate(
        total_products=Count('id'),
        total_stock=Sum('stock'),
        out_of_stock=Count('id', filter=Q(stock=0))
    )
    
    # Источники трафика (если есть данные)
    # Это требует дополнительной модели для отслеживания источников
    
    # Время обработки заказа
    processing_times = []
    for order in Order.objects.filter(
        status__in=['confirmed', 'shipped', 'delivered']
    ).select_related('user'):
        if order.updated_at and order.created_at:
            processing_hours = (order.updated_at - order.created_at).total_seconds() / 3600
            processing_times.append(processing_hours)
    
    avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
    
    context = {
        # Деньги
        'total_revenue': total_revenue,
        'today_revenue': today_revenue,
        'week_revenue': week_revenue,
        'month_revenue': month_revenue,
        'avg_order_value': avg_order_value,
        'customer_ltv': customer_ltv,
        
        # Заказы
        'total_orders': total_orders,
        'today_orders': today_orders,
        'week_orders': week_orders,
        'month_orders': month_orders,
        'order_status_stats': order_status_stats,
        'avg_processing_time': avg_processing_time,
        
        # Товары
        'total_products_sold': total_products_sold,
        'top_products': top_products,
        'inventory_stats': inventory_stats,
        
        # Клиенты
        'total_customers': total_customers,
        'new_customers': new_customers,
        'returning_customers': returning_customers,
        
        # Конверсия (новые клиенты / все посетители)
        'conversion_rate': (new_customers / 100 * 100) if new_customers > 0 else 0,  # условно, т.к. нет данных о посетителях
        
        # Последние заказы
        'recent_orders': recent_orders,
        
        # График
        'sales_chart_data': json.dumps(sales_chart_data),
        
        # Методы оплаты
        'payment_method_stats': payment_method_stats,
    }
    
    return render(request, 'dashboard/dashboard.html', context)

@login_required
@user_passes_test(is_admin)
def dashboard_analytics(request):
    """Детальная аналитика"""
    
    period = request.GET.get('period', 'month')  # week, month, year
    
    if period == 'week':
        start_date = timezone.now().date() - timedelta(days=7)
        trunc_func = TruncDay
    elif period == 'year':
        start_date = timezone.now().date() - timedelta(days=365)
        trunc_func = TruncMonth
    else:  # month
        start_date = timezone.now().date() - timedelta(days=30)
        trunc_func = TruncDay
    
    # Продажи по дням/месяцам
    sales_by_period = Order.objects.filter(
        created_at__date__gte=start_date
    ).annotate(
        period=trunc_func('created_at')
    ).values('period').annotate(
        orders=Count('id'),
        revenue=Sum('total_price')
    ).order_by('period')
    
    # Топ категории
    top_categories = OrderItem.objects.values(
        'product__category__name'
    ).annotate(
        total_sold=Sum('quantity'),
        total_revenue=Sum(F('quantity') * F('price'))
    ).order_by('-total_revenue')[:10]
    
    # Средний чек
    avg_order_value = Order.objects.filter(
        created_at__date__gte=start_date
    ).aggregate(avg=Avg('total_price'))['avg'] or 0
    
    context = {
        'period': period,
        'sales_by_period': sales_by_period,
        'top_categories': top_categories,
        'avg_order_value': avg_order_value,
    }
    
    return render(request, 'dashboard/analytics.html', context)

@login_required
@user_passes_test(is_admin)
def dashboard_products(request):
    """Аналитика по товарам"""
    
    products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity'),
        total_revenue=Sum(F('orderitem__quantity') * F('orderitem__price'))
    ).order_by('-total_revenue')
    
    # Фильтрация
    search = request.GET.get('search', '')
    if search:
        products = products.filter(name__icontains=search)
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(products, 20)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    context = {
        'products': products,
        'search': search,
    }
    
    return render(request, 'dashboard/products.html', context)

@login_required
@user_passes_test(is_admin)
def dashboard_orders(request):
    """Аналитика по заказам"""
    
    orders = Order.objects.select_related('user').order_by('-created_at')
    
    # Фильтры
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)
    
    date_from = request.GET.get('date_from', '')
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    
    date_to = request.GET.get('date_to', '')
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    # Пагинация
    from django.core.paginator import Paginator
    paginator = Paginator(orders, 25)
    page = request.GET.get('page')
    orders = paginator.get_page(page)
    
    context = {
        'orders': orders,
        'status': status,
        'date_from': date_from,
        'date_to': date_to,
    }
    
    return render(request, 'dashboard/orders.html', context)

@login_required
@user_passes_test(is_admin)
def export_orders_excel(request):
    """Экспорт заказов в Excel"""
    
    # Получаем данные
    orders = Order.objects.select_related('user').order_by('-created_at')
    
    # Применяем фильтры
    status = request.GET.get('status', '')
    if status:
        orders = orders.filter(status=status)
    
    date_from = request.GET.get('date_from', '')
    if date_from:
        orders = orders.filter(created_at__date__gte=date_from)
    
    date_to = request.GET.get('date_to', '')
    if date_to:
        orders = orders.filter(created_at__date__lte=date_to)
    
    # Создаем DataFrame
    data = []
    for order in orders:
        data.append({
            'ID заказа': order.id,
            'Пользователь': order.user.username if order.user else 'Гость',
            'Имя': order.first_name,
            'Фамилия': order.last_name,
            'Email': order.email,
            'Телефон': order.phone,
            'Город': order.city,
            'Адрес': order.address,
            'Сумма': order.total_price,
            'Статус': order.get_status_display(),
            'Способ оплаты': order.get_payment_method_display(),
            'Дата создания': order.created_at.strftime('%d.%m.%Y %H:%M'),
            'QR код': order.qr_code or '',
            'Оплачен': 'Да' if order.paid else 'Нет'
        })
    
    df = pd.DataFrame(data)
    
    # Создаем Excel файл
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Заказы', index=False)
        
        # Получаем доступ к листу для форматирования
        worksheet = writer.sheets['Заказы']
        
        # Настраиваем ширину колонок
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    # Создаем ответ
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=orders_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return response

@login_required
@user_passes_test(is_admin)
def export_products_excel(request):
    """Экспорт товаров в Excel"""
    
    # Получаем данные
    products = Product.objects.annotate(
        total_sold=Sum('orderitem__quantity'),
        total_revenue=Sum(F('orderitem__quantity') * F('orderitem__price'))
    ).order_by('-total_revenue')
    
    # Применяем фильтр поиска
    search = request.GET.get('search', '')
    if search:
        products = products.filter(name__icontains=search)
    
    # Создаем DataFrame
    data = []
    for product in products:
        data.append({
            'ID товара': product.id,
            'Название': product.name,
            'Категория': product.category.name,
            'Цена': product.price,
            'Количество на складе': product.stock,
            'Доступен': 'Да' if product.available else 'Нет',
            'Продано штук': product.total_sold or 0,
            'Общая выручка': product.total_revenue or 0,
            'Дата добавления': product.created_at.strftime('%d.%m.%Y'),
            'Дата обновления': product.updated_at.strftime('%d.%m.%Y')
        })
    
    df = pd.DataFrame(data)
    
    # Создаем Excel файл
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Товары', index=False)
        
        # Настраиваем ширину колонок
        worksheet = writer.sheets['Товары']
        for column in worksheet.columns:
            max_length = 0
            column_letter = column[0].column_letter
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            adjusted_width = min(max_length + 2, 50)
            worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    # Создаем ответ
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=products_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return response

@login_required
@user_passes_test(is_admin)
def export_dashboard_excel(request):
    """Экспорт всей аналитики дашборда в Excel"""
    
    # Создаем Excel файл с несколькими листами
    output = BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        
        # 1. Лист с общей статистикой
        today = timezone.now().date()
        last_7_days = today - timedelta(days=7)
        last_30_days = today - timedelta(days=30)
        
        total_orders = Order.objects.count()
        total_revenue = Order.objects.aggregate(total=Sum('total_price'))['total'] or 0
        total_products_sold = OrderItem.objects.aggregate(total=Sum('quantity'))['total'] or 0
        total_customers = Order.objects.values('user').distinct().count()
        avg_order_value = Order.objects.aggregate(avg=Avg('total_price'))['avg'] or 0
        
        today_orders = Order.objects.filter(created_at__date=today).count()
        today_revenue = Order.objects.filter(created_at__date=today).aggregate(total=Sum('total_price'))['total'] or 0
        
        week_orders = Order.objects.filter(created_at__date__gte=last_7_days).count()
        week_revenue = Order.objects.filter(created_at__date__gte=last_7_days).aggregate(total=Sum('total_price'))['total'] or 0
        
        month_orders = Order.objects.filter(created_at__date__gte=last_30_days).count()
        month_revenue = Order.objects.filter(created_at__date__gte=last_30_days).aggregate(total=Sum('total_price'))['total'] or 0
        
        # Новые и постоянные клиенты
        new_customers = Order.objects.filter(
            created_at__date__gte=last_30_days
        ).values('user').distinct().count()
        
        returning_customers = Order.objects.values('user').annotate(
            order_count=Count('id')
        ).filter(order_count__gt=1).count()
        
        customer_ltv = total_revenue / total_customers if total_customers > 0 else 0
        
        # Остатки на складе
        inventory_stats = Product.objects.aggregate(
            total_products=Count('id'),
            total_stock=Sum('stock'),
            out_of_stock=Count('id', filter=Q(stock=0))
        )
        
        # Время обработки
        processing_times = []
        for order in Order.objects.filter(
            status__in=['confirmed', 'shipped', 'delivered']
        ).select_related('user'):
            if order.updated_at and order.created_at:
                processing_hours = (order.updated_at - order.created_at).total_seconds() / 3600
                processing_times.append(processing_hours)
        
        avg_processing_time = sum(processing_times) / len(processing_times) if processing_times else 0
        
        # Общая статистика
        general_stats = [
            ['Показатель', 'Значение'],
            ['Общая выручка', total_revenue],
            ['Средний чек', avg_order_value],
            ['LTV клиента', customer_ltv],
            ['Всего заказов', total_orders],
            ['Всего клиентов', total_customers],
            ['Новых клиентов (30дн)', new_customers],
            ['Постоянных клиентов', returning_customers],
            ['Всего продано товаров', total_products_sold],
            ['Всего товаров в каталоге', inventory_stats['total_products']],
            ['Товаров нет в наличии', inventory_stats['out_of_stock']],
            ['Среднее время обработки заказа (часы)', round(avg_processing_time, 2)],
            ['Заказов сегодня', today_orders],
            ['Выручка сегодня', today_revenue],
            ['Заказов за 7 дней', week_orders],
            ['Выручка за 7 дней', week_revenue],
            ['Заказов за 30 дней', month_orders],
            ['Выручка за 30 дней', month_revenue],
        ]
        
        df_general = pd.DataFrame(general_stats[1:], columns=general_stats[0])
        df_general.to_excel(writer, sheet_name='Общая статистика', index=False)
        
        # 2. Лист с заказами
        orders_data = []
        for order in Order.objects.select_related('user').order_by('-created_at'):
            orders_data.append({
                'ID заказа': order.id,
                'Пользователь': order.user.username if order.user else 'Гость',
                'Имя': order.first_name,
                'Фамилия': order.last_name,
                'Email': order.email,
                'Телефон': order.phone,
                'Город': order.city,
                'Адрес': order.address,
                'Сумма': order.total_price,
                'Статус': order.get_status_display(),
                'Способ оплаты': order.get_payment_method_display(),
                'Оплачен': 'Да' if order.paid else 'Нет',
                'QR код': order.qr_code or '',
                'Дата создания': order.created_at.strftime('%d.%m.%Y %H:%M'),
                'Дата обновления': order.updated_at.strftime('%d.%m.%Y %H:%M') if order.updated_at else '',
            })
        
        df_orders = pd.DataFrame(orders_data)
        df_orders.to_excel(writer, sheet_name='Заказы', index=False)
        
        # 3. Лист с товарами
        products_data = []
        for product in Product.objects.annotate(
            total_sold=Sum('orderitem__quantity'),
            total_revenue=Sum(F('orderitem__quantity') * F('orderitem__price'))
        ).order_by('-total_revenue'):
            products_data.append({
                'ID товара': product.id,
                'Название': product.name,
                'Категория': product.category.name,
                'Цена': product.price,
                'Количество на складе': product.stock,
                'Доступен': 'Да' if product.available else 'Нет',
                'Продано штук': product.total_sold or 0,
                'Общая выручка': product.total_revenue or 0,
                'Дата добавления': product.created_at.strftime('%d.%m.%Y'),
                'Дата обновления': product.updated_at.strftime('%d.%m.%Y')
            })
        
        df_products = pd.DataFrame(products_data)
        df_products.to_excel(writer, sheet_name='Товары', index=False)
        
        # 4. Лист с топ товарами
        top_products_data = []
        top_products = OrderItem.objects.values(
            'product__name', 'product__id'
        ).annotate(
            total_sold=Sum('quantity'),
            total_revenue=Sum(F('quantity') * F('price'))
        ).order_by('-total_sold')[:20]
        
        for i, product in enumerate(top_products, 1):
            top_products_data.append({
                'Место': i,
                'Название товара': product['product__name'],
                'Продано штук': product['total_sold'],
                'Общая выручка': product['total_revenue']
            })
        
        df_top = pd.DataFrame(top_products_data)
        df_top.to_excel(writer, sheet_name='Топ товары', index=False)
        
        # 5. Лист со статистикой по статусам
        status_stats = Order.objects.values('status').annotate(
            count=Count('id')
        ).order_by('status')
        
        # Статусы заказов
        STATUS_CHOICES = {
            'pending': 'В обработке',
            'confirmed': 'Подтвержден',
            'shipped': 'Отправлен',
            'delivered': 'Доставлен',
            'cancelled': 'Отменен'
        }
        
        status_data = []
        for stat in status_stats:
            status_data.append({
                'Статус': STATUS_CHOICES.get(stat['status'], stat['status']),
                'Количество': stat['count'],
                'Процент': round(stat['count'] / total_orders * 100, 2) if total_orders > 0 else 0
            })
        
        df_status = pd.DataFrame(status_data)
        df_status.to_excel(writer, sheet_name='Статусы заказов', index=False)
        
        # 6. Лист с методами оплаты
        PAYMENT_CHOICES = {
            'cash': 'Наличные',
            'card': 'Карта',
            'qr': 'QR код'
        }
        
        payment_stats = Order.objects.values('payment_method').annotate(
            count=Count('id'),
            total=Sum('total_price')
        ).order_by('-total')
        
        payment_data = []
        for stat in payment_stats:
            payment_data.append({
                'Способ оплаты': PAYMENT_CHOICES.get(stat['payment_method'], stat['payment_method']),
                'Количество заказов': stat['count'],
                'Общая сумма': stat['total'],
                'Процент': round(stat['count'] / total_orders * 100, 2) if total_orders > 0 else 0
            })
        
        df_payment = pd.DataFrame(payment_data)
        df_payment.to_excel(writer, sheet_name='Методы оплаты', index=False)
        
        # 7. Лист с графиком продаж за 30 дней
        sales_chart_data = []
        for i in range(30):
            date = today - timedelta(days=i)
            daily_orders = Order.objects.filter(created_at__date=date).count()
            daily_revenue = Order.objects.filter(created_at__date=date).aggregate(total=Sum('total_price'))['total'] or 0
            sales_chart_data.append({
                'Дата': date.strftime('%d.%m.%Y'),
                'Заказы': daily_orders,
                'Выручка': daily_revenue
            })
        sales_chart_data.reverse()
        
        df_chart = pd.DataFrame(sales_chart_data)
        df_chart.to_excel(writer, sheet_name='График продаж', index=False)
        
        # Настраиваем ширину колонок для всех листов
        for sheet_name in writer.sheets:
            worksheet = writer.sheets[sheet_name]
            for column in worksheet.columns:
                max_length = 0
                column_letter = column[0].column_letter
                for cell in column:
                    try:
                        if len(str(cell.value)) > max_length:
                            max_length = len(str(cell.value))
                    except:
                        pass
                adjusted_width = min(max_length + 2, 50)
                worksheet.column_dimensions[column_letter].width = adjusted_width
    
    output.seek(0)
    
    # Создаем ответ
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=dashboard_analytics_{datetime.now().strftime("%Y%m%d_%H%M%S")}.xlsx'
    
    return response
