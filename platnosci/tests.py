# -*- encoding: utf-8 -*-

import os
import time
from decimal import Decimal

from django import test
from django.core.urlresolvers import reverse
from django.contrib.auth.models import User

from platnosci.conf import settings
from platnosci.models import PlatnosciPayType
from platnosci.models import PlatnosciOutgoingTransaction
from platnosci.models import PlatnosciIncomingTransaction
from platnosci.tasks import UpdateOutgoingTransactionTask
from platnosci.tasks import UpdateDefinitionsTask
from platnosci.util import calc_outgoing_sig
from platnosci.util import get_server_signature


def create_test_user():
    user = User.objects.create_user('foo', 'bar@baz.pl')
    user.save()
    return user


class FakeHTTPRequest(object):
    META = { 'REMOTE_ADDR' : '192.168.1.1',
             'HTTP_X_FORWARDED_FOR' : '10.0.0.1 10.0.0.2'}
    
    def __init__(self, user):
        self.user = user


def create_test_pot(user, request = None, session_id = '2', order_id = '3', paytype = 'FOO'):
    """Utwórz testowy obiekt PlatnosciOutgoingTransaction 
    dla użytkownika user.
    """
    
    if request is None:
        request = FakeHTTPRequest(user)

    try:
        pt = PlatnosciPayType.objects.get(type = paytype)
    except PlatnosciPayType.DoesNotExist:
        pt = PlatnosciPayType(type = paytype, name = 'Autocereated', enable = True, img = 'img',
                              min = Decimal('0.0'), max = Decimal('100.0'))
        pt.save()
    
    return PlatnosciOutgoingTransaction.run_payment(
        request = request,
        user = user, 
        amount = Decimal('4'),
        paytype = paytype,
        first_name = 'Foo',
        last_name = 'Bar',
        email = 'foo@bar.pl',
        phone = 'banana',
        street = 'street',
        city = 'city',
        post_code = '00-000', 
        
        pos_id = '1',
        session_id = session_id,
        order_id = order_id,
        desc = 'Opis',
        ts = '1')


def create_test_pit(user, status = 99, amount = Decimal(100), session_id = '2', 
                    order_id = '3', request = None, paytype = 'FOO'):
                    
    """Utwórz testowy obiekt PlatnosciIncomingTransaction
    dla użytkownika user"""
    
    pot = create_test_pot(user = user, request = request, paytype = paytype,
                          order_id = order_id, session_id = session_id)['pot']
    pit = PlatnosciIncomingTransaction(
        trans_status = status, added_to_user_account = False,
        outgoing = pot, trans_id = 333, trans_pos_id = 'bar',
        trans_session_id = session_id, trans_order_id = order_id,
        trans_amount = amount, trans_pay_type = 'FOO', 
        trans_pay_gw_name = 'BAR',
        trans_desc = 'xx', trans_desc2 = 'yy', trans_auth_fraud = 'z',
        trans_ts = 'z', trans_sig = 'y', created_from_url = 'none',
        created_from_ip = 'none', last_updated_from_url = 'none',
        last_updated_from_ip = 'none')
    pit.save()
    return pit
    

class TestUtil(test.TestCase):
    def test_calc_outgoing_sig(self):
        dct = {}
        for name in ['pos_id', 'pay_type', 'session_id', 'pos_auth_key',
                     'amount', 'desc', 'desc2', 'trsDesc', 'order_id', 'first_name', 'last_name',
                     'payback_login', 'street', 'street_hn', 'street_an', 'city',
                     'post_code', 'country', 'email', 'phone', 'language', 'client_ip', 'ts']:
            dct[name] = '123'
        calc_outgoing_sig(dct)



class TestPlatnosciOutgoingTransaction(test.TestCase):

    def test_update_failed(self):
        p = PlatnosciOutgoingTransaction()
        p.update_failed('coś poszło nie tak')
        self.assertEquals(p.failed, True)
        self.assertEquals(p.fail_reason, 'coś poszło nie tak')


    def test_update_succeeded(self):
        p = PlatnosciOutgoingTransaction()
        p.update_failed('coś poszło nie tak')
        p.update_succeeded()
        self.assertEquals(p.failed, False)
        self.assertEquals(p.failed_on, None)
        self.assertEquals(p.fail_reason, None)



def test_file_url(fn):
    '''Zwróć URL pliku na dysku, który zawiera testową odpowiedź z serwera'''

    t = os.path.abspath(os.path.join(os.path.dirname(__file__), fn))
    return 'file:///' + t



class TestUpdateDefinitionsTask(test.TestCase):

    def test_update_definitions_task(self):
        old = settings.PLATNOSCI_PAY_TYPES_URL

        print "-" * 78
        print "Teraz bedzie blad w logu - wszystko w porzadku!"
        print "-" * 78

        settings.PLATNOSCI_PAY_TYPES_URL = test_file_url('test-paytypes-bad.xml')
        self.assertEquals(PlatnosciPayType.objects.all().count(), 0)
        result = UpdateDefinitionsTask.delay()
        self.assertEquals(result.get(), False)
        self.assertTrue(result.successful())
        self.assertEquals(PlatnosciPayType.objects.all().count(), 0)

        print "-" * 78
        print "Byl blad w logu - tak ma byc!"
        print "-" * 78

        settings.PLATNOSCI_PAY_TYPES_URL = test_file_url('test-paytypes-good.xml')
        self.assertEquals(PlatnosciPayType.objects.all().count(), 0)
        result = UpdateDefinitionsTask.delay()
        self.assertEquals(result.get(), True)
        self.assertTrue(result.successful())
        self.assertEquals(PlatnosciPayType.objects.all().count(), 2)
        self.assertTrue(PlatnosciPayType.objects.get(type = 'FOO').enable)
        self.assertFalse(PlatnosciPayType.objects.get(type = 'BAR').enable)
        
        settings.PLATNOSCI_PAY_TYPES_URL = old



