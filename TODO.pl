# -*- encoding: utf-8 -*-

* PlatnosciOutgoingTransaction.amount powinno byc na dobra sprawe typu tekstowego -- decimal z 2ma miejscami po przecinku nie ma tam wiekszego sensu, bo te 2 miejsca po przecinku po przemnozeniu tego amount przez 100 zgodnie z wymaganiami platnosci.pl i tak zawsze beda zawierac '00'

* upewnij sie, ze testujesz daty w dobrych formatach - plik test-geturl-good.txt

* po autoryzacji platnosci, gdy nalezy ją dodać do konta użytkownika, serwis powinien wywołać
  jakieś celery-task np. przez URL, zwrotnie do głównego serwisu django... (vide komentarz
  w platnosci.tasks.UpdateOutgoingTransactionTask)

* dla wybranych kanałów płatności platnosci.pl wysyłają wybrane dane dodatkowe; być może warto byłoby
  te dane zachowywać w bazie...
