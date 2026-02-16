from django.contrib import admin
from django.db.models import Count
from .models import Category, Product, Cart, CartItem, Order, OrderItem, Review, BankAccount


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'slug', 'product_count', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at',)
    
    def product_count(self, obj):
        count = obj.product_set.count()
        return count if count > 0 else 'Нет товаров'
    product_count.short_description = 'Количество товаров'


class CartItemInline(admin.TabularInline):
    model = CartItem
    extra = 0
    readonly_fields = ('created_at',)


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ('user', 'session_key', 'total_items', 'total_price', 'created_at')
    list_filter = ('created_at',)
    search_fields = ('user__username', 'session_key')
    readonly_fields = ('created_at', 'updated_at')
    inlines = [CartItemInline]


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'price', 'quantity', 'total_price')
    
    def total_price(self, obj):
        return obj.total_price
    total_price.short_description = 'Сумма'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'user', 'status', 'total_price', 'paid', 'qr_code', 'created_at')
    list_filter = ('status', 'paid', 'payment_method', 'created_at')
    search_fields = ('user__username', 'email', 'phone')
    readonly_fields = ('created_at', 'updated_at', 'total_price')
    inlines = [OrderItemInline]
    
    fieldsets = (
        ('Информация о клиенте', {
            'fields': ('user', 'first_name', 'last_name', 'email', 'phone')
        }),
        ('Адрес доставки', {
            'fields': ('address', 'postal_code', 'city')
        }),
        ('Информация о заказе', {
            'fields': ('status', 'total_price', 'paid', 'payment_method', 'qr_code')
        }),
    )


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'price', 'stock', 'available', 'created_at')
    list_filter = ('category', 'available', 'created_at')
    search_fields = ('name', 'description', 'category__name')
    list_editable = ('price', 'stock', 'available')
    prepopulated_fields = {'slug': ('name',)}
    readonly_fields = ('created_at', 'updated_at')
    ordering = ('-created_at',)
    
    def changelist_view(self, request, extra_context=None):
        response = super().changelist_view(request, extra_context)
        try:
            qs = response.context_data['cl'].queryset
            if qs.count() == 0:
                response.context_data['cl'].result_list = []
                response.context_data['cl'].result_count = 0
        except:
            pass
        return response
    
    fieldsets = (
        ('Основная информация', {
            'fields': ('name', 'slug', 'category', 'description')
        }),
        ('Цена и наличие', {
            'fields': ('price', 'stock', 'available')
        }),
        ('Изображение', {
            'fields': ('image',)
        }),
        ('Метаданные', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('category')


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('product', 'user', 'rating', 'approved', 'created_at')
    list_filter = ('rating', 'approved', 'created_at')
    search_fields = ('product__name', 'user__username', 'text')
    list_editable = ('approved',)
    readonly_fields = ('created_at',)
    
    actions = ['approve_reviews', 'disapprove_reviews']
    
    def approve_reviews(self, request, queryset):
        queryset.update(approved=True)
    approve_reviews.short_description = 'Одобрить выбранные отзывы'
    
    def disapprove_reviews(self, request, queryset):
        queryset.update(approved=False)
    disapprove_reviews.short_description = 'Отклонить выбранные отзывы'


@admin.register(BankAccount)
class BankAccountAdmin(admin.ModelAdmin):
    list_display = ('bank_name', 'account_number', 'is_active', 'created_at')
    list_filter = ('is_active', 'created_at', 'bank_name')
    search_fields = ('bank_name', 'account_number')
    readonly_fields = ('created_at',)
    
    def get_queryset(self, request):
        return super().get_queryset(request).order_by('-created_at')
