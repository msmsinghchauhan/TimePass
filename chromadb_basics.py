import chromadb
from docx import Document


directory_location = "/Users/sinm/Library/CloudStorage/OneDrive-NetAppInc/Desktop/Mukesh/TimePass"
collection_name = "TongaPlusSpecVectorDB"

def create_collection(path=directory_location,collection_name=collection_name):
    client = chromadb.PersistentClient(path=path)
    collection = client.get_or_create_collection(collection_name)
    return collection

def delete_collection(collection=collection_name):
    all_docs = collection.peek(limit=1000)
    all_ids = all_docs["ids"]
    if all_ids:
        collection.delete(ids=all_ids)
    return

                            # Example 1
                            
collection = create_collection(path=directory_location,collection_name=collection_name)
collection.add(ids=["id1"], documents=["TongaPlusSpec"])
results = collection.query(query_texts=["PCIe"], n_results=100)
print(results["documents"])
# Get all documents in the collection
all_docs=collection.peek(limit=1000)
print(all_docs["documents"])
delete_collection(collection=collection)
all_docs=collection.peek(limit=1000)
print(all_docs["documents"])

                            # Example 2

# Read word document and build database
doc = Document("/Users/sinm/Library/CloudStorage/OneDrive-NetAppInc/Desktop/Mukesh/TimePass/TongaPlusSpec.docx")
collection = create_collection(path=directory_location,collection_name=collection_name)
i=1
for para in doc.paragraphs:
    if para.text.strip():
        # collection.add(ids=[para.text.strip()], documents=[para.text.strip()])
        collection.add(ids=[f"ID_{i}"], documents=[para.text.strip()])
        i += 1

results = collection.query(query_texts=["roce"], n_results=1)
print(results)
#print(results["ids"])       # IDs of the matching documents
#print(results["documents"])

# Get all documents in the collection
#all_docs=collection.peek(limit=1000)
#print(all_docs["documents"])
#print(all_docs["ids"])


