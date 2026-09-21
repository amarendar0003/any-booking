"""
Management command: link venue photos already uploaded to media storage.

Photos live at services/<vendor-slug>/<n>.jpg. Each file becomes a
ServiceImage on every Service of the vendor whose slugified name matches
the folder. The first photo (lowest filename) is the primary image.

Usage:
    python manage.py link_venue_photos            # dry run, writes nothing
    python manage.py link_venue_photos --apply    # create ServiceImage rows
"""
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.utils.text import slugify

from services.models import Service, ServiceImage, Vendor

PREFIX = 'services'


class Command(BaseCommand):
    help = 'Create ServiceImage rows for venue photos already in media storage'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true',
                            help='Write rows to the database (default is a dry run)')

    def handle(self, *args, **options):
        apply = options['apply']
        vendors = {slugify(v.name): v for v in Vendor.objects.all()}
        folders, _ = default_storage.listdir(PREFIX)

        created = unmatched = 0
        for folder in sorted(folders):
            vendor = vendors.get(folder)
            if not vendor:
                unmatched += 1
                self.stdout.write(self.style.WARNING(f'{folder}: no vendor with this slug'))
                continue

            _, files = default_storage.listdir(f'{PREFIX}/{folder}')
            photos = sorted(f for f in files if f.lower().endswith(('.jpg', '.jpeg', '.png', '.webp')))
            services = Service.objects.filter(vendor=vendor)
            if not services:
                self.stdout.write(self.style.WARNING(f'{folder}: vendor has no services'))
                continue

            for service in services:
                has_primary = service.images.filter(is_primary=True).exists()
                for order, photo in enumerate(photos):
                    path = f'{PREFIX}/{folder}/{photo}'
                    if service.images.filter(image=path).exists():
                        continue
                    if apply:
                        ServiceImage.objects.create(
                            service=service, image=path, order=order,
                            is_primary=not has_primary and order == 0,
                        )
                    created += 1
            self.stdout.write(f'{folder}: {len(photos)} photos -> {services.count()} service(s)')

        verb = 'created' if apply else 'would create (dry run)'
        self.stdout.write(self.style.SUCCESS(f'{created} ServiceImage rows {verb}, {unmatched} folders unmatched'))
