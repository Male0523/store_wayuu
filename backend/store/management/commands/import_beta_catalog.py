import re
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from store.models import Category, Product


class Command(BaseCommand):
    help = 'Importa el catálogo de mantas desde mantas_wayuu_beta_6.0.html.'

    item_pattern = re.compile(
        r'\{\s*id:\s*(?P<id>\d+),\s*'
        r'talla:\s*"(?P<size>[^"]+)",\s*'
        r'name:\s*"(?P<name>[^"]+)",\s*'
        r'region:\s*"(?P<region>[^"]+)",\s*'
        r'colorTag:\s*"(?P<color_tag>[^"]+)",\s*'
        r'colorName:\s*"(?P<color>[^"]+)",\s*'
        r'desc:\s*"(?P<description>[^"]+)",\s*'
        r'img:\s*"(?P<image>data:image/[^"]+)"\s*\}',
        re.DOTALL,
    )

    prices = {'S': 50000, 'M': 120000, 'L': 180000, 'XL': 250000}
    times = {'S': '12-15 días', 'M': '18-22 días', 'L': '22-28 días', 'XL': '25-30 días'}

    names = {
        1: 'Manta Marfil Dorada',
        2: 'Manta Terracota de Uribia',
        3: 'Manta Salinas Azul',
        4: 'Manta Oliva de Riohacha',
        5: 'Manta Tricolor Wayuu',
        6: 'Manta Flores de La Guajira',
        7: 'Manta Sol de Manaure',
        8: 'Manta Noche Floral',
    }

    def handle(self, *args, **options):
        source = Path(settings.BASE_DIR).parent / 'mantas_wayuu_beta_6.0.html'
        if not source.exists():
            raise CommandError(f'No se encontró el archivo beta: {source}')

        source_text = source.read_text(encoding='utf-8')
        items_block = re.search(r'const ITEMS\s*=\s*\[(.*?)\];\s*\n\s*const customProducts', source_text, re.DOTALL)
        if not items_block:
            raise CommandError('No se encontró el catálogo ITEMS dentro del archivo beta.')
        items = list(self.item_pattern.finditer(items_block.group(1)))
        if not items:
            raise CommandError('No se pudieron leer productos del catálogo beta.')

        category, _ = Category.objects.get_or_create(
            name='Catálogo Wayuu',
            defaults={'description': 'Mantas importadas desde el catálogo inicial.', 'active': True},
        )
        imported = 0
        for match in items:
            item = match.groupdict()
            size = item['size']
            Product.objects.update_or_create(
                sku=f"BETA-{int(item['id']):03d}",
                defaults={
                    'name': self.names.get(int(item['id']), item['name']),
                    'category': category,
                    'description': item['description'],
                    'region': item['region'],
                    'color': item['color'],
                    'size': size,
                    'production_time': self.times.get(size, '18-22 días'),
                    'price': self.prices.get(size, 120000),
                    'stock': 10,
                    'image_url': item['image'],
                    'made_to_order': True,
                    'active': True,
                },
            )
            imported += 1
        self.stdout.write(self.style.SUCCESS(f'{imported} productos del catálogo beta fueron importados o actualizados.'))
