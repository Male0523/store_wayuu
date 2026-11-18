from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [('store', '0020_explicit_specialized_role_grants')]

    operations = [
        migrations.AddField(
            model_name='product',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='products/', verbose_name='imagen cargada'),
        ),
    ]
