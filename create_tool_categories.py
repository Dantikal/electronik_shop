import os
import django

# Устанавливаем настройки Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'constr_store.settings')
django.setup()

from shop.models import Category

def create_tool_categories():
    """Создает начальные категории инструментов"""
    
    categories_data = [
        {
            'name': 'Болгарки',
            'slug': 'bulgarki',
            'description': 'Угловые шлифовальные машины для различных работ'
        },
        {
            'name': 'Отвертки',
            'slug': 'otvertki',
            'description': 'Ручные и электрические отвертки'
        },
        {
            'name': 'Шуруповерты',
            'slug': 'shurupoverty',
            'description': 'Аккумуляторные и сетевые шуруповерты'
        },
        {
            'name': 'Перфораторы',
            'slug': 'perforatory',
            'description': 'Профессиональные перфораторы для сверления'
        },
        {
            'name': 'Дрели',
            'slug': 'dreli',
            'description': 'Электрические дрели для сверления и смешивания'
        },
    ]
    
    created_count = 0
    for category_data in categories_data:
        category, created = Category.objects.get_or_create(
            slug=category_data['slug'],
            defaults=category_data
        )
        if created:
            created_count += 1
            print(f"Создана категория: {category.name}")
        else:
            print(f"Категория уже существует: {category.name}")
    
    print(f"\nВсего создано категорий: {created_count}")

if __name__ == '__main__':
    create_tool_categories()
