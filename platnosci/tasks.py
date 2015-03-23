# -*- encoding: utf-8 -*-

import time
from decimal import Decimal
from datetime import timedelta
from xml.dom import minidom
import hashlib
import socket
import urlparse
import os
import sys
import traceback
from urllib import urlencode
import urllib2

from django.db import transaction
from django.core.cache import cache

from celery.task import PeriodicTask, Task
from celery.task.http import URL

from platnosci.conf import settings
from platnosci.util import calc_incoming_sig
from platnosci.models import PlatnosciPayType, PlatnosciOutgoingTransaction, PlatnosciIncomingTransaction


class UpdateDefinitionsTask(PeriodicTask):
    '''Sciagnij definicje platnosci z serwera platnosci.pl w XML, następnie
    dodaj do bazy danych. Wykonaj to zadanie domyślnie co 2 dni. W przypadku, gdybyś
    ręcznie zmienił dostępne kanały płatności w serwisie platnosci.pl dla tego punktu sprzedaży,
    musisz ręcznie wyczyścić bazę danych z obiektów platnosci.models.PlatnosciPayType i ponownie
    uruchomić to zadanie.'''

    run_every = timedelta(days = 2)

    @transaction.atomic
    def run(self, **kwargs):

        logger = self.get_logger(**kwargs)

        try:
            response = urllib2.urlopen(settings.PLATNOSCI_PAY_TYPES_URL)
            xmlString = response.read()
            xml = minidom.parseString(xmlString)
        except Exception:
            logger.error(traceback.format_exc(51200))
            logger.error('Nie mozna uzyskac listy platnosci od platnosci.pl!')
            logger.error('Adres URL: %r' % settings.PLATNOSCI_PAY_TYPES_URL)
            return False

        cnt = 0

        for paytype in xml.getElementsByTagName('paytype'):
            cnt += 1
            def _get(n):
                return paytype.getElementsByTagName(n)[0].firstChild.data

            type = _get('type')
            name = _get('name')
            enable = _get('enable') == 'true'
            img = _get('img')
            min = Decimal(_get('min'))
            max = Decimal(_get('max'))

            try:
                p = PlatnosciPayType.objects.get(type = type)
            except PlatnosciPayType.DoesNotExist:
                p = PlatnosciPayType(type = type)
            p.name = name
            p.enable = enable
            p.img = img
            p.min = min
            p.max = max
            p.save()

        return True


LOCK_EXPIRE = 60 * 5

class FakeLogger:
    def error(self, msg):
        print msg
    def debug(self, msg):
        print msg


