import asyncio
import csv
import os
from prisma import Prisma
from app.ai_engine.rag_engine import vector_store, KnowledgeChunk

INPUT_FILE = "backend/data/cdc_dataset.csv"

async def import_cdc_data():
    print("🚀 Starting CDC Public Health Data Import...")
    
    db = Prisma()
    await db.connect()

    # Fix scope issue by using local variable
    target_file = INPUT_FILE
    if not os.path.exists(target_file):
        print(f"❌ File not found: {target_file}")
        # Try relative path
        if os.path.exists("data/cdc_dataset.csv"):
            target_file = "data/cdc_dataset.csv"
        else:
            return

    count = 0
    chunks_to_index = []

    with open(target_file, mode='r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for i, row in enumerate(reader):
            if i >= 100: break # Limit for demo speed

            state = row.get("StateDesc")
            county = row.get("CountyName")
            measure = row.get("Measure")
            value = row.get("Data_Value")
            unit = row.get("Data_Value_Unit")
            category = row.get("Category")

            if not value or not measure:
                continue

            # Create a natural language fact
            title = f"{measure} in {county}, {state}"
            content = f"In {county} County, {state}, the prevalence of {measure} was {value}{unit} (Source: CDC PLACES 2023)."
            
            # Check for existing
            existing = await db.knowledgebase.find_first(where={"title": title})
            if existing:
                continue

            # Add to DB
            kb_entry = await db.knowledgebase.create(
                data={
                    "title": title,
                    "content": content,
                    "category": "Public Health Stats",
                    "isActive": True
                }
            )
            
            # Prepare for Indexing
            chunks_to_index.append(
                KnowledgeChunk(
                    id=kb_entry.id,
                    title=kb_entry.title,
                    content=kb_entry.content,
                    category="Public Health Stats"
                )
            )
            count += 1

    print(f"✅ Imported {count} CDC health statistics.")

    # Index
    if chunks_to_index:
        print(f"🧠 Indexing {len(chunks_to_index)} statistics...")
        try:
            vector_store.add_documents(chunks_to_index)
            print("✅ Vector Index Updated!")
        except Exception as e:
            print(f"⚠️ Indexing failed: {e}")

    await db.disconnect()

if __name__ == "__main__":
    asyncio.run(import_cdc_data())
