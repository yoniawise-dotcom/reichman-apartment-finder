from manual import parse_manual
from scoring import enrich

row = parse_manual('5 rooms 120 sqm ₪9000 renovated balcony mamad parking https://example.com/a')[0]
assert row['bedrooms'] == 4
assert row['price_per_bedroom'] == 2250
assert row['renovated'] == 1 and row['mamad'] == 1
assert row['score'] >= 90
print('smoke test passed')
from yad2_client import parse_yad2_markdown
sample = '''## Yad2 Rental Results
Found 1 listings

### Nice place
**Price:** ₪9,200/month
**Details:** 5 rooms · 120m² · floor 2
**Address:** HaNadiv 1
**Description:** renovated balcony parking
**Token:** abc
**URL:** https://www.yad2.co.il/item/abc
**Listed:** today
'''
y = parse_yad2_markdown(sample)[0]
assert y['bedrooms'] == 4 and y['price_per_bedroom'] == 2300 and y['renovated'] == 1
print('yad2 parser test passed')
