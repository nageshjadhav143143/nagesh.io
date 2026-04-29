from django.contrib import admin
from .models import Category, MenuItem, Order, OrderItem, Table, ContactMessage

admin.site.register(Category)
admin.site.register(MenuItem)
admin.site.register(Order)
admin.site.register(OrderItem)
admin.site.register(Table)
admin.site.register(ContactMessage)
