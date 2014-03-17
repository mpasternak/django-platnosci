# -*- encoding: utf-8 -*-

django-platnosci - obsługa serwisu platnosci.pl dla django, korzysta z celery

(C) 2009, 2010, 2011 FHU Kagami, http://fhu-kagami.pl/

Ten moduł rozpowszechniany jest na licencji MIT. ŻADNEJ GWARANCJI POPRAWNEGO DZIAŁANIA. AUTORZY
NIE ZALECAJĄ KORZYSTANIA Z TEGO MODUŁU DO AUTORYZACJI PRAWDZIWYCH TRANSAKCJI -- KORZYSTAJ JEDYNIE
Z TESTOWYCH.

Jak to działa?

    1) korzystamy z Django, Celery oraz serwisu platnosci.pl. Zapoznaj się z dokumentacją tychże.
       Skontaktuj się z platnosci.pl i skorzystaj z podanych przez nich danych aby ustawić odpowiednio
       zmienne konfiguracyjne settings.PLATNOSCI_POS_ID, PLATNOSCI_MD5_KEY1, PLATNOSCI_MD5_KEY2,
       PLATNOSCI_POS_AUTH_KEY. Tyle konfiguracji. Zobacz platnosci.conf.settings, aby sprawdzić, 
       z jakich adresów URL będziemy korzystali.

    2) utwórz obiekt PlatnosciOutgoingTransaction -- wartosci kluczowe to pay_type, pos_id, session_id,
       order_id; sumę pieniędzy przekazuje wartość amount.

    3) zaprezentuj użytkownikowi formularz POST do serwera platnosci.pl który będzie zawierał
       powżysze wartości oraz inne, wymagane przez platnosci.pl

    3.5) kroki w punktach 2 i 3 ułatwia funkcja PlatnosciOutgoingTransaction.run_payment - przeczytaj
	 jej docstrings, podaj jej wymagane parametry (parametry nie-wymagane zostaną ustawione
	 automatycznie). Funkcja zwróci słownik, który to słownik wystarczy wyświetlić użytkownikowi
         w ukrytych polach formularzu z metodą POST, kierującego do PLATNOSCI_NEW_PAYMENT_URL. 

    4) gdy użytkownik zaakceptuje ten formularz i dokona platnosci - dalsza jej autoryzacja dzieje się
       już po stronie platnosci.pl. Serwer platnosci.pl kontaktuje się z naszym serwerem. 
       To dzieje się już bez ingerencji użytkownika i może trwać nawet dniami (w przypadku przekazu 
       pieniężnego, przykładowo).

    5) musisz udostępnić serwerowi platnosci.pl widok platnosci.views.payment_status_view tak, aby
       mógł on aktualizować informacje o zmienionych płatnościach; w przypadku, gdy platnosci.pl
       wywoła nasz serwis i zmieni istniejącą płatność PaymentsOutgoingTransaction, django przesyła
       informację o nowym zadaniu dla Celery -- w takiej sytuacji będzie musiało być uruchomione
       zadanie platnosci.task.update_outgoing_transaction(PlatnosciOutgoingTransaction.pk).

    6) musisz uruchomić daemona celery wraz z obsługą zadań periodycznych aby pobierać definicje
       płatności z serwera platnosci.pl (platnosci.task.UpdateDefinitionsTask) oraz aby móc
       aktualizować na-żądanie (patrz punkt 4) zmienione transakcje
       (platnosci.task.UpdateOutgoingTransactionTask). Domyślnie, definicje platnosci pobierane 
       są co 2 dni. W przypadku, gdybyś je zmienił, musisz ręcznie wyczyścić bazę danych z obiektów
       PlatnosciPayType i ponownie uruchomić proces pobierania definicji platnosci.

    7) co zrobić po aktualizacji transakcji? (vide komentarz na końcu procedury
       platnosci.task.update_outgoing_transaction) -- to już należy do Ciebie, ten moduł nie
       implementuje żadnej funkcjonalności związanej z obsługą i zapisywaniem płatności docelowo
       dla konta użytkownika, ponieważ autorom wydaje się, że jest to bardzo specyficzne zadanie
       -- czego nie stworzymy w tej kwestii, na pewno nie będziemy w stanie wszystkim dogodzić...
