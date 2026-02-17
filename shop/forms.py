from django import forms
from .models import Product, Category, Review


class ProductFilterForm(forms.Form):
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="Все категории",
        label="Категория"
    )
    brand = forms.CharField(
        required=False,
        label="Бренд"
    )
    price_min = forms.DecimalField(
        required=False,
        min_value=0,
        label="Минимальная цена"
    )
    price_max = forms.DecimalField(
        required=False,
        min_value=0,
        label="Максимальная цена"
    )
    in_stock = forms.BooleanField(
        required=False,
        label="Только в наличии"
    )
    sort_by = forms.ChoiceField(
        choices=[
            ('created_at', 'Новинки'),
            ('price', 'Цена: по возрастанию'),
            ('-price', 'Цена: по убыванию'),
            ('name', 'Название: А-Я'),
            ('-name', 'Название: Я-А'),
        ],
        required=False,
        label="Сортировка"
    )


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['rating', 'text']
        widgets = {
            'rating': forms.RadioSelect(choices=[(i, f'{i} звезд') for i in range(1, 6)]),
            'text': forms.Textarea(attrs={'rows': 4, 'placeholder': 'Напишите ваш отзыв...'}),
        }
        labels = {
            'rating': 'Оценка',
            'text': 'Текст отзыва',
        }


class CartAddProductForm(forms.Form):
    quantity = forms.IntegerField(
        min_value=1,
        initial=1,
        label="Количество"
    )
    override = forms.BooleanField(
        required=False,
        initial=False,
        widget=forms.HiddenInput
    )
