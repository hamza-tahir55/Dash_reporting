"""
Quick test to verify the AI extracts value and label fields correctly.
"""
from api import FinancialTSXGenerator

# Sample financial text
financial_text = """
Income Analysis:
Income peaked in December 2020 at $155,815. The latest value in September 2024 is $5,200, 
showing a decline from August 2024 which was $9,384.

Gross Profit:
Gross Profit in September 2024 was $5,097, down from $9,374 in August 2024.
The peak was $101,828 in December 2020.
"""

print("=" * 80)
print("Testing AI Data Extraction")
print("=" * 80)

generator = FinancialTSXGenerator()
result = generator.generate_financial_slides(financial_text)

print("\n" + "=" * 80)
print("Checking if 'value' and 'label' fields are present:")
print("=" * 80)

for metric in result.get('metrics', []):
    name = metric.get('name', 'Unknown')
    value = metric.get('value', None)
    label = metric.get('label', None)
    
    print(f"\n✓ Metric: {name}")
    if value and value != 'N/A':
        print(f"  ✅ Value: {value}")
    else:
        print(f"  ❌ Value: MISSING or N/A")
    
    if label:
        print(f"  ✅ Label: {label}")
    else:
        print(f"  ❌ Label: MISSING")

print("\n" + "=" * 80)
print("Test Complete")
print("=" * 80)
