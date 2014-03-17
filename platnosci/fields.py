# -*- encoding: utf-8 -*-

from decimal import Decimal

from django.db import models

class MoneyField(models.DecimalField):
    """Pole pieniężne - czyli pole decymalne z dwoma miejscami po
    przecinku, domyślnie 0.0"""
    
    def __init__(self, *args, **kw):

        # south 0.7

        if 'decimal_places' in kw:
            if kw['decimal_places'] != 2:
                raise TypeError, 'To pole nie akceptuje innych wartosci dla decimal_places, niz 2'
            del kw['decimal_places']

        if 'max_digits' in kw:
            if kw['max_digits'] != 10:
                raise TypeError, 'To pole nie akceptuje innych wartosci dla max_digits, niz 10'
            del kw['max_digits']

        # koniec zmian dla south 0.7

        if 'default' not in kw:
            kw['default'] = Decimal("0.00")

        models.DecimalField.__init__(self, decimal_places=2, max_digits=10, *args, **kw)
                                     

try:
    from south.modelsinspector import add_introspection_rules
    using_south = True
except ImportError:
    using_south = False

if using_south:
    add_introspection_rules([], ["^platnosci\.fields\.MoneyField"])

