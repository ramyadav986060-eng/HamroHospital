document.addEventListener('DOMContentLoaded', function () {

    // Auto-dismiss alerts after 6 seconds
    document.querySelectorAll('.alert').forEach(function (alertEl) {
        setTimeout(function () {
            const alert = bootstrap.Alert.getOrCreateInstance(alertEl);
            alert.close();
        }, 6000);
    });

    // Show/hide insurance fields based on "Has Insurance" checkbox
    const hasInsurance = document.getElementById('id_has_insurance');
    const insuranceBlock = document.getElementById('insurance-fields');
    function toggleInsurance() {
        if (!hasInsurance || !insuranceBlock) return;
        insuranceBlock.style.display = hasInsurance.checked ? 'block' : 'none';
    }
    if (hasInsurance) {
        hasInsurance.addEventListener('change', toggleInsurance);
        toggleInsurance();
    }

    // Auto-update registration fee based on patient type (New/Old) - no manual entry
    const patientType = document.getElementById('id_patient_type');
    const feeDisplay = document.getElementById('fee-display');
    if (patientType && feeDisplay) {
        const NEW_FEE = feeDisplay.dataset.newFee || 100;
        const OLD_FEE = feeDisplay.dataset.oldFee || 50;
        function updateFee() {
            feeDisplay.textContent = patientType.value === 'new' ? NEW_FEE : OLD_FEE;
        }
        patientType.addEventListener('change', updateFee);
        updateFee();
    }

    // Department -> Doctor dependent dropdown (fetches via AJAX)
    const deptSelect = document.getElementById('id_department');
    const doctorSelect = document.getElementById('id_doctor');
    if (deptSelect && doctorSelect) {
        deptSelect.addEventListener('change', function () {
            const deptId = this.value;
            doctorSelect.innerHTML = '<option value="">Loading...</option>';
            if (!deptId) {
                doctorSelect.innerHTML = '<option value="">---------</option>';
                return;
            }
            fetch(`/patients/ajax/department/${deptId}/doctors/`)
                .then(res => res.json())
                .then(data => {
                    doctorSelect.innerHTML = '<option value="">-- Any available doctor --</option>';
                    data.doctors.forEach(doc => {
                        const opt = document.createElement('option');
                        opt.value = doc.id;
                        opt.textContent = `${doc.full_name} (NPR ${doc.consultation_fee})`;
                        doctorSelect.appendChild(opt);
                    });
                })
                .catch(() => {
                    doctorSelect.innerHTML = '<option value="">-- Could not load doctors --</option>';
                });
        });
    }

    // Age entry -> approximate Date of Birth preview (spec section 12).
    // The authoritative calculation happens server-side in PatientForm.clean()
    // (patients/utils.py: parse_age_to_dob); this just gives the user instant
    // feedback and pre-fills the Date of Birth field so they rarely need to
    // touch it manually.
    const ageInput = document.getElementById('id_age_input');
    const dobInput = document.getElementById('id_date_of_birth');
    const dobHint = document.getElementById('approx-dob-hint');
    function parseAgeToDob(text) {
        if (!text) return null;
        const re = /(?:(\d+)\s*y(?:ea)?rs?)?\s*,?\s*(?:(\d+)\s*m(?:o(?:nth)?s?)?)?\s*,?\s*(?:(\d+)\s*d(?:ay)?s?)?/i;
        const m = text.trim().match(re);
        if (!m) return null;
        const years = parseInt(m[1] || '0', 10);
        const months = parseInt(m[2] || '0', 10);
        const days = parseInt(m[3] || '0', 10);
        if (!years && !months && !days) return null;
        const today = new Date();
        const dob = new Date(today.getFullYear(), today.getMonth(), today.getDate());
        dob.setMonth(dob.getMonth() - (years * 12 + months));
        dob.setDate(dob.getDate() - days);
        return dob;
    }
    function toDateInputValue(d) {
        const pad = (n) => String(n).padStart(2, '0');
        return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`;
    }
    if (ageInput && dobInput) {
        ageInput.addEventListener('input', function () {
            const dob = parseAgeToDob(ageInput.value);
            if (dob) {
                dobInput.value = toDateInputValue(dob);
                if (dobHint) dobHint.textContent = `Approximate DOB: ${toDateInputValue(dob)} (you can edit this manually)`;
            } else if (dobHint) {
                dobHint.textContent = '';
            }
        });
    }

    // Real typeahead for select boxes (spec section 11): typing suggests options.
    // Converts the plain <select> into a text input backed by a <datalist> built from its own options.
    document.querySelectorAll('.district-autocomplete, .autocomplete-select').forEach(function (select) {
        if (select.dataset.typeaheadReady) return;
        select.dataset.typeaheadReady = 'true';

        const listId = select.id + '_list';
        const datalist = document.createElement('datalist');
        datalist.id = listId;

        const optionByLabel = {};
        Array.from(select.options).forEach(function (opt) {
            if (!opt.value) return;
            const dataOpt = document.createElement('option');
            dataOpt.value = opt.textContent;
            datalist.appendChild(dataOpt);
            optionByLabel[opt.textContent.trim()] = opt.value;
        });

        const textInput = document.createElement('input');
        textInput.type = 'text';
        textInput.className = select.className;
        textInput.setAttribute('list', listId);
        textInput.setAttribute('autocomplete', 'off');
        textInput.placeholder = 'Type to search district, e.g. "KAT" for Kathmandu';
        const selectedOption = select.options[select.selectedIndex];
        if (selectedOption && selectedOption.value) {
            textInput.value = selectedOption.textContent.trim();
        }

        select.style.display = 'none';
        select.insertAdjacentElement('afterend', textInput);
        textInput.insertAdjacentElement('afterend', datalist);

        function syncSelectFromText() {
            const match = optionByLabel[textInput.value.trim()];
            if (match) {
                select.value = match;
            }
        }
        textInput.addEventListener('input', syncSelectFromText);
        textInput.addEventListener('change', syncSelectFromText);
    });

    // Print buttons
    document.querySelectorAll('.btn-print').forEach(function (btn) {
        btn.addEventListener('click', function () {
            window.print();
        });
    });
});
