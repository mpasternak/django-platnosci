# -*- encoding: utf-8 -*-

import hashlib

from platnosci.conf import settings

# Numery i nazwy komunikatów pozyskane zostały z dokumentacji platnosci.pl

PLATNOSCI_STATUSY = {
    '100' : 'brak lub błedna wartosc parametru pos id',
    '101' : 'brak parametru session id',
    '102' : 'brak parametru ts',
    '103' : 'brak lub błedna wartosc parametru sig',
    '104' : 'brak parametru desc',
    '105' : 'brak parametru client ip',
    '106' : 'brak parametru first name',
    '107' : 'brak parametru last name',
    '108' : 'brak parametru street',
    '109' : 'brak parametru city',
    '110' : 'brak parametru post code',
    '111' : 'brak parametru amount',
    '112' : 'błedny numer konta bankowego',
    '113' : 'brak parametru email',
    '114' : 'brak numeru telefonu',
    '200' : 'inny chwilowy bład',
    '201' : 'inny chwilowy bład bazy danych',
    '202' : 'Pos o podanym identyfikatorze jest zablokowany',
    '203' : 'niedozwolona wartosc pay type dla danego pos id',
    '204' : 'podana metoda płatnosci (wartosc pay type) jest chwilowo zablokowana dla danego pos id, np. przerwa konserwacyjna bramki płatniczej',
    '205' : 'kwota transakcji mniejsza od wartosci minimalnej',
    '206' : 'kwota transakcji wieksza od wartosci maksymalnej',
    '207' : 'przekroczona wartosc wszystkich transakcji dla jednego klienta w ostatnim przedziale czasowym',
    '208' : 'Pos działa w wariancie ExpressPayment lecz nie nastapiła aktywacja tego wariantu współpracy (czekamy na zgode działu obsługi klienta)',
    '209' : 'błedny numer pos id lub pos auth key',
    '500' : 'transakcja nie istnieje',
    '501' : 'brak autoryzacji dla danej transakcji',
    '502' : 'transakcja rozpoczeta wczesniej',
    '503' : 'autoryzacja do transakcji była juz przeprowadzana',
    '504' : 'transakcja anulowana wczesniej',
    '505' : 'transakcja przekazana do odbioru wczesniej',
    '506' : 'transakcja juz odebrana',
    '507' : 'bład podczas zwrotu srodków do klienta',
    '599' : 'błedny stan transakcji, np. nie mozna uznac transakcji kilka razy lub inny, prosimy o kontakt',
    '999' : 'inny bład krytyczny - prosimy o kontakt'
    }


def get_single_client_ip(request):
    '''Ustal IP klienta, bazując na HttpRequest.
    Skorzystaj z tej funkcji, gdy potrzebujesz jednego (i tylko jednego)
    adresu IP klienta (np. dla systemu platnosci.pl)
    
    Jeżeli jest nagłówek X-Forwarded-For, to użyj tego IP.

    Jeżeli nie ma tego nagłówka, użyj REMOTE_ADDR.

    Jeżeli nic nie ma, użyj 255.255.255.255
    '''

    client_ip = request.META.get('HTTP_X_FORWARDED_FOR')

    if not client_ip:
        client_ip = request.META.get('REMOTE_ADDR')

    if not client_ip:
        client_ip = '255.255.255.255'

    return client_ip


def get_client_ip(request):
    '''Zwroc string z adresem (adresami) IP klienta w postaci:

        "remote_addr=255.255.255.255 forwarded_for=10.0.0.0 42.0.32.12 ..."
        
    Maksymalnie ten ciag znakow ma mieć 250 znaków. 
    '''

    xff = request.META.get('HTTP_X_FORWARDED_FOR')
    ra = request.META.get('REMOTE_ADDR')

    if xff and ra:
        ret = "remote_addr=%s forwarded_for=%s" % (ra, xff)

    elif xff:
        ret = "forwarded_for=%s" % xff

    elif ra:
        ret = "remote_addr=%s" % ra

    else:
        ret = "unknown"

    return ret[:250]


def get_server_signature(pos_id, session_id, ts):
    return hashlib.md5(pos_id + session_id + ts + settings.PLATNOSCI_MD5_KEY2).hexdigest()


def calc_incoming_sig(dct, key1 = None):
    if key1 is None:
        key1 = settings.PLATNOSCI_MD5_KEY1

    return hashlib.md5(dct['pos_id'] + dct['session_id'] + dct['ts'] + key1).hexdigest()


def calc_outgoing_sig(dct, key1 = None):
    '''Liczy sumę kontrolną dla płatności wychodzącej'''

    if key1 is None:
        key1 = settings.PLATNOSCI_MD5_KEY1

    element_names = ['pos_id', 'pay_type', 'session_id', 'pos_auth_key',
        'amount', 'desc', 'desc2', 'trsDesc', 'order_id', 'first_name', 'last_name',
        'payback_login', 'street', 'street_hn', 'street_an', 'city',
        'post_code', 'country', 'email', 'phone', 'language', 'client_ip', 'ts' ]

    s = u''
    for element_name in element_names:
        try:
            s += dct[element_name]
        except (TypeError, UnicodeDecodeError), e:
            raise Exception, 'cannot add %s (%r) because of %r' % (element_name, dct[element_name], e)
        except KeyError:
            pass
        
    s += unicode(key1)

    s = s.encode('utf8')

    return hashlib.md5(s).hexdigest()
