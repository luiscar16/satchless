import decimal
from django.conf import settings
from django.test import TestCase
from django import template
import mock
from satchless.pricing import handler, Price, PricingHandler

from ..templatetags import product_prices

__all__ = ['BasicHandlerTest', 'PricingTagsTest']

class FiveZlotyPriceHandler(PricingHandler):
    """Dummy base price handler - everything has 5PLN price"""

    def get_variant_price(self, *args, **kwargs):
        return Price(net=5, gross=5, currency=u'PLN')

    def get_product_price_range(self, *args, **kwargs):
        return (Price(net=5, gross=5, currency=u'PLN'),
                Price(net=5, gross=5, currency=u'PLN'))

class NinetyPerecentTaxPriceHandler(PricingHandler):
    """Scary price handler - it counts 90% of tax for everything"""

    def _tax(self, price):
        return Price(currency=price.currency, net=price.net,
                     gross=price.gross*decimal.Decimal('1.9'))

    def get_variant_price(self, *args, **kwargs):
        price = kwargs.get('price')
        return self._tax(price)

    def get_product_price_range(self, *args, **kwargs):
        price_range = kwargs.get('price_range')
        return (self._tax(price_range[0]),
                self._tax(price_range[1]))

class TenPercentDiscountPriceHandler(PricingHandler):
    """Discount all handler"""

    def _discount(self, price):
        return Price(currency=price.currency, net=price.net*decimal.Decimal('0.9'),
                     gross=price.gross*decimal.Decimal('0.9'))

    def get_variant_price(self, *args, **kwargs):
        price = kwargs.pop('price')
        if kwargs.get('discount', True):
            return self._discount(price)
        return price

    def get_product_price_range(self, *args, **kwargs):
        price_range = kwargs.pop('price_range')
        if kwargs.get('discount', True):
            return (self._discount(price_range[0]),
                    self._discount(price_range[1]))
        return price_range

class BasicHandlerTest(TestCase):
    def setUp(self):
        self.original_pricing_handlers = settings.SATCHLESS_PRICING_HANDLERS
        settings.SATCHLESS_PRICING_HANDLERS = [FiveZlotyPriceHandler,
                                               NinetyPerecentTaxPriceHandler,
                                               TenPercentDiscountPriceHandler]
        handler.init_queue()

    def tearDown(self):
        settings.SATCHLESS_PRICING_HANDLERS = self.original_pricing_handlers
        handler.init_queue()

    def test_discounted_price(self):
        price = handler.get_variant_price(None, u'PLN', quantity=1, discount=True)
        self.assertEqual(price,
                         Price(net=5*decimal.Decimal('0.9'),
                               gross=5*decimal.Decimal('1.9')*decimal.Decimal('0.9'),
                               currency=u'PLN'))

    def test_undiscounted_price(self):
        price = handler.get_variant_price(None, u'PLN', quantity=1, discount=False)
        self.assertEqual(price,
                         Price(net=5,
                               gross=5*decimal.Decimal('1.9'),
                               currency=u'PLN'))

class PricingTagsTest(TestCase):
    def setUp(self):
        self.original_pricing_handlers = settings.SATCHLESS_PRICING_HANDLERS
        settings.SATCHLESS_PRICING_HANDLERS = [FiveZlotyPriceHandler,
                                               NinetyPerecentTaxPriceHandler,
                                               TenPercentDiscountPriceHandler]
        handler.init_queue()

    def tearDown(self):
        settings.SATCHLESS_PRICING_HANDLERS = self.original_pricing_handlers
        handler.init_queue()

    def test_undiscounted_variant_price_tag_without_asvar(self):
        token = mock.Mock()
        token.split_contents.return_value = ('variant_price', 'product',
                                             'currency=PLN', 'discount=0')
        parser = mock.Mock()
        def side_effect(arg):
            return template.Variable(arg)
        parser.compile_filter = mock.Mock(side_effect=side_effect)

        node = product_prices.variant_price(parser, token)

        #testing simple expresion
        self.assertEqual(node.item.var, 'product')
        self.assertEqual(node.kwargs['currency'].var, 'PLN')
        self.assertEqual(node.kwargs['discount'].var, '0')

        context = {'product': 'product', 'PLN': 'PLN', '0': 0}
        result = node.render(context)
        self.assertEqual(result,
                         Price(net=5,
                               gross=5*decimal.Decimal('1.9'),
                               currency=u'PLN'))

    def test_discounted_variant_price_tag_without_asvar(self):
        token = mock.Mock()
        token.split_contents.return_value = ('variant_price', 'product',
                                             'currency=PLN')
        parser = mock.Mock()
        def side_effect(arg):
            return template.Variable(arg)
        parser.compile_filter = mock.Mock(side_effect=side_effect)

        node = product_prices.variant_price(parser, token)

        #testing simple expresion
        self.assertEqual(node.item.var, 'product')
        self.assertEqual(node.kwargs['currency'].var, 'PLN')

        context = {'product': 'product', 'PLN': 'PLN', '0': 0}
        result = node.render(context)
        self.assertEqual(result,
                         Price(net=5*decimal.Decimal('0.9'),
                               gross=5*decimal.Decimal('1.9')*decimal.Decimal('0.9'),
                               currency=u'PLN'))

    def test_variant_price_tag_with_asvar(self):
        token = mock.Mock()
        token.split_contents.return_value = ('variant_price', 'product',
                                             'currency=PLN', 'as', 'price')
        parser = mock.Mock()
        def side_effect(arg):
            return template.Variable(arg)
        parser.compile_filter = mock.Mock(side_effect=side_effect)

        node = product_prices.variant_price(parser, token)
        self.assertEqual(node.item.var, 'product')
        self.assertEqual(node.kwargs['currency'].var, 'PLN')
        self.assertEqual(node.asvar, 'price')

        context = {'product': 'product', 'PLN': 'PLN', '0': 0}
        node.render(context)
        self.assertEqual(context['price'],
                         Price(net=5*decimal.Decimal('0.9'),
                               gross=5*decimal.Decimal('1.9')*decimal.Decimal('0.9'),
                               currency=u'PLN'))

    def test_undiscounted_product_price_range(self):
        token = mock.Mock()
        token.split_contents.return_value = ('product_price_range', 'product',
                                             'currency=PLN', 'discount=0', 'as',
                                             'price')
        parser = mock.Mock()
        def side_effect(arg):
            return template.Variable(arg)
        parser.compile_filter = mock.Mock(side_effect=side_effect)

        node = product_prices.product_price_range(parser, token)

        context = {'product': 'product', 'PLN': 'PLN', '0': 0}
        node.render(context)
        self.assertEqual(context['price']['min'],
                         Price(net=5, gross=5*decimal.Decimal('1.9'),
                         currency=u'PLN'))
        self.assertEqual(context['price']['max'],
                         Price(net=5, gross=5*decimal.Decimal('1.9'),
                         currency=u'PLN'))
