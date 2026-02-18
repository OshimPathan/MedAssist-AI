import asyncio
import csv
import os
import uuid
import random
from datetime import datetime, timezone, timedelta
from prisma import Prisma
from faker import Faker

fake = Faker()

INPUT_FILE = "backend/data/Triage.csv.xls"

async def import_data():
    print("🚀 Starting Import from Real Triage Data (Kaggle)...")
    
    db = Prisma()
    await db.connect()

    # Read CSV
    input_file = INPUT_FILE
    if not os.path.exists(input_file):
        print(f"❌ File not found: {input_file}")
        # Try without backend prefix just in case cwd is different
        INPUT_FILE_ALT = "data/Triage.csv.xls"
        if os.path.exists(INPUT_FILE_ALT):
            input_file = INPUT_FILE_ALT
        else:
            return

    count_patients = 0
    count_cases = 0

    with open(input_file, mode='r', encoding='latin-1') as f:
        # Use semi-colon separator for this dataset
        csv_reader = csv.DictReader(f, delimiter=';') 
        
        # Process only first 50 for demo speed
        for i, row in enumerate(csv_reader):
            if i >= 50: break
            
            try:
                # 1. Generate Fake Patient based on Data
                sex_code = row.get("Sex", "1")
                gender = "Male" if sex_code == "1" else "Female"
                age = int(row.get("Age", "30"))
                
                # Calculate DOB from Age
                dob = datetime.now() - timedelta(days=age*365)
                
                # Generate Name
                if gender == "Male":
                    first_name = fake.first_name_male()
                    last_name = fake.last_name()
                else:
                    first_name = fake.first_name_female()
                    last_name = fake.last_name()
                
                email = f"{first_name.lower()}.{last_name.lower()}{i}@example.com"
                phone = fake.phone_number()

                # Create Patient
                patient = await db.patient.create(
                    data={
                        "name": f"{first_name} {last_name}",
                        "age": age,
                        "gender": gender.upper(),
                        "phone": phone,
                        "email": email,
                        "consentStatus": True
                    }
                )
                count_patients += 1

                # 2. Map Clinical Data to Emergency Case
                # KTAS_RN (1-5): 1=Resuscitation, 2=Emergency, 3=Urgent, 4=Less Urgent, 5=Non Urgent
                ktas = int(row.get("KTAS_RN", "3"))
                if ktas <= 2:
                    severity = "CRITICAL"
                elif ktas == 3:
                    severity = "URGENT"
                else:
                    severity = "NON_URGENT"

                # Disposition (1=Admission, 2=Discharge typically in this dataset)
                disposition = row.get("Disposition", "2")
                dispatch_status = "DISPATCHED" if disposition == "1" else "PENDING"

                # Construct detailed symptoms string
                chief_complaint = row.get("Chief_complain", "Unknown")
                injury = "Yes" if row.get("Injury") == "1" else "No"
                pain_score = row.get("NRS_pain", "0")
                
                # Vitals
                sbp = row.get("SBP")
                dbp = row.get("DBP")
                hr = row.get("HR")
                rr = row.get("RR")
                bt = row.get("BT")
                sat = row.get("Saturation")

                symptoms_desc = (
                    f"Complaint: {chief_complaint}. "
                    f"Injury: {injury}. "
                    f"Pain (NRS): {pain_score}/10. "
                    f"Vitals: BP {sbp}/{dbp}, HR {hr}, RR {rr}, Temp {bt}, Sat {sat}%."
                )

                diagnosis = row.get("Diagnosis in ED", "Pending")

                # Create Emergency Case
                await db.emergencycase.create(
                    data={
                        "patient": {"connect": {"id": patient.id}},
                        "severity": severity,
                        "dispatchStatus": dispatch_status,
                        "symptoms": symptoms_desc,
                        "location": "Triage Imported",
                        "contactNumber": phone,
                        "notes": f"Diagnosis: {diagnosis}. Original KTAS: {ktas}",
                        "createdAt": datetime.now(timezone.utc)
                    }
                )
                count_cases += 1
                
            except Exception as e:
                print(f"⚠️ Error processing row {i}: {e}")
                continue

    print("✅ Import Complete!")
    print(f"   Patients Created: {count_patients}")
    print(f"   Cases Created: {count_cases}")

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(import_data())
