import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.test import Client
from services.models import Category

n = Category.objects.count()
r = Client().get('/')
html = r.content.decode()
print('HTTP', r.status_code)
print('categories in DB:', n)
print('tiles rendered:', html.count('class="cat-tile"'))
print('clone tiles rendered:', html.count('data-clone="true"'))
print('arrows rendered:', html.count('cat-arrow cat-arrow-left'))
print('static-guard present in JS:', 'origItems.length <= 3' in html)
