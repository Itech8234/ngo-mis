# Django admin registration (customized).
from django.contrib import admin

from .models import CarouselSlide


@admin.register(CarouselSlide)
class CarouselSlideAdmin(admin.ModelAdmin):
    list_display = ("title", "order", "is_active")
    list_editable = ("order", "is_active")
    search_fields = ("title", "eyebrow")
