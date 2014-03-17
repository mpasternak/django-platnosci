from setuptools import setup, find_packages
    
setup(
    name = 'django-platnosci',
    version = '0.8',
    author = 'FHU Kagami',
    author_email = 'info@fhu-kagami.pl',
    url = 'http://fhu-kagami.pl/',
    packages = find_packages(),
    package_data = {
        'platnosci': [
            'test-paytypes-good.xml', 
            'test-paytypes-bad.xml', 
            'test-geturl-good.txt', 
            'test-geturl-bad.txt']},
    zip_safe = False,
    install_requires = ['django', 'celery'],
    license = 'MIT')
