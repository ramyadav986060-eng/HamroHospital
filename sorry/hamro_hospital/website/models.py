from django.db import models
from django.utils import timezone


class HospitalService(models.Model):
    """
    Master catalogue of billable hospital services (OPD Consultation,
    Emergency, ECG, X-Ray, Blood Test, Surgery, etc). Managed only by
    Super Admin; used throughout Billing and Pharmacy for line items.
    Cash Counter can select these but never edit their price.
    """
    service_code = models.CharField(max_length=30, unique=True)
    name = models.CharField(max_length=150)
    department = models.ForeignKey(
        'departments.Department', on_delete=models.SET_NULL, null=True, blank=True, related_name='services',
    )
    price = models.DecimalField(max_digits=10, decimal_places=2)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'website_hospital_service'
        ordering = ['name']

    def __str__(self):
        return f"{self.name} (NPR {self.price})"


class Testimonial(models.Model):
    patient_name = models.CharField(max_length=150)
    photo = models.ImageField(upload_to='testimonials/', blank=True, null=True)
    message = models.TextField()
    rating = models.PositiveSmallIntegerField(default=5, help_text='Out of 5')
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'website_testimonial'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.patient_name} ({self.rating}/5)"


class GalleryImage(models.Model):
    title = models.CharField(max_length=150)
    image = models.ImageField(upload_to='gallery/')
    caption = models.CharField(max_length=255, blank=True)
    is_published = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'website_gallery_image'
        ordering = ['display_order', '-created_at']

    def __str__(self):
        return self.title


class DiseaseInfo(models.Model):
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True)
    department = models.ForeignKey(
        'departments.Department', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='diseases',
    )
    summary = models.CharField(max_length=300)
    description = models.TextField()
    symptoms = models.TextField(blank=True, help_text='One symptom per line')
    icon_class = models.CharField(
        max_length=60, blank=True,
        help_text="Bootstrap Icons / Font Awesome class, e.g. 'bi bi-heart-pulse'",
    )
    is_published = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'website_disease_info'
        ordering = ['name']

    def __str__(self):
        return self.name

    def symptom_list(self):
        return [line.strip() for line in self.symptoms.splitlines() if line.strip()]


class ContactMessage(models.Model):
    full_name = models.CharField(max_length=150)
    email = models.EmailField()
    phone_number = models.CharField(max_length=20, blank=True)
    subject = models.CharField(max_length=200)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'website_contact_message'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.full_name} - {self.subject}"


class MedicalService(models.Model):
    """
    Public-facing Medical Services directory (spec section 10). Deliberately
    separate from HospitalService (the billable catalogue used in Billing/
    Pharmacy) — this one has no price and is purely informational, shown in
    an accordion on the public Medical Services page.
    """
    name = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    description = models.TextField()
    icon_class = models.CharField(
        max_length=60, blank=True,
        help_text="Bootstrap Icons class, e.g. 'bi bi-heart-pulse'",
    )
    department = models.ForeignKey(
        'departments.Department', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='medical_services',
        help_text='Optional — links this service to a department so doctors/schedule can be shown.',
    )
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'website_medical_service'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            from django.utils.text import slugify
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)


class Announcement(models.Model):
    """
    Public site-wide notices shown from the notification icon in the navbar
    (spec section 5) — visible to every visitor, not just logged-in staff
    (that's the separate accounts.Notification system).
    """
    class Category(models.TextChoices):
        APPOINTMENT = 'appointment', 'Online Appointment Available'
        PAYMENT = 'payment', 'eSewa Payment Available'
        NOTICE = 'notice', 'Hospital Notice'
        HOLIDAY = 'holiday', 'Holiday Notice'
        SERVICE = 'service', 'New Service'

    title = models.CharField(max_length=200)
    message = models.CharField(max_length=300)
    category = models.CharField(max_length=20, choices=Category.choices, default=Category.NOTICE)
    is_active = models.BooleanField(default=True)
    publish_at = models.DateTimeField(default=timezone.now)
    expires_at = models.DateTimeField(null=True, blank=True, help_text='Leave blank to show indefinitely.')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'website_announcement'
        ordering = ['-publish_at']

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"

    @property
    def icon_class(self):
        return {
            self.Category.APPOINTMENT: 'bi bi-calendar-check',
            self.Category.PAYMENT: 'bi bi-wallet2',
            self.Category.NOTICE: 'bi bi-megaphone',
            self.Category.HOLIDAY: 'bi bi-calendar-heart',
            self.Category.SERVICE: 'bi bi-stars',
        }.get(self.category, 'bi bi-bell')

class HomeNotification(models.Model):
    """
    Second notification system specifically for the scrolling banner
    at the top of the homepage.
    """
    message = models.TextField(help_text="Nepali text to scroll (e.g. 'हाम्रो अस्पतालमा तपाईंलाई हार्दिक स्वागत छ।')")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'website_home_notification'
        ordering = ['-updated_at']

    def __str__(self):
        return self.message[:50]
