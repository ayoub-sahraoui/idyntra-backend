import requests
import json

API_BASE_URL = "https://api.idyntra.space"
API_KEY = "api_1d7b6f4e8c404c0fb2e6b1aa90122379"

# Test clean_cropped_id
id_path = "docs/clean_cropped_id/id.jpg"
selfie_path = "docs/clean_cropped_id/selfie.jpg"

print("🔍 Testing clean_cropped_id...")
print(f"   ID: {id_path}")
print(f"   Selfie: {selfie_path}")
print()

files = {
    'id_document': ('id.jpg', open(id_path, 'rb'), 'image/jpeg'),
    'selfie': ('selfie.jpg', open(selfie_path, 'rb'), 'image/jpeg')
}

headers = {
    'X-API-Key': API_KEY
}

response = requests.post(
    f"{API_BASE_URL}/api/v1/verify",
    files=files,
    headers=headers,
    timeout=60
)

for file_tuple in files.values():
    file_tuple[1].close()

if response.status_code == 200:
    result = response.json()
    print("="*80)
    print("📊 RESPONSE")
    print("="*80)
    print(json.dumps(result, indent=2))
    
    # Check if document_structure is in the response
    if 'document_structure' in result:
        print("\n" + "="*80)
        print("🔍 DOCUMENT STRUCTURE DETAILS")
        print("="*80)
        doc_struct = result['document_structure']
        print(json.dumps(doc_struct, indent=2))
else:
    print(f"❌ Request failed: HTTP {response.status_code}")
    print(response.text)
