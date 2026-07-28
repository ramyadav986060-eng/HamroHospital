from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import super_admin_required
from departments.models import Department
from doctors.models import Doctor
from website.models import Testimonial, GalleryImage, DiseaseInfo, HospitalService, MedicalService
from website.forms import ContactForm, HospitalServiceForm


def home(request):
    context = {
        'departments': Department.objects.filter(is_active=True)[:8],
        'featured_doctors': Doctor.objects.filter(is_active=True, is_featured=True)[:6],
        'diseases': DiseaseInfo.objects.filter(is_published=True)[:8],
        'testimonials': Testimonial.objects.filter(is_published=True)[:6],
        'gallery_images': GalleryImage.objects.filter(is_published=True)[:8],
    }
    return render(request, 'website/home.html', context)


def about(request):
    return render(request, 'website/about.html')


def department_list(request):
    departments = Department.objects.filter(is_active=True)
    return render(request, 'website/department_list.html', {'departments': departments})


def department_detail(request, slug):
    department = get_object_or_404(Department, slug=slug, is_active=True)
    doctors = department.doctors.filter(is_active=True).select_related('unit').prefetch_related('schedules')
    return render(request, 'website/department_detail.html', {
        'department': department, 'doctors': doctors,
        'units': department.units.all(),
    })


def doctor_list(request):
    doctors = Doctor.objects.filter(is_active=True).select_related('department', 'unit')
    department_id = request.GET.get('department')
    if department_id:
        doctors = doctors.filter(department_id=department_id)
    search = request.GET.get('q', '').strip()
    if search:
        from django.db.models import Q
        needle = search[3:].strip() if search.lower().startswith('dr ') else search
        doctors = doctors.filter(
            Q(full_name__icontains=needle) | Q(specialization__icontains=needle) | Q(department__name__icontains=needle)
        )
    return render(request, 'website/doctor_list.html', {
        'doctors': doctors, 'departments': Department.objects.filter(is_active=True),
        'selected_department': department_id, 'search_query': search,
    })


def doctor_detail(request, pk):
    doctor = get_object_or_404(Doctor, pk=pk, is_active=True)
    return render(request, 'website/doctor_detail.html', {'doctor': doctor})


def medical_services(request):
    services = MedicalService.objects.filter(is_active=True).select_related('department')
    return render(request, 'website/medical_services.html', {'services': services})


def disease_list(request):
    diseases = DiseaseInfo.objects.filter(is_published=True)
    return render(request, 'website/disease_list.html', {'diseases': diseases})


def disease_detail(request, slug):
    disease = get_object_or_404(DiseaseInfo, slug=slug, is_published=True)
    return render(request, 'website/disease_detail.html', {'disease': disease})


def contact(request):
    if request.method == 'POST':
        form = ContactForm(request.POST)
        if form.is_valid():
            contact_msg = form.save()
            
            # Create an internal notification for Super Admin (spec section 6)
            from accounts.utils import create_notification
            from accounts.models import Role
            create_notification(
                title="New Contact Message",
                message=f"Received message from {contact_msg.full_name} ({contact_msg.email}) on '{contact_msg.subject}': '{contact_msg.message[:60]}...'",
                role=Role.SUPER_ADMIN
            )
            
            messages.success(request, "Thank you! Your message has been received. We'll get back to you soon.")
            return redirect('website:contact')
    else:
        form = ContactForm()
    return render(request, 'website/contact.html', {'form': form})


def gallery(request):
    images = GalleryImage.objects.filter(is_published=True)
    return render(request, 'website/gallery.html', {'images': images})


# --- Super Admin: Hospital Services catalogue --------------------------------

@super_admin_required
def service_list(request):
    services = HospitalService.objects.select_related('department').all()
    return render(request, 'website/service_list.html', {'services': services})


@super_admin_required
def service_create(request):
    if request.method == 'POST':
        form = HospitalServiceForm(request.POST)
        if form.is_valid():
            service = form.save()
            messages.success(request, f'Service "{service.name}" added.')
            return redirect('website:service_list')
    else:
        form = HospitalServiceForm()
    return render(request, 'website/service_form.html', {'form': form, 'title': 'Add Hospital Service'})


@super_admin_required
def service_edit(request, pk):
    service = get_object_or_404(HospitalService, pk=pk)
    if request.method == 'POST':
        form = HospitalServiceForm(request.POST, instance=service)
        if form.is_valid():
            form.save()
            messages.success(request, f'Service "{service.name}" updated.')
            return redirect('website:service_list')
    else:
        form = HospitalServiceForm(instance=service)
    return render(request, 'website/service_form.html', {'form': form, 'title': f'Edit {service.name}'})


