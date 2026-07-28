import mimetypes

from django.contrib import messages
from django.http import FileResponse, Http404
from django.shortcuts import render, redirect, get_object_or_404

from accounts.decorators import any_staff_required, role_required
from accounts.models import AuditLog, Role
from accounts.utils import write_audit_log
from documents.forms import DocumentUploadForm, DocumentReplaceForm
from documents.models import PatientDocument, DocumentCategory
from patients.models import Patient


@any_staff_required
def document_list(request, patient_id):
    """
    The merged, chronological document list for one patient - shown on the
    Patient Profile page and usable standalone by any department.
    """
    patient = get_object_or_404(Patient, pk=patient_id)
    documents = patient.documents.filter(is_active=True).select_related('uploaded_by')

    category = request.GET.get('category', '')
    if category:
        documents = documents.filter(category=category)

    return render(request, 'documents/document_list.html', {
        'patient': patient, 'documents': documents,
        'categories': DocumentCategory.choices, 'selected_category': category,
    })


@any_staff_required
def document_upload(request, patient_id):
    patient = get_object_or_404(Patient, pk=patient_id)
    if request.method == 'POST':
        form = DocumentUploadForm(request.POST, request.FILES)
        if form.is_valid():
            doc = form.save(commit=False)
            doc.patient = patient
            doc.uploaded_by = request.user
            doc.uploaded_by_role = request.user.effective_role
            doc.department_note = request.user.get_role_display()
            doc.save()
            write_audit_log(
                request, AuditLog.Action.DOCUMENT_UPLOADED,
                f"Uploaded {doc.get_category_display()}: {doc.title} for {patient.full_name}",
                patient_id_text=patient.patient_code,
            )
            messages.success(request, f'"{doc.title}" uploaded to {patient.full_name}\'s file.')
            return redirect('documents:document_list', patient_id=patient.pk)
    else:
        form = DocumentUploadForm()
    return render(request, 'documents/document_upload.html', {'form': form, 'patient': patient})


@any_staff_required
def document_replace(request, pk):
    doc = get_object_or_404(PatientDocument, pk=pk, is_active=True)
    if request.method == 'POST':
        form = DocumentReplaceForm(request.POST, request.FILES)
        if form.is_valid():
            new_doc = doc.replace_with(
                new_file=form.cleaned_data['file'],
                uploaded_by=request.user,
                remarks=form.cleaned_data['remarks'],
            )
            write_audit_log(
                request, AuditLog.Action.DOCUMENT_REPLACED,
                f"Replaced document \"{doc.title}\" (v{doc.version} -> v{new_doc.version}) "
                f"for {doc.patient.full_name}",
                patient_id_text=doc.patient.patient_code,
            )
            messages.success(request, 'Document replaced. Previous version kept for audit history.')
            return redirect('documents:document_list', patient_id=doc.patient_id)
    else:
        form = DocumentReplaceForm()
    return render(request, 'documents/document_replace.html', {'form': form, 'document': doc})


@any_staff_required
def document_view(request, pk):
    """Built-in viewer (spec 8: 'Do not automatically download PDFs.
    Click PDF -> Open built-in viewer.'). Served inline, not as an
    attachment, so it opens in the browser instead of triggering a save
    dialog. Available to any authorized staff role - this is the 'view
    only' route; document_download (Super Admin only) is the exception."""
    doc = get_object_or_404(PatientDocument, pk=pk, is_active=True)
    if not doc.file:
        raise Http404('File not found.')
    write_audit_log(
        request, AuditLog.Action.DOCUMENT_DOWNLOADED,
        f"Viewed \"{doc.title}\" for {doc.patient.full_name}",
        patient_id_text=doc.patient.patient_code,
    )
    content_type, _ = mimetypes.guess_type(doc.file.name)
    return FileResponse(
        doc.file.open('rb'), filename=doc.file.name.rsplit('/', 1)[-1],
        content_type=content_type or 'application/octet-stream', as_attachment=False,
    )


@role_required(Role.SUPER_ADMIN)
def document_download(request, pk):
    """Secure, authenticated file download - Super Admin only on the staff
    side (spec 8: 'Only Patients and Super Admin may download files.
    Other authorized users may view only.'). Patients download their own
    documents through patient_portal's own route instead."""
    doc = get_object_or_404(PatientDocument, pk=pk)
    if not doc.file:
        raise Http404('File not found.')
    write_audit_log(
        request, AuditLog.Action.DOCUMENT_DOWNLOADED,
        f"Downloaded \"{doc.title}\" for {doc.patient.full_name}",
        patient_id_text=doc.patient.patient_code,
    )
    return FileResponse(doc.file.open('rb'), filename=doc.file.name.rsplit('/', 1)[-1])


@role_required(Role.SUPER_ADMIN)
def document_delete(request, pk):
    """Delete a document from a patient's medical record - Super Admin
    only (spec 8 permission matrix). Soft-deleted, never hard-removed,
    so the audit trail survives."""
    doc = get_object_or_404(PatientDocument, pk=pk, is_active=True)
    if request.method == 'POST':
        doc.soft_delete(deleted_by=request.user)
        write_audit_log(
            request, AuditLog.Action.DOCUMENT_DELETED,
            f"Deleted document \"{doc.title}\" for {doc.patient.full_name}",
            patient_id_text=doc.patient.patient_code,
        )
        messages.success(request, f'"{doc.title}" deleted.')
        return redirect('documents:document_list', patient_id=doc.patient_id)
    return render(request, 'documents/document_confirm_delete.html', {'document': doc})
