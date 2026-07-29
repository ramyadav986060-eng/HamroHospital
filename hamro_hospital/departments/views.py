from django.contrib import messages
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import super_admin_required
from departments.models import Department
from departments.forms import DepartmentForm


@super_admin_required
def department_list(request):
    departments = Department.objects.all()
    return render(request, 'departments/department_list.html', {'departments': departments})


@super_admin_required
def department_create(request):
    if request.method == 'POST':
        form = DepartmentForm(request.POST, request.FILES)
        if form.is_valid():
            department = form.save()
            messages.success(request, f'Department "{department.name}" created.')
            return redirect('departments:department_list')
    else:
        form = DepartmentForm()
    return render(request, 'departments/department_form.html', {'form': form, 'title': 'Add Department'})


@super_admin_required
def department_edit(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        form = DepartmentForm(request.POST, request.FILES, instance=department)
        if form.is_valid():
            form.save()
            messages.success(request, f'Department "{department.name}" updated.')
            return redirect('departments:department_list')
    else:
        form = DepartmentForm(instance=department)
    return render(request, 'departments/department_form.html', {
        'form': form, 'title': f'Edit {department.name}', 'department': department,
    })


@super_admin_required
def department_delete(request, pk):
    department = get_object_or_404(Department, pk=pk)
    if request.method == 'POST':
        if department.doctors.exists():
            messages.error(
                request,
                f'"{department.name}" still has doctors assigned. Deactivate it instead of deleting.'
            )
            return redirect('departments:department_list')
        name = department.name
        department.delete()
        messages.success(request, f'Department "{name}" deleted.')
        return redirect('departments:department_list')
    return render(request, 'departments/department_confirm_delete.html', {'department': department})