def assistant_api(request):
    """
    Public-facing AI Assistant for Hamro Hospital (spec section 1).
    Answers hospital-related questions only.
    """
    from django.http import JsonResponse
    from django.db.models import Q
    from doctors.models import Doctor
    from departments.models import Department
    import datetime

    query = request.GET.get('q', '').strip()
    if not query:
        return JsonResponse({'response': "Hello! Ask me anything about Hamro Hospital."})

    q_lower = query.lower()

    # Define allowed keywords (only hospital-related queries are allowed)
    is_hospital_related = any(w in q_lower for w in [
        'dr', 'doctor', 'schedule', 'timing', 'opd', 'emergency', 'hour', 'open', 'close',
        'location', 'service', 'facility', 'contact', 'phone', 'email', 'address',
        'appointment', 'book', 'insurance', 'visit', 'pharmacy', 'about', 'fee', 'charge', 'help'
    ])

    if not is_hospital_related:
        return JsonResponse({'response': "I can only answer questions related to Hamro Hospital services, schedules, contact info, and departments. Please ask me hospital-related queries!"})

    # OPD timings
    if 'opd' in q_lower or 'opening hours' in q_lower or 'timing' in q_lower or 'opening' in q_lower:
        return JsonResponse({'response': "Hamro Hospital's OPD registration is open Sunday to Thursday from 8:00 AM to 2:00 PM, and Friday from 8:00 AM to 12:00 PM. Emergency services are open 24/7."})

    # Emergency timing
    if 'emergency' in q_lower:
        return JsonResponse({'response': "The Emergency Department of Hamro Hospital is fully functional and open 24 hours a day, 7 days a week, including public holidays."})

    # Visiting hours
    if 'visiting' in q_lower or 'visit' in q_lower:
        return JsonResponse({'response': "Patient visiting hours in the Wards are from 4:00 PM to 6:00 PM daily. Only one visitor with an official visitor pass is allowed per patient."})

    # Contact information
    if 'contact' in q_lower or 'phone' in q_lower or 'email' in q_lower or 'address' in q_lower:
        return JsonResponse({'response': "You can contact Hamro Hospital at our primary line: 01-4412345, or Emergency: 01-4412346. Email: info@hamrohospital.example.np. Address: Maharajgunj, Kathmandu, Nepal."})

    # How to book an appointment
    if 'book' in q_lower or 'appointment' in q_lower:
        return JsonResponse({'response': "To book an appointment, you can either: 1) Book online through our website's Appointment booking page, 2) Log in to your Patient Portal account, or 3) Visit the Registration Counter physically in Maharajgunj."})

    # Insurance
    if 'insurance' in q_lower:
        return JsonResponse({'response': "We support major health insurance companies of Nepal, including Nepal Life Insurance and government health insurance schemes. Please present your insurance card at the Insurance Counter for claim validation."})

    # Doctors & schedule
    if 'doctor' in q_lower or 'dr' in q_lower:
        # Extract doctor's name if typed
        name_part = q_lower.replace('where is dr.', '').replace('where is dr', '').replace('is there dr', '').replace('schedule of dr', '').replace('doctor', '').replace('dr', '').strip()
        for w in ['please', 'now', '?', 'is', 'located', 'available', 'today']:
            name_part = name_part.replace(w, '').strip()

        if name_part:
            doc = Doctor.objects.filter(full_name__icontains=name_part).first()
            if doc:
                dept_name = doc.department.name if doc.department else "General OPD"
                return JsonResponse({'response': f"Dr. {doc.full_name} ({doc.qualification}) is in the {dept_name} department. Specialization: {doc.specialization}. Available days: {doc.available_days.upper()}. Consultation Fee: NPR {doc.consultation_fee}."})
            
        # List of departments or general doctor availability
        return JsonResponse({'response': "We have leading doctors available today in Cardiology, Pediatrics, Orthopedics, Gynecology, and General Medicine. You can view our full Doctors Directory or filter by department on our website."})

    # Locations & Departments
    if 'location' in q_lower or 'department' in q_lower:
        return JsonResponse({'response': "Hamro Hospital is located in Maharajgunj, Kathmandu. The OPD block is on the west wing, emergency block on the east wing, and inpatient wards on the main building upper floors."})

    # General fallback
    return JsonResponse({'response': "Hello! I am the Hamro Hospital public assistant. You can ask me about doctor availability, OPD/emergency timings, hospital locations, services, or contact details."})
