# -*- encoding: utf-8 -*-

import time
from uuid import uuid4
from datetime import datetime
from decimal import Decimal

from django.db import models
from django.contrib.auth.models import User

from platnosci.fields import MoneyField
from platnosci.util import get_single_client_ip
from platnosci.util import calc_outgoing_sig
from platnosci.util import get_client_ip
from platnosci.conf import settings


class PlatnosciPayType(models.Model):
    '''
    Kanały płatności -- dostajemy je od  platnosci.pl

    Uzupelniane przez platnosci.tasks.UpdateDefinitionsTask na podstawie XML udostepnianego
    w serwisie platnosci.pl . Plik XML z kolei zależy od opcji wybranych w serwisie platnosci.pl
    dla danego POS.
    '''
    type = models.CharField(max_length = 3, unique = True, db_index = True)
    name = models.CharField(max_length = 150)
    enable = models.BooleanField()
    img = models.CharField(max_length = 150)
    min = MoneyField()
    max = MoneyField()

    created_on = models.DateTimeField(auto_now_add = True)
    last_updated_on = models.DateTimeField(auto_now = True, auto_now_add = True)



class PlatnosciOutgoingTransaction(models.Model):
    '''
    Wychodzaca (zlozona) transakcja. Uzytkownik zaznacza, ile chce
    wplacic, transakcja wychodzaca jest tworzona, a nastepnie komunikacje
    przejmuje serwis platnosci.pl
    '''
    user = models.ForeignKey(User)
    pay_type = models.CharField(max_length = 3)
    pos_id = models.CharField(max_length = 100)
    session_id = models.CharField(max_length = 150, unique = True)
    order_id = models.CharField(max_length = 150, unique = True)
    amount = MoneyField()
    desc = models.CharField(max_length = 200)
    desc2 = models.CharField(max_length = 200)

    needs_update = models.BooleanField(db_index = True, default = False)

    created_on = models.DateTimeField(auto_now_add = True)
    created_by_ip = models.CharField(max_length = 250)
    last_modified_on = models.DateTimeField(auto_now_add = True,
        auto_now = True)
    last_modified_by_ip = models.CharField(max_length = 250)

    failed = models.BooleanField(default = False, db_index = True)
    failed_on = models.DateTimeField(null = True, blank = True)
    fail_reason = models.CharField('Błąd konwersji', max_length=51200, blank=True, null=True)


    def __unicode__(self):
        return "Platnosc wychodzaca dla %s - %s - %s PLN" % (self.user.username, self.session_id, str(self.amount).split(".")[0])


    def update_failed(self, traceback):
        self.failed = True
        self.failed_on = datetime.now()
        self.fail_reason = traceback


    def update_succeeded(self):
        self.failed = False
        self.failed_on = None
        self.fail_reason = None

    
    @classmethod
    def run_payment(klass, request, user, amount, paytype, first_name, last_name, email, phone,
                    street, city, post_code, pos_id = None, pos_auth_key = None, session_id = None, 
                    order_id = None, desc = None, desc2 = None, ts = None):

        '''Gdy wiesz już, jaką sumę (amount) chce zapłacić użytkownik (user) za pomocą
        kanału płątności (paytype) -- i masz jego dane teleadresowe, które to już Twoja 
        sprawa, skąd weźmiesz, bo Django nijak tego nie standaryzuje -- wywołaj tą funkcję. 

        Skorzysta ona ze skonfigurowanych w settings wartości dla PLATNOSCI_POS_ID i innych,
        nada niepowtarzalne numery sesji i zamówienia, pobierze IP klienta... 

        Do tego, funkcja ta zwróci Ci słownik wartości, którymi to powinieneś posłużyć się przy 
        wysyłaniu zapytania POST do serwisu platnosci.pl (czyli: musisz zaprezentować użytkownikowi
        formularz z tymi wartościami, użytkownik zatwierdza formularz i jest przenoszony do serwisu
        transakcyjnego)...

        Przypominamy, że autorzy tego modułu nie biorą odpowiedzialności za jego działanie.
        '''

        # pay_type musi istniec
        paytype_show = PlatnosciPayType.objects.get(type = paytype)

        # user musi być
        assert(user)

        # amount musi być typu Decimal
        assert(type(amount) == Decimal)

        # amount musi mieć nie więcej, niż 2 miejsca po przecinku
        tmp = str(amount).split('.')
        if len(tmp)>1:
            assert(len(tmp[1]) <= 2)

        # w przypadku nie podania wybranych wartości, ustaw im domyślne informacje
        if pos_id is None:
            pos_id = str(settings.PLATNOSCI_POS_ID)
        
        if pos_auth_key is None:
            pos_auth_key = str(settings.PLATNOSCI_POS_AUTH_KEY)

        if desc is None:
            desc = u'doładowanie konta'
        
        if desc2 is None:
            desc2 = u'dla użytkownika %s' % user.username

        if session_id is None:
            session_id = str(uuid4())
        
        if order_id is None:
            order_id = str(uuid4())

        if ts is None:
            ts = str(int(time.time()))

        client_ip = get_single_client_ip(request)

        amount = str(amount * Decimal('100.0')).split(".")[0]
        amount_show = amount

        form_data = dict(pay_type = paytype, paytype_show = paytype_show,
                         first_name = first_name, last_name = last_name,
                         email = email, phone = phone, street = street, 
                         city = city, post_code = post_code, pos_id = pos_id,
                         pos_auth_key = pos_auth_key, desc = desc, desc2 = desc2, 
                         session_id = session_id, order_id = order_id, client_ip = client_ip,
                         ts = ts, amount = amount, amount_show = amount_show)

        form_data['sig'] = calc_outgoing_sig(form_data)
        
        full_client_ip = get_client_ip(request)

        pot = klass(user = user,
                    pay_type = paytype, 
                    pos_id = form_data['pos_id'],
                    session_id = form_data['session_id'], 
                    order_id = form_data['order_id'],
                    amount = form_data['amount'], 
                    desc = form_data['desc'], 
                    desc2 = form_data['desc2'],
                    created_by_ip = full_client_ip, 
                    last_modified_by_ip = full_client_ip, 
                    needs_update = False)

        pot.save()

        form_data['pot'] = pot

        return form_data
        



