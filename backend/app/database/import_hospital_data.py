import asyncio
import csv
import os
import uuid
from datetime import datetime
from prisma import Prisma
from faker import Faker

fake = Faker()

# Define expected filenames for the other datasets
DATASETS = {
    "HOSPITAL_EMERGENCY": "backend/data/hospital_emergency.csv",
    "PATIENT_HISTORY": "backend/data/patient_history.csv",
    "MIMIC_ED": "backend/data/mimic_iv_ed.csv"
}

async def import_datasets():
    print("🚀 Starting Additional Datasets Import...")
    
    db = Prisma()
    await db.connect()

    for key, filepath in DATASETS.items():
        if not os.path.exists(filepath):
            # Check without backend prefix
            alt_path = filepath.replace("backend/", "")
            if os.path.exists(alt_path):
                filepath = alt_path
            else:
                print(f"ℹ️  Skipping {key}: File not found at {filepath}")
                continue

        print(f"📂 Processing {key} from {filepath}...")
        
        try:
            with open(filepath, mode='r', encoding='latin-1') as f:
                reader = csv.DictReader(f)
                count = 0
                for row in reader:
                    if count >= 50: break # Limit for demo

                    # Generic Import Logic - Map to EmergencyCase
                    # This requires specific logic per dataset structure.
                    # For now, we'll try to map common columns or just creation generic cases.
                    
                    # Identify columns
                    keys = row.keys()
                    
                    # Synthesize Patient
                    patient = await db.patient.create(
                        data={
                            "name": fake.name(),
                            "phone": fake.phone_number(),
                            "email": fake.email(),
                            "consentStatus": True,
                            "gender": "OTHER"
                        }
                    )
                    
                    # Create Case
                    await db.emergencycase.create(
                        data={
                            "patient": {"connect": {"id": patient.id}},
                            "severity": "URGENT", # Default
                            "symptoms": f"Imported from {key}. Data: {str(list(row.values())[:3])}",
                            "location": "Imported",
                            "status": "TRIAGED",
                            "contactNumber": patient.phone
                        }
                    )
                    count += 1
                print(f"✅ Imported {count} records from {key}")
        
        except Exception as e:
            print(f"❌ Failed to import {key}: {e}")

    await db.disconnect()
    print("✨ All imports finished.")

if __name__ == "__main__":
    asyncio.run(import_datasets())
