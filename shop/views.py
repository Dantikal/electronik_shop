from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.db.models import Q, Count, Avg
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views.generic import ListView, DetailView, CreateView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse_lazy
from django.conf import settings
import asyncio

from .models import Product, Category, Cart, CartItem, Order, OrderItem, Review, BankAccount
from .forms import ProductFilterForm, ReviewForm, CartAddProductForm


def home(request):
    categories = Category.objects.annotate(product_count=Count('product'))[:6]
    featured_products = Product.objects.filter(available=True)[:8]
    new_products = Product.objects.filter(available=True).order_by('-created_at')[:8]
    
    context = {
        'categories': categories,
        'featured_products': featured_products,
        'new_products': new_products,
    }
    return render(request, 'shop/home.html', context)


class ProductListView(ListView):
    model = Product
    template_name = 'shop/product_list.html'
    context_object_name = 'products'
    paginate_by = 12

    def get_queryset(self):
        queryset = Product.objects.filter(available=True)
        
        form = ProductFilterForm(self.request.GET)
        if form.is_valid():
            if form.cleaned_data['category']:
                queryset = queryset.filter(category=form.cleaned_data['category'])
            if form.cleaned_data['price_min']:
                queryset = queryset.filter(price__gte=form.cleaned_data['price_min'])
            if form.cleaned_data['price_max']:
                queryset = queryset.filter(price__lte=form.cleaned_data['price_max'])
            if form.cleaned_data['in_stock']:
                queryset = queryset.filter(stock__gt=0)
            if form.cleaned_data['sort_by']:
                queryset = queryset.order_by(form.cleaned_data['sort_by'])
        
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['filter_form'] = ProductFilterForm(self.request.GET)
        context['categories'] = Category.objects.all()
        return context


class ProductDetailView(DetailView):
    model = Product
    template_name = 'shop/product_detail.html'
    context_object_name = 'product'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['cart_product_form'] = CartAddProductForm()
        
        # Получаем похожие товары из той же категории
        context['related_products'] = Product.objects.filter(
            category=self.object.category,
            available=True
        ).exclude(id=self.object.id)[:4]
        
        # Получаем отзывы
        context['reviews'] = self.object.reviews.filter(approved=True)
        context['review_form'] = ReviewForm()
        
        # Проверял ли пользователь товар
        if self.request.user.is_authenticated:
            context['user_review'] = self.object.reviews.filter(user=self.request.user).first()
        
        return context


class CategoryDetailView(DetailView):
    model = Category
    template_name = 'shop/category_detail.html'
    context_object_name = 'category'

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        products = Product.objects.filter(category=self.object, available=True)
        
        paginator = Paginator(products, 12)
        page = self.request.GET.get('page')
        context['products'] = paginator.get_page(page)
        
        return context


def get_or_create_cart(request):
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        session_key = request.session.session_key
        if not session_key:
            request.session.create()
            session_key = request.session.session_key
        cart, created = Cart.objects.get_or_create(session_key=session_key)
    return cart


def cart_detail(request):
    cart = get_or_create_cart(request)
    return render(request, 'shop/cart_detail.html', {'cart': cart})


@require_POST
def cart_add(request, product_id):
    cart = get_or_create_cart(request)
    product = get_object_or_404(Product, id=product_id)
    form = CartAddProductForm(request.POST)
    
    if form.is_valid():
        quantity = form.cleaned_data['quantity']
        override = form.cleaned_data['override']
        
        cart_item, created = CartItem.objects.get_or_create(
            cart=cart,
            product=product,
            defaults={'quantity': quantity}
        )
        
        if not created:
            if override:
                cart_item.quantity = quantity
            else:
                cart_item.quantity += quantity
            cart_item.save()
    
    return redirect('shop:cart_detail')


@require_POST
def cart_remove(request, product_id):
    cart = get_or_create_cart(request)
    product = get_object_or_404(Product, id=product_id)
    CartItem.objects.filter(cart=cart, product=product).delete()
    return redirect('shop:cart_detail')


@login_required
def checkout(request):
    cart = get_or_create_cart(request)
    
    if not cart.items.exists():
        messages.error(request, 'Ваша корзина пуста')
        return redirect('shop:cart_detail')
    
    if request.method == 'POST':
        # Создание заказа
        payment_method = request.POST.get('payment_method', 'qr_code')
        
        if payment_method == 'telegram':
            # Отправляем корзину в Telegram
            from telegram_bot.bot import send_cart_to_telegram
            
            user_info = {
                'first_name': request.user.first_name,
                'last_name': request.user.last_name,
                'email': request.user.email,
                'phone': request.POST.get('phone'),
                'address': request.POST.get('address'),
                'city': request.POST.get('city'),
            }
            
            # Отправляем в Telegram
            send_cart_to_telegram(cart, user_info)
            
            # Создаем заказ со статусом "В обработке"
            order = Order.objects.create(
                user=request.user,
                first_name=request.user.first_name,
                last_name=request.user.last_name,
                email=request.user.email,
                phone=request.POST.get('phone'),
                address=request.POST.get('address'),
                city=request.POST.get('city'),
                postal_code=request.POST.get('postal_code', ''),
                total_price=cart.total_price,
                payment_method=payment_method
            )
            
            # Создаем элементы заказа
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                )
            
            # Очищаем корзину
            cart.items.all().delete()
            
            messages.success(request, f'Заказ #{order.id} отправлен в Telegram! Ожидайте связи с менеджером.')
            return redirect('shop:order_detail', pk=order.id)
        else:
            # Стандартное оформление через QR-код
            order = Order.objects.create(
                user=request.user,
                first_name=request.user.first_name,
                last_name=request.user.last_name,
                email=request.user.email,
                phone=request.POST.get('phone'),
                address=request.POST.get('address'),
                city=request.POST.get('city'),
                postal_code=request.POST.get('postal_code', ''),
                total_price=cart.total_price,
                payment_method=payment_method
            )
            
            # Создаем элементы заказа
            for item in cart.items.all():
                OrderItem.objects.create(
                    order=order,
                    product=item.product,
                    quantity=item.quantity,
                    price=item.product.price
                )
            
            # Генерируем QR-код для заказа
            order.generate_qr_code()
            
            # Очищаем корзину
            cart.items.all().delete()
            
            # Перенаправляем на страницу QR-оплаты
            messages.success(request, f'Заказ #{order.id} успешно оформлен!')
            return redirect('shop:qr_payment', order_id=order.id)
    
    return render(request, 'shop/checkout.html', {'cart': cart})


