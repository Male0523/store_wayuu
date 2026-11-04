# Generated for persistent customer carts.
import django.core.validators
import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('store', '0011_userpermissiongrant_delegation'),
    ]

    operations = [
        migrations.CreateModel(
            name='CustomerCartItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantity', models.PositiveIntegerField(validators=[django.core.validators.MinValueValidator(1)], verbose_name='cantidad')),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('customer', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='cart_items', to='store.customer')),
                ('product', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='customer_cart_items', to='store.product')),
            ],
            options={
                'verbose_name': 'producto del carrito',
                'verbose_name_plural': 'productos de los carritos',
                'ordering': ('updated_at',),
            },
        ),
        migrations.AddConstraint(
            model_name='customercartitem',
            constraint=models.UniqueConstraint(fields=('customer', 'product'), name='unique_customer_cart_product'),
        ),
    ]