class PlatnosciIncomingTransaction(models.Model):
    '''
    Platnosc przychodzaca -- te rekordy tworzone sa przez tasks.UpdateOutgoingTransactionTask
    na podstawie informacji uzyskanych z serwisu platnosci.pl
    '''
    outgoing = models.ForeignKey(PlatnosciOutgoingTransaction)

    trans_id = models.IntegerField()
    trans_pos_id = models.CharField(max_length = 200)
    trans_session_id = models.CharField(max_length = 200)
    trans_order_id = models.CharField(max_length = 200)
    trans_amount = MoneyField()
    trans_status = models.IntegerField()
    trans_pay_type = models.CharField(max_length = 3)
    trans_pay_gw_name = models.CharField(max_length = 200)
    trans_desc = models.CharField(max_length = 200)
    trans_desc2 = models.CharField(max_length = 200)
    trans_create = models.DateTimeField(null = True)
    trans_init = models.DateTimeField(null = True)
    trans_sent = models.DateTimeField(null = True)
    trans_recv = models.DateTimeField(null = True)
    trans_cancel = models.DateTimeField(null = True)
    trans_auth_fraud = models.CharField(max_length = 200)
    trans_ts = models.CharField(max_length = 200)
    trans_sig = models.CharField(max_length = 200)

    created_from_url = models.CharField(max_length = 200)
    created_from_ip = models.CharField(max_length = 200)

    last_updated_from_url = models.CharField(max_length = 200)
    last_updated_from_ip = models.CharField(max_length = 200)

    created_on = models.DateTimeField(auto_now_add = True)
    last_updated_on = models.DateTimeField(auto_now = True, auto_now_add = True)

    added_to_user_account = models.BooleanField(default = False, db_index = True)
    added_to_user_account_on = models.DateTimeField(null = True, blank = True)
