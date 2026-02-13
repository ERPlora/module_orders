from django import forms
from django.utils.translation import gettext_lazy as _

from .models import Order, OrderItem, OrderModifier, KitchenStation


class OrderForm(forms.ModelForm):
    class Meta:
        model = Order
        fields = ['order_type', 'table', 'customer', 'priority', 'round_number', 'notes']
        widgets = {
            'order_type': forms.Select(attrs={'class': 'select'}),
            'table': forms.Select(attrs={'class': 'select'}),
            'customer': forms.Select(attrs={'class': 'select'}),
            'priority': forms.Select(attrs={'class': 'select'}),
            'round_number': forms.NumberInput(attrs={
                'class': 'input', 'min': '1',
            }),
            'notes': forms.Textarea(attrs={
                'class': 'textarea', 'rows': 3,
                'placeholder': _('Order notes'),
            }),
        }


class OrderItemForm(forms.ModelForm):
    class Meta:
        model = OrderItem
        fields = ['product', 'product_name', 'unit_price', 'quantity', 'modifiers', 'notes', 'seat_number']
        widgets = {
            'product': forms.Select(attrs={'class': 'select'}),
            'product_name': forms.TextInput(attrs={
                'class': 'input', 'placeholder': _('Product name'),
            }),
            'unit_price': forms.NumberInput(attrs={
                'class': 'input', 'step': '0.01', 'min': '0',
            }),
            'quantity': forms.NumberInput(attrs={
                'class': 'input', 'min': '1', 'value': '1',
            }),
            'modifiers': forms.TextInput(attrs={
                'class': 'input',
                'placeholder': _('e.g. No onions, Extra cheese'),
            }),
            'notes': forms.Textarea(attrs={
                'class': 'textarea', 'rows': 2,
                'placeholder': _('Special instructions'),
            }),
            'seat_number': forms.NumberInput(attrs={
                'class': 'input', 'min': '1',
                'placeholder': _('Seat #'),
            }),
        }


class OrderModifierForm(forms.ModelForm):
    class Meta:
        model = OrderModifier
        fields = ['name', 'price']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input', 'placeholder': _('Modifier name'),
            }),
            'price': forms.NumberInput(attrs={
                'class': 'input', 'step': '0.01', 'min': '0',
            }),
        }


class KitchenStationForm(forms.ModelForm):
    class Meta:
        model = KitchenStation
        fields = ['name', 'name_es', 'description', 'color', 'icon', 'printer_name', 'sort_order', 'is_active']
        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'input', 'placeholder': _('Station name'),
            }),
            'name_es': forms.TextInput(attrs={
                'class': 'input', 'placeholder': _('Spanish name'),
            }),
            'description': forms.Textarea(attrs={
                'class': 'textarea', 'rows': 2,
            }),
            'color': forms.TextInput(attrs={
                'class': 'input', 'type': 'color',
            }),
            'icon': forms.TextInput(attrs={
                'class': 'input', 'placeholder': 'flame-outline',
            }),
            'printer_name': forms.TextInput(attrs={
                'class': 'input', 'placeholder': _('System printer name'),
            }),
            'sort_order': forms.NumberInput(attrs={
                'class': 'input', 'min': '0',
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'toggle'}),
        }


class OrderFilterForm(forms.Form):
    q = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'input',
            'placeholder': _('Search orders...'),
        }),
    )
    status = forms.ChoiceField(
        required=False,
        choices=[('', _('All Statuses'))] + list(Order.STATUS_CHOICES),
        widget=forms.Select(attrs={'class': 'select'}),
    )
    order_type = forms.ChoiceField(
        required=False,
        choices=[('', _('All Types'))] + list(Order.ORDER_TYPE_CHOICES),
        widget=forms.Select(attrs={'class': 'select'}),
    )
    date_from = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
    )
    date_to = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={'class': 'input', 'type': 'date'}),
    )
