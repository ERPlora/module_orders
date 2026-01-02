"""
Initial migration for Orders module.
"""

from django.db import migrations, models
import django.db.models.deletion
import django.core.validators


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='OrdersConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('auto_print_tickets', models.BooleanField(default=True, help_text='Automatically print tickets when order is placed', verbose_name='Auto Print Kitchen Tickets')),
                ('show_prep_time', models.BooleanField(default=True, help_text='Display elapsed preparation time on kitchen display', verbose_name='Show Preparation Time')),
                ('alert_threshold_minutes', models.PositiveIntegerField(default=15, help_text='Time before order is flagged as delayed', verbose_name='Alert Threshold (minutes)')),
                ('use_rounds', models.BooleanField(default=True, help_text='Allow grouping items into rounds (starter, main, dessert)', verbose_name='Use Rounds/Courses')),
                ('auto_fire_on_round', models.BooleanField(default=False, help_text='Automatically send rounds to kitchen when created', verbose_name='Auto Fire Rounds')),
                ('sound_on_new_order', models.BooleanField(default=True, help_text='Play sound when new order arrives', verbose_name='Sound on New Order')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Orders Configuration',
                'verbose_name_plural': 'Orders Configuration',
                'db_table': 'orders_config',
            },
        ),
        migrations.CreateModel(
            name='KitchenStation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=100, unique=True, verbose_name='Name')),
                ('name_es', models.CharField(blank=True, max_length=100, verbose_name='Name (Spanish)')),
                ('description', models.TextField(blank=True, verbose_name='Description')),
                ('color', models.CharField(default='#F97316', max_length=7, verbose_name='Color')),
                ('icon', models.CharField(default='flame-outline', max_length=50, verbose_name='Icon')),
                ('printer_name', models.CharField(blank=True, help_text='System printer name for this station', max_length=100, verbose_name='Printer Name')),
                ('order', models.PositiveIntegerField(default=0, verbose_name='Display Order')),
                ('is_active', models.BooleanField(default=True, verbose_name='Active')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={
                'verbose_name': 'Kitchen Station',
                'verbose_name_plural': 'Kitchen Stations',
                'db_table': 'orders_kitchen_station',
                'ordering': ['order', 'name'],
            },
        ),
        migrations.CreateModel(
            name='Order',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('order_number', models.CharField(max_length=20, unique=True, verbose_name='Order Number')),
                ('table_id', models.PositiveIntegerField(blank=True, help_text='ID of the table from tables module', null=True, verbose_name='Table ID')),
                ('sale_id', models.PositiveIntegerField(blank=True, help_text='ID of the sale from sales module', null=True, verbose_name='Sale ID')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('preparing', 'Preparing'), ('ready', 'Ready'), ('served', 'Served'), ('cancelled', 'Cancelled')], default='pending', max_length=20, verbose_name='Status')),
                ('priority', models.CharField(choices=[('normal', 'Normal'), ('rush', 'Rush'), ('vip', 'VIP')], default='normal', max_length=20, verbose_name='Priority')),
                ('round_number', models.PositiveIntegerField(default=1, help_text='Course number (1=starter, 2=main, etc.)', verbose_name='Round Number')),
                ('created_by', models.CharField(blank=True, help_text='Name of the waiter who placed the order', max_length=100, verbose_name='Created By')),
                ('notes', models.TextField(blank=True, verbose_name='Notes')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('fired_at', models.DateTimeField(blank=True, help_text='When order was sent to kitchen', null=True, verbose_name='Fired At')),
                ('ready_at', models.DateTimeField(blank=True, null=True, verbose_name='Ready At')),
                ('served_at', models.DateTimeField(blank=True, null=True, verbose_name='Served At')),
            ],
            options={
                'verbose_name': 'Order',
                'verbose_name_plural': 'Orders',
                'db_table': 'orders_order',
                'ordering': ['-created_at'],
            },
        ),
        migrations.CreateModel(
            name='OrderItem',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_id', models.PositiveIntegerField(verbose_name='Product ID')),
                ('product_name', models.CharField(max_length=255, verbose_name='Product Name')),
                ('quantity', models.PositiveIntegerField(default=1, validators=[django.core.validators.MinValueValidator(1)], verbose_name='Quantity')),
                ('modifiers', models.TextField(blank=True, help_text="Applied modifiers (e.g., 'No onions, Extra cheese')", verbose_name='Modifiers')),
                ('notes', models.TextField(blank=True, verbose_name='Special Instructions')),
                ('status', models.CharField(choices=[('pending', 'Pending'), ('preparing', 'Preparing'), ('ready', 'Ready'), ('served', 'Served'), ('cancelled', 'Cancelled')], default='pending', max_length=20, verbose_name='Status')),
                ('seat_number', models.PositiveIntegerField(blank=True, null=True, verbose_name='Seat Number')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('started_at', models.DateTimeField(blank=True, null=True, verbose_name='Started At')),
                ('completed_at', models.DateTimeField(blank=True, null=True, verbose_name='Completed At')),
                ('order', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='items', to='orders.order', verbose_name='Order')),
                ('station', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='items', to='orders.kitchenstation', verbose_name='Kitchen Station')),
            ],
            options={
                'verbose_name': 'Order Item',
                'verbose_name_plural': 'Order Items',
                'db_table': 'orders_order_item',
                'ordering': ['order', 'created_at'],
            },
        ),
        migrations.CreateModel(
            name='ProductStation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('product_id', models.PositiveIntegerField(unique=True, verbose_name='Product ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('station', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='products', to='orders.kitchenstation', verbose_name='Kitchen Station')),
            ],
            options={
                'verbose_name': 'Product Station Mapping',
                'verbose_name_plural': 'Product Station Mappings',
                'db_table': 'orders_product_station',
            },
        ),
        migrations.CreateModel(
            name='CategoryStation',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('category_id', models.PositiveIntegerField(unique=True, verbose_name='Category ID')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('station', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='categories', to='orders.kitchenstation', verbose_name='Kitchen Station')),
            ],
            options={
                'verbose_name': 'Category Station Mapping',
                'verbose_name_plural': 'Category Station Mappings',
                'db_table': 'orders_category_station',
            },
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['status'], name='orders_orde_status_4b7a9e_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['table_id'], name='orders_orde_table_i_ccc5a3_idx'),
        ),
        migrations.AddIndex(
            model_name='order',
            index=models.Index(fields=['created_at'], name='orders_orde_created_18f5e3_idx'),
        ),
        migrations.AddIndex(
            model_name='orderitem',
            index=models.Index(fields=['status'], name='orders_orde_status_d2bf2e_idx'),
        ),
        migrations.AddIndex(
            model_name='orderitem',
            index=models.Index(fields=['station', 'status'], name='orders_orde_station_1f3e8a_idx'),
        ),
    ]
