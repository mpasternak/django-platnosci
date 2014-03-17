# -*- encoding: utf-8 -*-

from django.conf import settings

#
# Poniższe ustawienia musisz pozyskać z serwisu platnosci.pl
#

PLATNOSCI_POS_ID = getattr(settings, 'PLATNOSCI_POS_ID', 'ustaw-mnie')
PLATNOSCI_MD5_KEY1 = getattr(settings, 'PLATNOSCI_MD5_KEY1', 'ustaw-mnie')
PLATNOSCI_MD5_KEY2 = getattr(settings, 'PLATNOSCI_MD5_KEY2', 'ustaw-mnie')
PLATNOSCI_POS_AUTH_KEY = getattr(settings, 'PLATNOSCI_POS_AUTH_KEY', 'ustaw-mnie')



#
# Adres URL dla celów powiadamiania Twojego serwisu WWW o zatwierdzonych
# (zapłaconych) płatnościach. Będzie wywoływany za każdym razem, gdy 
# jakaś płatność uzyska status zatwierdzonej (zapłaconej). Domyślna
# wartosć (None) powoduje pominięcie operacji notyfikacji. 
#

PLATNOSCI_SUCCESS_URL = getattr(settings, 'PLATNOSCI_SUCCESS_URL', None)



#
# Standardowe adresy URL do komunikacji z serwisem platnosci.pl
# Normalnie nie ma potrzeby ich zmieniania.
#

PLATNOSCI_NEW_PAYMENT_URL = getattr(settings, "PLATNOSCI_NEW_PAYMENT_URL", 
    "https://www.platnosci.pl/paygw/UTF/NewPayment")

PLATNOSCI_PAY_TYPES_URL = getattr(settings, "PLATNOSCI_PAY_TYPES_URL", 
    "https://www.platnosci.pl/paygw/UTF/xml/%s/%s/paytype.xml" % (PLATNOSCI_POS_ID, PLATNOSCI_MD5_KEY1[:2]))

PLATNOSCI_PLATNOSC_GET_URL = getattr(settings, "PLATNOSCI_PLATNOSC_GET_URL",
    "https://www.platnosci.pl/paygw/UTF/Payment/get/txt")

