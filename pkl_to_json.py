import pickle
import json

# Read the pickle file
with open('lessness/azure_result.pkl', 'rb') as f:
    result = pickle.load(f)

# Convert to JSON-friendly format
text_content = {
    'pages': []
}

# Extract text content from each page
for page in result.pages:
    page_content = {
        'page_number': page.page_number,
        'lines': [line.content for line in page.lines],
        'text': ' '.join(line.content for line in page.lines)
    }
    text_content['pages'].append(page_content)

# Save as JSON
with open('lessness/azure_result.json', 'w', encoding='utf-8') as f:
    json.dump(text_content, f, indent=2, ensure_ascii=False)

print("Conversion complete. Data saved to lessness/azure_result.json")