@login_required
def order_detail(request, pk):
    order = get_object_or_404(Order, pk=pk, user=request.user)
    return render(request, 'shop/order_detail.html', {'order': order})


@login_required
def order_list(request):
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'shop/order_list.html', {'orders': orders})


@login_required
@require_POST
def add_review(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    form = ReviewForm(request.POST)
    
    if form.is_valid():
        review = form.save(commit=False)
        review.product = product
        review.user = request.user
        review.save()
        messages.success(request, 'Отзыв добавлен и будет опубликован после модерации')
    else:
        messages.error(request, 'Ошибка при добавлении отзыва')
    
    return redirect('shop:product_detail', slug=product.slug)


def search(request):
    query = request.GET.get('q')
    results = []
    
    if query:
        results = Product.objects.filter(
            Q(name__icontains=query) | Q(description__icontains=query),
            available=True
        )
    
    paginator = Paginator(results, 12)
    page = request.GET.get('page')
    products = paginator.get_page(page)
    
    return render(request, 'shop/search.html', {
        'products': products,
        'query': query
    })


@login_required
def qr_payment(request, order_id):
    """Страница с QR-кодом для оплаты заказа"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    # Генерируем уникальный код для заказа
    order.generate_qr_code()
    
    # Получаем активный банковский счет
    bank_account = BankAccount.get_active()
    
    if not bank_account:
        messages.error(request, 'QR-код оплаты временно недоступен')
        return redirect('shop:order_detail', pk=order.pk)
    
    context = {
        'order': order,
        'bank_account': bank_account,
        'payment_description': order.get_payment_description(),
    }
    
    return render(request, 'shop/qr_payment.html', context)


@login_required
def order_status_api(request, order_id):
    """API для проверки статуса заказа"""
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        print(f"Проверка статуса заказа #{order_id}: paid={order.paid}, status={order.status}")  # Отладка
        
        return JsonResponse({
            'paid': order.paid,
            'status': order.status,
            'order_id': order.id
        })
    except Exception as e:
        print(f"Ошибка в order_status_api: {e}")  # Отладка
        return JsonResponse({
            'paid': False,
            'status': 'error',
            'error': str(e)
        }, status=500)


@csrf_exempt
def generate_qr_api(request, order_id):
    """API для генерации QR-кода заказа"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Генерируем QR-код
        qr_code = order.generate_qr_code()
        
        return JsonResponse({
            'success': True,
            'qr_code': qr_code,
            'message': 'QR-код успешно сгенерирован'
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def change_payment_method_api(request, order_id):
    """API для изменения метода оплаты заказа"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Проверяем, что заказ не оплачен
        if order.paid:
            return JsonResponse({
                'success': False,
                'error': 'Нельзя изменить способ оплаты для оплаченного заказа'
            }, status=400)
        
        import json
        data = json.loads(request.body)
        new_method = data.get('payment_method')
        
        if new_method not in ['qr_code']:
            return JsonResponse({
                'success': False,
                'error': 'Неверный способ оплаты'
            }, status=400)
        
        # Изменяем способ оплаты
        order.payment_method = new_method
        order.save()
        
        # Если это QR-код, генерируем его
        if new_method == 'qr_code':
            order.generate_qr_code()
        
        return JsonResponse({
            'success': True,
            'message': f'Способ оплаты изменен на {new_method}',
            'payment_method': new_method
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)


@csrf_exempt
def notify_payment_api(request, order_id):
    """API для отправки уведомления об оплате"""
    if request.method != 'POST':
        return JsonResponse({'success': False, 'error': 'Method not allowed'}, status=405)
    
    try:
        order = get_object_or_404(Order, id=order_id, user=request.user)
        
        # Отправляем уведомление в Telegram
        try:
            from telegram_notifications_sync import send_telegram_notification_sync
            
            # Используем синхронную функцию
            success = send_telegram_notification_sync(order)
            
            if success:
                return JsonResponse({
                    'success': True,
                    'message': 'Уведомление отправлено администратору'
                })
            else:
                return JsonResponse({
                    'success': False,
                    'error': 'Не удалось отправить уведомление - Telegram bot не настроен'
                }, status=500)
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Ошибка отправки уведомления: {e}")
            return JsonResponse({
                'success': False,
                'error': f'Ошибка отправки уведомления: {str(e)}'
            }, status=500)
        
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Ошибка API notify_payment: {e}")
        return JsonResponse({
            'success': False,
            'error': f'Ошибка API: {str(e)}'
        }, status=500)
