import asyncio
import csv
import os
from prisma import Prisma
from app.ai_engine.rag_engine import vector_store, KnowledgeChunk

INPUT_FILE = "backend/data/symptoms_disease.csv"

async def import_symptoms():
    print("🚀 Starting Disease-Symptom Data Import...")
    
    db = Prisma()
    await db.connect()

    target_file = INPUT_FILE
    if not os.path.exists(target_file):
        print(f"❌ File not found: {target_file}")
        # Try relative path
        if os.path.exists("data/symptoms_disease.csv"):
            target_file = "data/symptoms_disease.csv"
        else:
            return

    # Dictionary to aggregate symptoms by disease
    # Structure: { "DiseaseName": { "symptoms": set(), "count": 0 } }
    disease_map = {}

    print(f"📄 Reading {target_file}...")
    with open(target_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        
        # Identify symptom columns (all except 'prognosis')
        symptom_cols = [col for col in fieldnames if col != "prognosis"]
        
        for row in reader:
            disease = row.get("prognosis")
            if not disease: continue
            
            if disease not in disease_map:
                disease_map[disease] = {"symptoms": set(), "count": 0}
            
            disease_map[disease]["count"] += 1
            
            # Find active symptoms in this row
            for symptom in symptom_cols:
                if row.get(symptom) == "1":
                    # Clean symptom name (e.g., "itching" -> "itching")
                    clean_symptom = symptom.replace("_", " ")
                    disease_map[disease]["symptoms"].add(clean_symptom)

    print(f"📊 Found {len(disease_map)} unique diseases.")
    
    count = 0
    chunks_to_index = []
    
    for disease, data in disease_map.items():
        symptoms_list = list(data["symptoms"])
        symptoms_str = ", ".join(sorted(symptoms_list))
        
        title = f"Symptoms of {disease}"
        content = f"Common symptoms of {disease} include: {symptoms_str}. (Source: Disease Prediction Dataset)"
        
        # Check existing
        existing = await db.knowledgebase.find_first(where={"title": title})
        if existing:
            continue
            
        # Create DB Entry
        kb_entry = await db.knowledgebase.create(
            data={
                "title": title,
                "content": content,
                "category": "Medical Conditions",
                "isActive": True
            }
        )
        count += 1
        
        # Prepare for Indexing
        chunks_to_index.append(
            KnowledgeChunk(
                id=kb_entry.id,
                title=kb_entry.title,
                content=kb_entry.content,
                category="Medical Conditions"
            )
        )
            
    print(f"✅ Imported {count} disease profiles.")

    # Index
    if chunks_to_index:
        print(f"🧠 Indexing {len(chunks_to_index)} disease profiles...")
        try:
            vector_store.add_documents(chunks_to_index)
            print("✅ Vector Index Updated!")
        except Exception as e:
            print(f"⚠️ Indexing failed: {e}")

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(import_symptoms())
