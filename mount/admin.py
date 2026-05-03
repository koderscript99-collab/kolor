from django.contrib import admin

# Register your models here.
from .models import DataPurchase, Transaction,Account,Detail


admin.site.register(DataPurchase)
admin.site.register(Account)
admin.site.register(Transaction)
admin.site.register(Detail)
