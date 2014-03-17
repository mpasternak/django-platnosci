# -*- encoding: utf-8 -*-

# Skonfiguruj moduł platnosci -- te dane otrzymasz od serwisu platnosci.pl

PLATNOSCI_POS_ID = 'Moj punkt sprzedazy'
PLATNOSCI_MD5_KEY1 = 'Klucz MD5'
PLATNOSCI_MD5_KEY2 = 'ustaw-mnie' # testy zależą od tego ustawienia (checksuma w test-geturl-good.txt)
PLATNOSCI_POS_AUTH_KEY = 'Klucz autoryzacji POS'

# Dodaj platnosci i celery do INSTALLED_APPS

INSTALLED_APPS = (
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.sites',

    'platnosci',
    'celery'
)

# Skonfiguruj celery wedle uznania:

CELERY_BACKEND = 'database'
CELERY_ALWAYS_EAGER = True



# 
# Pozostałe ustawienia Django -- typowe
#

DATABASE_ENGINE = 'sqlite3'

DEBUG = True

SECRET_KEY = ')px&o!z0u4eg$c%+-0)a_c+7z@)o4h0wc47myemde^cawb5+-d'

ROOT_URLCONF = 'demo.urls'
