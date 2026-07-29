# Seeding Commands

## The one command you actually need

```powershell
python manage.py seed_all
```

This is the **master seed command**. It:

1. Runs every prerequisite seeder automatically if the data isn't there yet
   (Nepal address database, departments, demo staff accounts, wards/beds,
   medicines, lab/radiology test catalogs, testimonials, gallery, etc.).
2. Tops up **Doctors to 150**, spread realistically across every department.
3. Tops up **Patients to 500**, each with a full Nepal address and ~35%
   carrying insurance.
4. Generates **5,000 OPD visits**, each with a consultation, 1-3
   prescription items, and (for a realistic share of visits) lab and/or
   radiology requests — many already completed with reports.
5. Generates **5,000 online appointment bookings** (paid via eSewa, ~half
   linked back to a real registered patient).
6. Generates **~4,000 bills** across OPD/Lab/Pharmacy/IPD/Other types, each
   with its own unique barcode.
7. Generates **4,000 pharmacy dispensing sales**, linked to real
   prescriptions where possible.
8. Generates **500 admissions** with ward/bed allocation (~55% already
   discharged), a matching IPD bill for each, and a surgery record for
   about 30% of them.
9. Generates **300 insurance claims** for patients who actually carry
   insurance, with a realistic mix of pending/approved/settled/rejected.

It is **safe to run more than once** — every number is a target, not an
increment, so re-running only tops up what's missing rather than creating
duplicates.

## How long does it take?
At full scale (the defaults above) it typically takes 5-10 minutes,
since each record also generates its own QR code / barcode image on disk.
If your terminal or IDE has a command timeout, either run it directly in a
plain terminal window, or seed in smaller stages (see below).

## Seeding in stages (if you hit a timeout)
Every option below defaults to the full target, but you can pass smaller
numbers and re-run repeatedly to top up gradually - each run picks up where
the last one left off:

```powershell
python manage.py seed_all --bills 1000 --pharmacy-sales 1000 --admissions 100 --insurance-claims 50
python manage.py seed_all --bills 4000 --pharmacy-sales 4000 --admissions 500 --insurance-claims 300
```

## All available options
```
--patients            (default 500)
--doctors             (default 150)
--appointments        (default 5000)
--visits              (default 5000)
--bills               (default 4000)
--pharmacy-sales      (default 4000)
--admissions          (default 500)
--insurance-claims    (default 300)
--skip-prereqs        skip the prerequisite seeders (use once they've already run)
```

## Individual seeders (advanced / already called automatically by seed_all)
These exist for granular control but you shouldn't normally need to run
them by hand:

```powershell
python manage.py seed_nepal_address        # Provinces + districts
python manage.py seed_demo_data            # Departments, a handful of doctors, disease articles
python manage.py create_demo_accounts      # One demo login per staff role
python manage.py seed_checkpoint3_data     # Wards/beds, blood bank, initial patients/visits, surgeries
python manage.py seed_final_requirements   # Medicines, lab/radiology catalogs, insurance companies, testimonials, gallery
```

## Starting over
To wipe and re-seed from scratch:
```powershell
python manage.py flush --noinput
python manage.py seed_all
```
`flush` clears all data but keeps your schema/migrations, so you don't
need to re-run `migrate` afterwards.
