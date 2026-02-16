from django.db import models
from django.contrib.auth.models import User
from django.urls import reverse
from django.utils.text import slugify


class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Название категории")
    slug = models.SlugField(max_length=100, unique=True, verbose_name="URL")
    description = models.TextField(blank=True, verbose_name="Описание")
    image = models.ImageField(upload_to='categories/', blank=True, verbose_name="Изображение")
    image_data = models.TextField(blank=True, null=True, verbose_name="Изображение в Base64")
    # Test deploy - проверка что данные не исчезают
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Конставар"
        verbose_name_plural = "Конставары"
        ordering = ['name']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:category_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        # Сначала сохраняем объект чтобы получить файл
        super().save(*args, **kwargs)
        
        # Затем конвертируем изображение в Base64
        if self.image and hasattr(self.image, 'path'):
            import base64
            
            try:
                # Читаем сохраненный файл
                with open(self.image.path, 'rb') as f:
                    image_data = f.read()
                
                # Конвертируем в Base64
                self.image_data = base64.b64encode(image_data).decode('utf-8')
                
                # Сохраняем только image_data поле
                super().save(update_fields=['image_data'])
            except Exception as e:
                print(f"Ошибка чтения изображения: {e}")
        
        if not self.slug:
            self.slug = slugify(self.name)
            super().save(update_fields=['slug'])
    
    def get_image_url(self):
        """Возвращает URL изображения или Base64 data URL"""
        # Сначала проверяем Base64 данные
        if self.image_data:
            return f"data:image/jpeg;base64,{self.image_data}"
        # Если Base64 нет, пробуем файл
        elif self.image and self.image.url:
            return self.image.url
        return None


class Product(models.Model):
    name = models.CharField(max_length=200, verbose_name="Название товара")
    slug = models.SlugField(max_length=200, unique=True, verbose_name="URL")
    description = models.TextField(verbose_name="Описание")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена")
    stock = models.PositiveIntegerField(default=0, verbose_name="Количество на складе")
    available = models.BooleanField(default=True, verbose_name="Доступен")
    category = models.ForeignKey(Category, on_delete=models.CASCADE, verbose_name="Категория")
    image = models.ImageField(upload_to='products/', blank=True, verbose_name="Изображение")
    image_data = models.TextField(blank=True, null=True, verbose_name="Изображение в Base64")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")

    class Meta:
        verbose_name = "Товар"
        verbose_name_plural = "Товары"
        ordering = ['-created_at']

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_detail', kwargs={'slug': self.slug})

    def save(self, *args, **kwargs):
        # Сначала сохраняем объект чтобы получить файл
        super().save(*args, **kwargs)
        
        # Затем конвертируем изображение в Base64
        if self.image and hasattr(self.image, 'path'):
            from django.core.files.base import ContentFile
            import base64
            
            try:
                # Читаем сохраненный файл
                with open(self.image.path, 'rb') as f:
                    image_data = f.read()
                
                # Конвертируем в Base64
                self.image_data = base64.b64encode(image_data).decode('utf-8')
                
                # Сохраняем только image_data поле
                super().save(update_fields=['image_data'])
            except Exception as e:
                print(f"Ошибка чтения изображения: {e}")
        
        if not self.slug:
            self.slug = slugify(self.name)
            super().save(update_fields=['slug'])
    
    def get_image_url(self):
        """Возвращает URL изображения или Base64 data URL"""
        # Сначала проверяем Base64 данные
        if self.image_data:
            return f"data:image/jpeg;base64,{self.image_data}"
        # Если Base64 нет, пробуем файл
        elif self.image and self.image.url:
            return self.image.url
        return None

    @property
    def is_in_stock(self):
        return self.stock > 0 and self.available


