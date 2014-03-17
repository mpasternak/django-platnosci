# -*- encoding: utf-8 -*-

import sys
from django.http import HttpResponse
from django.http import HttpResponseBadRequest

from platnosci.models import PlatnosciOutgoingTransaction
from platnosci.util import get_server_signature, get_client_ip
from platnosci.tasks import UpdateOutgoingTransactionTask


def payment_status_view(request):
    '''Ten widok musisz wyeksponowac w taki sposob, 
    aby serwis platnosci.pl mogl go wywołać.

    Innymi słowy, adres URL do tego widoku podajesz bezpośrednio
    w ustawieniach konfiguracyjnych platnosci.pl
    '''

    if request.method == 'POST':
        pos_id = request.POST.get('pos_id')
        session_id = request.POST.get('session_id')
        ts = request.POST.get('ts')
        sig = request.POST.get('sig')
        
        # Sprawdź, czy suma kontrolna przekazana przez serwis platnosci.pl jest prawidłowa:
        mysig = get_server_signature(pos_id, session_id, ts)
        if sig != mysig:
            return HttpResponse("sig != mysig, %s != %s" % (sig, mysig))

        # Sprawdź, czy wychodząca transakcja o takiem pos_id oraz session_id istnieje:
        try:
            pot = PlatnosciOutgoingTransaction.objects.get(pos_id = pos_id, session_id = session_id)
        except PlatnosciOutgoingTransaction.DoesNotExist:
            return HttpResponse("No such outgoing transaction: (pos_id = %s, session_id = %s)" % (pos_id, session_id))

        # Suma się zgadza, transakcja istnieje -- wymaga zatem aktualizacji:
        pot.needs_update = True
        pot.last_modified_by_ip = get_client_ip(request)
        pot.save()
        
        # Wywołaj zadanie które skontaktuje się z serwisem 
        # platnosci.pl, a następnie pobierze informacje na temat 
        # zmienionej płatności. 
        UpdateOutgoingTransactionTask.delay(pot.pk)
        return HttpResponse("OK")

    return HttpResponseBadRequest()
