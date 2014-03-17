from django.conf.urls.defaults import *

# URL http://moj.django.site/platnosci/status/ przekaz do platnosci.pl jako URL informujacy
# o zmianie statusu platnosci.

# Pozostale dwa URLe ('ok' i 'error') -- Twoja aplikacja, obsluguj
# je wedle Twojego uznania, pamietaj o zdefiniowanych wartosciach komunikatow 
# w platnosci.util.PLATNOSCI_STATUSY

urlpatterns = patterns('',
    (r'^platnosci/', include('platnosci.urls')),
)
