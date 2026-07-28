from django.db import models


class Weekday(models.TextChoices):
    SUNDAY = 'sun', 'Sunday'
    MONDAY = 'mon', 'Monday'
    TUESDAY = 'tue', 'Tuesday'
    WEDNESDAY = 'wed', 'Wednesday'
    THURSDAY = 'thu', 'Thursday'
    FRIDAY = 'fri', 'Friday'
    SATURDAY = 'sat', 'Saturday'


class Doctor(models.Model):
    """
    Doctor profile, managed by Super Admin. Optionally linked 1:1 to a User
    account with role='doctor' so the doctor can log in and use the
    Consultation module (added in a later checkpoint).
    """
    user_account = models.OneToOneField(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='doctor_profile',
        help_text='Optional login account for this doctor (role must be "Doctor").',
    )
    department = models.ForeignKey(
        'departments.Department', on_delete=models.PROTECT, related_name='doctors',
    )
    full_name = models.CharField(max_length=150)
    qualification = models.CharField(max_length=200, help_text='e.g. MBBS, MD (Cardiology)')
    specialization = models.CharField(max_length=200)
    experience_years = models.PositiveIntegerField(default=0)
    consultation_fee = models.DecimalField(max_digits=8, decimal_places=2)
    biography = models.TextField(blank=True)
    short_introduction = models.CharField(
        max_length=300, blank=True,
        help_text='One or two lines shown on the public doctor profile (kept short by design).',
    )
    contact_number = models.CharField(max_length=20, blank=True, help_text='Optional — shown on public profile if set.')
    unit = models.ForeignKey(
        'departments.DepartmentUnit', on_delete=models.SET_NULL, null=True, blank=True,
        related_name='doctors', help_text='Optional sub-unit within the department (e.g. Unit 1).',
    )
    photo = models.ImageField(upload_to='doctors/', blank=True, null=True)

    available_days = models.CharField(
        max_length=40, blank=True,
        help_text='Comma-separated weekday codes, e.g. "mon,tue,wed,thu,fri"',
    )
    available_time_start = models.TimeField(null=True, blank=True)
    available_time_end = models.TimeField(null=True, blank=True)

    is_active = models.BooleanField(default=True)
    is_featured = models.BooleanField(default=False, help_text='Show on homepage "Featured Doctors"')

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'doctors_doctor'
        ordering = ['full_name']

    def __str__(self):
        return f"Dr. {self.full_name} ({self.department.name})"

    def available_days_list(self):
        codes = [c.strip() for c in self.available_days.split(',') if c.strip()]
        lookup = dict(Weekday.choices)
        return [lookup.get(c, c) for c in codes]

    def weekly_schedule(self):
        """
        Sunday-through-Saturday list of {code, label, schedule} for the
        public department/doctor pages. `schedule` is the matching
        DoctorSchedule row, or None if the doctor has none set for that day.
        """
        by_weekday = {s.weekday: s for s in self.schedules.all()}
        return [
            {'code': code, 'label': label, 'schedule': by_weekday.get(code)}
            for code, label in Weekday.choices
        ]

    # ---- Doctor Quota / Leave (spec section 12) -----------------------
    _WEEKDAY_CODES = ['sun', 'mon', 'tue', 'wed', 'thu', 'fri', 'sat']

    def is_on_leave(self, date):
        """True if the doctor has marked leave/holiday/off-duty for this date."""
        return self.leaves.filter(date=date).exists()

    def quota_for_date(self, date):
        """
        Max patients this doctor can see on `date`.
        Returns None if no quota has been configured (treated as unlimited,
        so existing doctors keep working exactly as before until an admin
        sets a quota for them).
        A Super Admin per-date override always wins over the weekly default.
        """
        override = self.quota_overrides.filter(date=date).first()
        if override:
            return override.quota
        weekday_code = self._WEEKDAY_CODES[(date.weekday() + 1) % 7]
        weekly = self.weekly_quotas.filter(weekday=weekday_code).first()
        if weekly:
            return weekly.quota
        return None

    def booked_count_for_date(self, date):
        """Walk-in OPD visits + online appointments already booked with this doctor on `date`."""
        from patients.models import Visit
        from appointments.models import Appointment
        # PENDING visits still occupy a slot, so nothing is excluded here.
        visit_count = Visit.objects.filter(doctor=self, visit_date=date).count()
        appt_count = Appointment.objects.filter(doctor=self, preferred_date=date) \
            .exclude(payment_status=Appointment.PaymentStatus.FAILED).count()
        return visit_count + appt_count

    def is_available_for_date(self, date):
        """False if on leave/holiday, or the daily quota (if any) is already full."""
        if not self.is_active:
            return False
        if self.is_on_leave(date):
            return False
        quota = self.quota_for_date(date)
        if quota is not None and quota <= 0:
            return False
        if quota is not None and self.booked_count_for_date(date) >= quota:
            return False
        return True

    def remaining_quota_for_date(self, date):
        """Remaining slots for `date`, or None if the doctor has no quota configured."""
        quota = self.quota_for_date(date)
        if quota is None:
            return None
        return max(0, quota - self.booked_count_for_date(date))


class DoctorLeave(models.Model):
    """A single date on which a doctor is unavailable: leave, holiday, or off-duty."""
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='leaves')
    date = models.DateField()
    reason = models.CharField(max_length=200, blank=True, help_text='e.g. Leave, Holiday, Off Duty, Conference')
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'doctors_doctorleave'
        unique_together = [('doctor', 'date')]
        ordering = ['-date']

    def __str__(self):
        return f"{self.doctor.full_name} unavailable on {self.date} ({self.reason or 'Leave'})"


class DoctorWeeklyQuota(models.Model):
    """Default number of patients a doctor can see on a given weekday. 0 = not available that day."""
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='weekly_quotas')
    weekday = models.CharField(max_length=3, choices=Weekday.choices)
    quota = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = 'doctors_doctorweeklyquota'
        unique_together = [('doctor', 'weekday')]
        ordering = ['doctor', 'weekday']

    def __str__(self):
        return f"{self.doctor.full_name} - {self.get_weekday_display()}: {self.quota}"


class DoctorQuotaOverride(models.Model):
    """Super Admin override of a doctor's quota for one specific calendar date."""
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='quota_overrides')
    date = models.DateField()
    quota = models.PositiveIntegerField()
    created_by = models.ForeignKey(
        'accounts.User', on_delete=models.SET_NULL, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'doctors_doctorquotaoverride'
        unique_together = [('doctor', 'date')]
        ordering = ['-date']

    def __str__(self):
        return f"{self.doctor.full_name} override {self.date}: {self.quota}"


class DoctorSchedule(models.Model):
    """
    Structured, per-weekday OPD schedule for the public website (spec
    sections 11/12): "Department + Doctors + Unit + Sunday..Saturday
    schedule". Additive alongside the existing free-text `available_days` /
    `available_time_start` / `available_time_end` fields on Doctor, which
    remain unchanged and keep powering the appointment booking form.
    """
    doctor = models.ForeignKey(Doctor, on_delete=models.CASCADE, related_name='schedules')
    weekday = models.CharField(max_length=3, choices=Weekday.choices)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room_or_unit_note = models.CharField(max_length=100, blank=True, help_text='e.g. "OPD Room 12"')

    class Meta:
        db_table = 'doctors_doctorschedule'
        unique_together = [('doctor', 'weekday')]
        ordering = ['doctor', 'weekday']

    def __str__(self):
        return f"{self.doctor.full_name} - {self.get_weekday_display()} {self.start_time}-{self.end_time}"
