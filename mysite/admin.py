from django.contrib import admin
from .models import Book, User, Rating

admin.site.register(Book)
admin.site.register(Rating)