class TestUpdateOutgoingTransactionTask(test.TestCase):

    def test_update_outgoing_transaction_task(self):

        user = create_test_user()
        request = FakeHTTPRequest(user)

        self.assertEquals(PlatnosciOutgoingTransaction.objects.all().count(), 0)
        self.assertEquals(PlatnosciIncomingTransaction.objects.all().count(), 0)

        create_test_pot(user = user)
        pot = PlatnosciOutgoingTransaction.objects.all()[0]
        pot.needs_update = True
        pot.save()
        
        # Zapisz na później adres URL do pobierania informacji o płatności
        old = (settings.PLATNOSCI_PLATNOSC_GET_URL,
               settings.PLATNOSCI_MD5_KEY2)

        settings.PLATNOSCI_MD5_KEY2 = 'ustaw-mnie'
        
        #
        # Użyj złej informacji - symulowanej odpowiedzi serwera, aby 
        # sprawdzić, czy logowanie błędów i obsługa błędnych odpowiedzi 
        # serwera działa poprawnie:
        #
        settings.PLATNOSCI_PLATNOSC_GET_URL = test_file_url('test-geturl-bad.txt')
        result = UpdateOutgoingTransactionTask.delay(pot.pk)
        self.assertEquals(result.get(), True)
        self.assertTrue(result.successful())
        pot = PlatnosciOutgoingTransaction.objects.all()[0]
        self.assertEquals(pot.needs_update, True)

        #
        # Teraz spróbujmy użyć dobrej odpowiedzi:
        #
        settings.PLATNOSCI_PLATNOSC_GET_URL = test_file_url('test-geturl-good.txt')
        result = UpdateOutgoingTransactionTask.delay(pot.pk)
        self.assertEquals(result.get(), True)
        self.assertTrue(result.successful())

        # ... która to z kolei powinna spowodować, że nasza testowa 
        # transakcja NIE będzie wymagać aktualizacji:
        pot = PlatnosciOutgoingTransaction.objects.all()[0]
        self.assertEquals(pot.needs_update, False)

        # ... oraz spowoduje, że pojawi się informacja o przychodzącej
        # transakcji:
        self.assertEquals(PlatnosciIncomingTransaction.objects.all().count(), 1)
        pit = PlatnosciIncomingTransaction.objects.all()[0]
        self.assertEquals(pit.last_updated_from_ip, '0.0.0.0')
	# socket.gethostbyname(urlparse('file:///...').netloc)

        # Posprzątajmy:
        settings.PLATNOSCI_PLATNOSC_GET_URL = old[0]
        settings.PLATNOSCI_MD5_KEY2 = old[1]




class TestViews(test.TestCase):
    def test_payment_status_view(self):
        """test_payment_status_view
        W tym teście udajemy serwis platnosci.pl aby sprawdzić,
        czy widok, który obsługuje komunikację z platnosci.pl działa
        poprawnie."""
        
        user = create_test_user()
        
        self.assertEquals(PlatnosciOutgoingTransaction.objects.all().count(), 0)
        self.assertEquals(PlatnosciIncomingTransaction.objects.all().count(), 0)

        create_test_pot(user)

        pot = PlatnosciOutgoingTransaction.objects.all()[0]
        pot.needs_update = True
        pot.save()
        
        old = (settings.PLATNOSCI_PLATNOSC_GET_URL,
               settings.PLATNOSCI_MD5_KEY2)

        settings.PLATNOSCI_PLATNOSC_GET_URL = test_file_url('test-geturl-good.txt')
        settings.PLATNOSCI_MD5_KEY2 = 'ustaw-mnie'

        from platnosci.views import payment_status_view

        response = self.client.post(reverse(payment_status_view), 
                                    {'pos_id': pot.pos_id,
                                     'session_id': pot.session_id,
                                     'ts': '1', 'sig': 'bad-sig'})
        self.assertEquals(response.content.startswith('sig != mysig'), True)

        sig = get_server_signature(pot.pos_id, 'no such session', '1')
        response = self.client.post(reverse(payment_status_view), 
                                    {'pos_id': pot.pos_id, 
                                     'session_id': 'no such session',
                                     'ts': '1', 'sig': sig})
        self.assertEquals(response.content.startswith('No such outgoing'), True)

        sig = get_server_signature(pot.pos_id, pot.session_id, '1')
        response = self.client.post(reverse(payment_status_view), 
                                    {'pos_id': pot.pos_id,
                                     'session_id': pot.session_id,
                                     'ts': '1', 'sig': sig, 
                                     'testing-wait-for-result': 1})
        self.assertEquals(response.status_code, 200)
        self.assertEquals(response.content, 'OK')

        self.assertEquals(PlatnosciIncomingTransaction.objects.all().count(), 1)
        pit = PlatnosciIncomingTransaction.objects.all()[0]
        self.assertEquals(pit.last_updated_from_ip, '0.0.0.0') # socket.gethostbyname(urlparse('file:///...').netloc)

        settings.PLATNOSCI_PLATNOSC_GET_URL = old[0]
        settings.PLATNOSCI_MD5_KEY2 = old[1]



class TestTests(test.TestCase):
    """Testuj funkcje pomocnicze z tego modułu
    """

    def test_create_test_pit(self):
        user = create_test_user()
        pit = create_test_pit(user, status = 88)
        self.assert_(pit != None)
        self.assertEquals(pit.trans_status, 88)


    def test_create_test_pot(self):
        user = create_test_user()
        self.assert_(create_test_pot(user) != None)
