import asyncio
import csv
import json
import os
from prisma import Prisma
from app.ai_engine.rag_engine import vector_store, KnowledgeChunk

# File Paths
PUBMED_FILE = "data/pubmedqa-master/data/ori_pqal.json"
HEART_FILE = "data/heart_disease.csv"
DIABETES_FILE = "data/diabetes.csv"

async def import_all():
    print("🚀 Starting Advanced Medical Data Import...")
    db = Prisma()
    await db.connect()

    await import_pubmed(db)
    await import_heart(db)
    await import_diabetes(db)

    await db.disconnect()
    print("✨ All Advanced Imports Complete!")

async def import_pubmed(db):
    print(f"📚 Processing PubMedQA from {PUBMED_FILE}...")
    if not os.path.exists(PUBMED_FILE):
        print("❌ PubMedQA file not found (check path)")
        return

    with open(PUBMED_FILE, 'r') as f:
        data = json.load(f)

    count = 0
    chunks = []
    
    # Process first 50 entries
    for pid, entry in list(data.items())[:50]:
        question = entry.get("QUESTION")
        # Context is a list of strings
        context = " ".join(entry.get("CONTEXTS", []))
        answer = entry.get("LONG_ANSWER") or entry.get("final_decision", "See context.")

        if not question or not context: continue

        title = f"Research QA: {question}"
        content = f"Question: {question}\nContext: {context}\nAnswer: {answer}\n(Source: PubMedQA ID {pid})"

        # DB Create
        kb = await db.knowledgebase.create(data={
            "title": title[:200], # Limit title length
            "content": content,
            "category": "Medical Research",
            "isActive": True
        })
        chunks.append(KnowledgeChunk(id=kb.id, title=kb.title, content=kb.content, category="Medical Research"))
        count += 1

    if chunks:
        vector_store.add_documents(chunks)
        print(f"✅ Imported {count} PubMedQA entries.")

async def import_heart(db):
    print(f"❤️ Processing Heart Disease Data from {HEART_FILE}...")
    if not os.path.exists(HEART_FILE):
        print("❌ Heart Disease file not found")
        return

    # Columns: age, sex, cp, trestbps, chol, fbs, restecg, thalach, exang, oldpeak, slope, ca, thal, num
    chunks = []
    count = 0
    
    with open(HEART_FILE, 'r') as f:
        reader = csv.reader(f)
        for i, row in enumerate(reader):
            if i >= 50: break
            if len(row) < 14: continue

            try:
                age, sex, cp, bp, chol, fbs, ecg, hr, exang, oldpeak, slope, ca, thal, num = row
                
                diagnosis = "Heart Disease Present" if int(num) > 0 else "No Heart Disease"
                sex_str = "Male" if float(sex) == 1.0 else "Female"
                
                title = f"Cardiac Case Study: {sex_str}, Age {age}, {diagnosis}"
                content = (
                    f"Patient Profile:\n"
                    f"- Age: {age}, Sex: {sex_str}\n"
                    f"- Chest Pain Type: {cp} (1=typical, 2=atypical, 3=non-anginal, 4=asymptomatic)\n"
                    f"- Resting BP: {bp} mmHg, Cholesterol: {chol} mg/dl\n"
                    f"- Max HR: {hr}, Exercise Angina: {'Yes' if float(exang)==1.0 else 'No'}\n"
                    f"- Diagnosis: {diagnosis} (Severity {num})\n"
                    f"(Source: Cleveland Heart Disease Dataset)"
                )

                kb = await db.knowledgebase.create(data={
                    "title": title,
                    "content": content,
                    "category": "Cardiology Cases",
                    "isActive": True
                })
                chunks.append(KnowledgeChunk(id=kb.id, title=kb.title, content=kb.content, category="Cardiology Cases"))
                count += 1
            except Exception as e:
                continue

    if chunks:
        vector_store.add_documents(chunks)
        print(f"✅ Imported {count} Cardiac Case Studies.")

async def import_diabetes(db):
    print(f"🍬 Processing Diabetes Data from {DIABETES_FILE}...")
    if not os.path.exists(DIABETES_FILE):
        print("❌ Diabetes file not found")
        return

    chunks = []
    count = 0
    
    with open(DIABETES_FILE, 'r') as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            if i >= 50: break
            
            try:
                outcome = "Diabetic" if row["Outcome"] == "1" else "Non-Diabetic"
                title = f"Diabetes Case Study: Age {row['Age']}, {outcome}"
                content = (
                    f"Patient Profile:\n"
                    f"- Age: {row['Age']}, Pregnancies: {row['Pregnancies']}\n"
                    f"- Glucose: {row['Glucose']} mg/dL, BP: {row['BloodPressure']} mmHg\n"
                    f"- BMI: {row['BMI']}, Insulin: {row['Insulin']}\n"
                    f"- Diabetes Pedigree Function: {row['DiabetesPedigreeFunction']}\n"
                    f"- Diagnosis: {outcome}\n"
                    f"(Source: PIMA Diabetes Dataset)"
                )

                kb = await db.knowledgebase.create(data={
                    "title": title,
                    "content": content,
                    "category": "Endocrinology Cases",
                    "isActive": True
                })
                chunks.append(KnowledgeChunk(id=kb.id, title=kb.title, content=kb.content, category="Endocrinology Cases"))
                count += 1
            except Exception:
                continue

    if chunks:
        vector_store.add_documents(chunks)
        print(f"✅ Imported {count} Diabetes Case Studies.")

if __name__ == "__main__":
    asyncio.run(import_all())
