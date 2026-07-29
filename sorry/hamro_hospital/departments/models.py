from django.db import models
from django.utils.text import slugify


class Department(models.Model):
    name = models.CharField(max_length=100, unique=True)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    description = models.TextField()
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    icon_class = models.CharField(
        max_length=60, blank=True,
        help_text="Bootstrap Icons / Font Awesome class, e.g. 'bi bi-heart-pulse'",
    )
    photo = models.ImageField(upload_to='departments/', blank=True, null=True)
    is_active = models.BooleanField(default=True)
    display_order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'departments_department'
        ordering = ['display_order', 'name']

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name)
        super().save(*args, **kwargs)

    @property
    def active_doctor_count(self):
        return self.doctors.filter(is_active=True).count()


class DepartmentUnit(models.Model):
    """
    A sub-unit within a department (e.g. "Unit 1", "Unit 2"), each of which
    can run its own OPD schedule via DoctorSchedule. Purely organisational —
    doctors optionally belong to one unit of their department.
    """
    department = models.ForeignKey(Department, on_delete=models.CASCADE, related_name='units')
    name = models.CharField(max_length=100, help_text='e.g. "Unit 1", "Unit 2", "General Unit"')
    description = models.CharField(max_length=255, blank=True)
    display_order = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'departments_departmentunit'
        ordering = ['display_order', 'name']
        unique_together = [('department', 'name')]

    def __str__(self):
        return f"{self.department.name} - {self.name}"
