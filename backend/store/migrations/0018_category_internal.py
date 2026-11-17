from django.db import migrations, models


def mark_generated_design_category_internal(apps, schema_editor):
    Category = apps.get_model('store', 'Category')
    Category.objects.filter(name='Diseños personalizados').update(is_internal=True)


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0017_customerfavorite'),
    ]

    operations = [
        migrations.AddField(
            model_name='category',
            name='is_internal',
            field=models.BooleanField(default=False, help_text='Las categorías internas organizan datos técnicos y no aparecen en el catálogo comercial.', verbose_name='categoría interna'),
        ),
        migrations.RunPython(mark_generated_design_category_internal, migrations.RunPython.noop),
    ]