class UpdateOutgoingTransactionTask(Task):


    @transaction.atomic
    def run(self, pot_id, **kwargs):

        # logger = self.get_logger(**kwargs)
        logger = FakeLogger()

        # upewnij się, że jednoczasowo przetwarzamy tylko i wyłącznie jedną płatność o takim ID:
        pot_id_hexdigest = hashlib.md5(str(pot_id)).hexdigest()
        lock_id = "%s-lock-%s" % (self.name, pot_id_hexdigest)

        is_locked = lambda: str(cache.get(lock_id)) == "true"
        acquire_lock = lambda: cache.set(lock_id, "true", LOCK_EXPIRE)
        release_lock = lambda: cache.set(lock_id, "nil", 1)

        logger.debug("Przetwarzam platnosc: %s" % pot_id)
        if is_locked():
            logger.debug(
                "Platnosci %s jest juz przetwarzana przez inny proces" % pot_id)
            return

        acquire_lock()

        try:
            pot = PlatnosciOutgoingTransaction.objects.get(id = pot_id)

            ts = str(int(time.time()))
            data = dict(pos_id = settings.PLATNOSCI_POS_ID,
                session_id = pot.session_id, ts = ts)

            data['sig'] = calc_incoming_sig(data)

            body = urlencode(data)

            url = settings.PLATNOSCI_PLATNOSC_GET_URL
            url_resolved = socket.gethostbyname(urlparse.urlparse(url).netloc)

            logger.debug('URL platnosci %s resolwuje sie do %s' % (url, url_resolved))

            response = urllib2.urlopen(url, body)

            dct = {}
            for line in response.readlines():
                line = line.strip()
                if not line: continue
                try:
                    name, value = line.split(": ", 1)
                except ValueError:
                    name = line.split(": ", 1)[0]
                    value = None
                dct[name] = value

            if dct['status'] != 'OK':
                logger.error('Status zwrocony z platnosci.pl dla POT.pk=%r to %s' % (pot.pk, dct['status']))

            else:
                del dct['status']

                assert(dct['trans_pos_id'] == pot.pos_id), "pos_id differs (%s!=%s)" % (dct['trans_pos_id'], pot.pos_id)
                assert(dct['trans_session_id'] == pot.session_id), "session_id differs"
                assert(dct['trans_order_id'] == pot.order_id), "order_id differs"
                assert(Decimal(dct['trans_amount']) == Decimal(pot.amount)), "amount differs" # 4400 != 4400.00

                mysig = hashlib.md5(dct['trans_pos_id'] + dct['trans_session_id'] +
                    dct['trans_order_id'] + dct['trans_status'] + dct['trans_amount'] +
                    dct['trans_desc'] + dct['trans_ts'] + settings.PLATNOSCI_MD5_KEY2).hexdigest()

                if mysig != dct['trans_sig']:
                    logger.error('Sygnatura z platnosci.pl nie odpowiada obliczonej lokalnie dla POT.pk=%r -- mysig != sig, %s != %s' % (pot.pk, mysig, dct['trans_sig']))
                else:

                    try:
                        pit = PlatnosciIncomingTransaction.objects.get(trans_pos_id = dct['trans_pos_id'],
                            trans_session_id = dct['trans_session_id'], outgoing = pot)
                    except PlatnosciIncomingTransaction.DoesNotExist:
                        pit = PlatnosciIncomingTransaction(trans_pos_id = dct['trans_pos_id'],
                            trans_session_id = dct['trans_session_id'], outgoing = pot,
                            created_from_url = url, created_from_ip = url_resolved,
                            last_updated_from_url = url, last_updated_from_ip = url_resolved)
                        logger.debug("Created new incoming transaction, status: %s" % dct['trans_status'])

                    dct['trans_amount'] = Decimal(dct['trans_amount']) / Decimal('100.0')

                    for varname in ['trans_id', 'trans_order_id', 'trans_amount', 'trans_status',
                        'trans_pay_type', 'trans_pay_gw', 'trans_pay_gw_name', 'trans_desc',
                        'trans_desc2', 'trans_create', 'trans_init', 'trans_sent', 'trans_recv',
                        'trans_cancel','trans_auth_fraud', 'trans_ts', 'trans_sig']:
                        setattr(pit, varname, dct.get(varname))

                    pit.save()

                    if pit.trans_status == '99' and not pit.added_to_user_account and settings.PLATNOSCI_SUCCESS_URL is not None:

                        # Teraz czas na Twoja aplikacje - poszukaj wszystkich PlatnosciIncomingTransaction
                        # ktore maja status = 99 oraz added_to_user_account = False i dodaj je do kont swoich
                        # uzytkownikow w taki sposob, jaki odpowiada Ci najbardziej. Proponujemy oczywiscie
                        # zrobic to przez Celery - PeriodicTask powinien sobie z tym poradzic, chociaż z drugiej
                        # strony nie jest to najlepsze rozwiązanie (polling bazy danych), wiec mozemy poinformowac Twoja aplikacje
                        # za pomoca URL:

                        url = settings.PLATNOSCI_SUCCESS_URL + "?pit_id=%i" % pit.pk
                        res = URL(url).get_async()

                    pot.update_succeeded()
                    pot.needs_update = False
                    pot.save()
        finally:
            release_lock()

        return True
