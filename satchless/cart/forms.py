from django import forms
from django.utils.translation import ugettext as _

from . import models
from ..forms.widgets import DecimalInput
from ..product.forms import variant_form_for_product

class QuantityForm(object):
    def clean_quantity(self):
        val = self.cleaned_data['quantity']
        if val < 0:
            raise forms.ValidationError(_("Quantity cannot be negative"))
        return val

class AddToCartForm(forms.Form, QuantityForm):
    """Form that adds a Variant quantity to a Cart.
    It may be replaced by more advanced one, performing some checks, e.g.
    verifying the number of items in stock."""
    quantity = forms.DecimalField(initial=1)
    typ = forms.CharField(max_length=100, widget=forms.HiddenInput())

    def __init__(self, data=None, *args, **kwargs):
        typ = kwargs.pop('typ')
        if data and data.get('typ') != typ:
            data = None
        self.cart = kwargs.pop('cart', None)
        super(AddToCartForm, self).__init__(data=data, *args, **kwargs)
        self.fields['typ'].initial = typ

    def clean(self):
        data = super(AddToCartForm, self).clean()
        if 'quantity' in data:
            qty = data['quantity']
            add_result = self.cart.add_quantity(self.get_variant(), qty, dry_run=True)
            if add_result.quantity_delta < qty:
                raise forms.ValidationError(add_result.reason)
        return data

    def save(self):
        return self.cart.add_quantity(self.get_variant(), self.cleaned_data['quantity'])


class EditCartItemForm(forms.ModelForm, QuantityForm):
    class Meta:
        model = models.CartItem
        fields = ('quantity',)
        widgets = {
            'quantity': DecimalInput(min_decimal_places=0),
        }

    def clean_quantity(self):
        qty = super(EditCartItemForm, self).clean_quantity()
        qty_result = self.instance.cart.set_quantity(self.instance.variant, qty, dry_run=True)
        if qty_result.new_quantity < qty:
            raise forms.ValidationError(qty_result.reason)
        return qty_result.new_quantity

    def save(self, commit=True):
        """Do not call the original save() method, but use cart.set_quantity() instead."""
        self.instance.cart.set_quantity(self.instance.variant, self.cleaned_data['quantity'])

def add_to_cart_variant_form_for_product(product,
                                         addtocart_formclass=AddToCartForm):
    variant_formclass = variant_form_for_product(product)
    class AddVariantToCartForm(addtocart_formclass, variant_formclass):
        pass
    return AddVariantToCartForm
