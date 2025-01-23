import csv
from django.utils import timezone
from django.utils.timezone import now
from .models import Contact, Email, PhoneNumber, BackgroundJob

def process_contacts(processed_data, user, job_id):
    try:
        print("job_id", job_id)
        job = BackgroundJob.objects.filter(job_id=job_id).first()
        print("job",job)
        if job:
            job.status = "PENDING"
            job.last_run_at = now()
            job.save()
        # Define a CSV file path
        csv_file_path = "/tmp/processed_data.csv"

        # Write data to a CSV file
        with open(csv_file_path, mode="w", newline="", encoding="utf-8") as csv_file:
            csv_writer = csv.writer(csv_file)

            # Write headers
            headers = processed_data.keys()
            csv_writer.writerow(headers)

            # Write rows
            rows = zip(*processed_data.values())
            csv_writer.writerows(rows)

        print(f"Data successfully written to {csv_file_path}")

        # Process the data from the CSV file
        with open(csv_file_path, mode="r", encoding="utf-8") as csv_file:
            csv_reader = csv.DictReader(csv_file)
            processed_emails = set()  # To track processed emails
            processed_phones = set()  # To track processed phone numbers

            for row in csv_reader:
                first_name = row.get("first_name")
                last_name = row.get("last_name")
                email = row.get("email")
                phone = row.get("phone_number")
                contact_type = row.get("contact_type")
                time_zone = row.get("time_zone")

                if not email and not phone:
                    print("Skipping row: Missing email and phone number")
                    continue

                if email in processed_emails or phone in processed_phones:
                    associated_contact_email = Email.objects.filter(email=email).first()
                    associated_contact_phone = PhoneNumber.objects.filter(phone_number=phone).first()

                    if (
                        associated_contact_email
                        and associated_contact_phone
                        and associated_contact_email.contact == associated_contact_phone.contact
                    ):
                        print(f"Skipping: Both email {email} and phone {phone} are already associated with the same contact.")
                        continue

                if email:
                    processed_emails.add(email)
                if phone:
                    processed_phones.add(phone)

                contact = (
                    Contact.objects.filter(emails__email=email)
                    .union(Contact.objects.filter(phone_numbers__phone_number=phone))
                    .first()
                )

                if contact:
                    contact.first_name = first_name or contact.first_name
                    contact.last_name = last_name or contact.last_name
                    contact.contact_type = contact_type or contact.contact_type
                    contact.time_zone = time_zone or contact.time_zone
                    contact.updated_at = timezone.now()
                    contact.save()
                    print(f"Updated contact: {email or phone}")
                else:
                    contact = Contact.objects.create(
                        user=user,
                        first_name=first_name,
                        last_name=last_name,
                        contact_type=contact_type or "bulk_import",
                        time_zone=time_zone or "UTC",
                        created_at=timezone.now(),
                    )
                    print(f"Created contact: {email or phone}")

                if email:
                    existing_email = Email.objects.filter(contact=contact, email=email).first()
                    is_primary_email = not existing_email and not Email.objects.filter(contact=contact, is_primary=True).exists()
                    if not existing_email:
                        Email.objects.create(
                            contact=contact,
                            email=email,
                            user=user,
                            is_primary=is_primary_email,
                        )

                if phone:
                    existing_phone = PhoneNumber.objects.filter(phone_number=phone).first()
                    if existing_phone:
                        if existing_phone.contact != contact:
                            print(f"Phone number {phone} already exists for another contact.")
                            if not PhoneNumber.objects.filter(contact=contact, phone_number=phone).exists():
                                try:
                                    PhoneNumber.objects.create(
                                        contact=contact,
                                        phone_number=phone,
                                        user=user,
                                        is_primary=False,
                                    )
                                    print(f"Phone number {phone} added as non-primary to contact {email}")
                                except Exception as e:
                                    print(f"Error associating phone number {phone}: {e}")
                        else:
                            print(f"Phone number {phone} is already associated with this contact.")
                    else:
                        is_primary_phone = not PhoneNumber.objects.filter(contact=contact, is_primary=True).exists()
                        PhoneNumber.objects.create(
                            contact=contact,
                            phone_number=phone,
                            user=user,
                            is_primary=is_primary_phone,
                        )
        if job:
            job.status = "COMPLETED"
            job.completed_at = now()
            job.save()
        print("Contacts processed successfully!")
    except Exception as e:
        print(f"Error processing contacts: {str(e)}")
        if job:
            job.status = "FAILED"
            job.error_message = str(e)
            job.save()