class Cart(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Корзина"
        verbose_name_plural = "Корзины"

    def __str__(self):
        return f"Корзина {self.user.username if self.user else self.session_key}"

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Элемент корзины"
        verbose_name_plural = "Элементы корзины"
        unique_together = ['cart', 'product']

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

    @property
    def total_price(self):
        return self.product.price * self.quantity


class Order(models.Model):
    STATUS_CHOICES = [
        ('pending', 'В обработке'),
        ('confirmed', 'Подтвержден'),
        ('shipped', 'Отправлен'),
        ('delivered', 'Доставлен'),
        ('cancelled', 'Отменен'),
    ]
    
    PAYMENT_CHOICES = [
        ('qr_code', 'QR-код (мБанк)'),
        ('telegram', 'Написать в Telegram'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, verbose_name="Пользователь")
    first_name = models.CharField(max_length=50, verbose_name="Имя")
    last_name = models.CharField(max_length=50, verbose_name="Фамилия")
    email = models.EmailField(verbose_name="Email")
    phone = models.CharField(max_length=20, verbose_name="Телефон")
    address = models.TextField(verbose_name="Адрес доставки")
    postal_code = models.CharField(max_length=10, blank=True, verbose_name="Почтовый индекс")
    city = models.CharField(max_length=100, verbose_name="Город")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    updated_at = models.DateTimeField(auto_now=True, verbose_name="Дата обновления")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending', verbose_name="Статус")
    total_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Общая сумма")
    paid = models.BooleanField(default=False, verbose_name="Оплачен")
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES, default='qr_code', verbose_name="Способ оплаты")
    qr_code = models.CharField(max_length=50, unique=True, blank=True, null=True, verbose_name="QR-код")
    qr_payment_data = models.TextField(blank=True, null=True, verbose_name="Данные для QR-оплаты")

    class Meta:
        verbose_name = "Заказ"
        verbose_name_plural = "Заказы"
        ordering = ['-created_at']

    def __str__(self):
        return f"Заказ #{self.id} - {self.user.username}"

    def get_absolute_url(self):
        return reverse('shop:order_detail', kwargs={'pk': self.pk})
    
    def generate_qr_code(self):
        """Генерирует уникальный код для заказа"""
        import random
        import string
        
        if not self.qr_code:
            # Генерируем уникальный код формата CHP-XXX
            random_num = ''.join(random.choices(string.digits, k=3))
            self.qr_code = f"CHP-{random_num}"
            self.save()
        
        return self.qr_code
    
    def get_payment_description(self):
        """Возвращает описание платежа для QR-кода"""
        return str(int(float(self.total_price)))


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Цена", default=0)
    quantity = models.PositiveIntegerField(verbose_name="Количество", default=1)

    class Meta:
        verbose_name = "Элемент заказа"
        verbose_name_plural = "Элементы заказа"

    def __str__(self):
        return f"{self.product.name} - {self.quantity}"

    @property
    def total_price(self):
        if self.price is None or self.quantity is None:
            return 0
        return self.price * self.quantity


class BankAccount(models.Model):
    """Модель для хранения банковских реквизитов магазина"""
    bank_name = models.CharField(max_length=100, verbose_name="Название банка")
    account_number = models.CharField(max_length=50, verbose_name="Номер счета")
    qr_code_image = models.ImageField(upload_to='qr_codes/', verbose_name="QR-код счета")
    qr_code_data = models.TextField(blank=True, null=True, verbose_name="QR-код в Base64")
    is_active = models.BooleanField(default=True, verbose_name="Активен")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")

    class Meta:
        verbose_name = "Банковский счет"
        verbose_name_plural = "Банковские счета"

    def __str__(self):
        return f"{self.bank_name} - {self.account_number}"

    @classmethod
    def get_active(cls):
        """Получить активный банковский счет"""
        return cls.objects.filter(is_active=True).first()

    def save(self, *args, **kwargs):
        # Сначала сохраняем объект чтобы получить файл
        super().save(*args, **kwargs)
        
        # Затем конвертируем QR-код в Base64
        if self.qr_code_image and hasattr(self.qr_code_image, 'path'):
            import base64
            
            try:
                # Читаем сохраненный файл
                with open(self.qr_code_image.path, 'rb') as f:
                    qr_data = f.read()
                
                # Конвертируем в Base64
                self.qr_code_data = base64.b64encode(qr_data).decode('utf-8')
                
                # Сохраняем только qr_code_data поле
                super().save(update_fields=['qr_code_data'])
            except Exception as e:
                print(f"Ошибка чтения QR-кода: {e}")
    
    def get_qr_url(self):
        """Возвращает URL QR-кода или Base64 data URL"""
        # Сначала проверяем Base64 данные
        if self.qr_code_data:
            return f"data:image/png;base64,{self.qr_code_data}"
        # Если Base64 нет, пробуем файл
        elif self.qr_code_image and self.qr_code_image.url:
            return self.qr_code_image.url
        return None


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='reviews')
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=[(i, i) for i in range(1, 6)], verbose_name="Оценка")
    text = models.TextField(verbose_name="Текст отзыва")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Дата создания")
    approved = models.BooleanField(default=False, verbose_name="Одобрен")

    class Meta:
        verbose_name = "Отзыв"
        verbose_name_plural = "Отзывы"
        unique_together = ['product', 'user']
        ordering = ['-created_at']

    def __str__(self):
        return f"Отзыв {self.user.username} на {self.product.name}"
