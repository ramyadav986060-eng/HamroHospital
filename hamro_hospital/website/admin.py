from django.contrib import admin
from website.models import (
    HospitalService, Testimonial, GalleryImage, DiseaseInfo, ContactMessage,
    MedicalService, Announcement, HomeNotification,
)


@admin.register(HospitalService)
class HospitalServiceAdmin(admin.ModelAdmin):
    list_display = ('service_code', 'name', 'department', 'price', 'is_active')
    list_filter = ('is_active', 'department')
    search_fields = ('service_code', 'name')


@admin.register(Testimonial)
class TestimonialAdmin(admin.ModelAdmin):
    list_display = ('patient_name', 'rating', 'is_published', 'created_at')
    list_filter = ('is_published', 'rating')
    search_fields = ('patient_name', 'message')


@admin.register(GalleryImage)
class GalleryImageAdmin(admin.ModelAdmin):
    list_display = ('title', 'display_order', 'is_published', 'created_at')
    list_filter = ('is_published',)
    ordering = ('display_order',)


@admin.register(DiseaseInfo)
class DiseaseInfoAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'is_published', 'created_at')
    list_filter = ('is_published', 'department')
    search_fields = ('name', 'summary', 'description')
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ContactMessage)
class ContactMessageAdmin(admin.ModelAdmin):
    list_display = ('full_name', 'email', 'subject', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at')
    search_fields = ('full_name', 'email', 'subject', 'message')


@admin.register(MedicalService)
class MedicalServiceAdmin(admin.ModelAdmin):
    list_display = ('name', 'department', 'is_active', 'display_order')
    list_filter = ('is_active', 'department')
    search_fields = ('name', 'description')
    prepopulated_fields = {'slug': ('name',)}
    ordering = ('display_order', 'name')


@admin.register(Announcement)
class AnnouncementAdmin(admin.ModelAdmin):
    list_display = ('title', 'category', 'is_active', 'publish_at', 'expires_at')
    list_filter = ('category', 'is_active')
    search_fields = ('title', 'message')
    date_hierarchy = 'publish_at'
@admin.register(HomeNotification)
class HomeNotificationAdmin(admin.ModelAdmin):
    list_display = ('message', 'is_active', 'updated_at')
    list_filter = ('is_active',)
