#!/usr/bin/env python3
import httpx, xml.etree.ElementTree as ET, sys, json
GROCERY_KW = ['food','beverage','snack','coffee','milk','rice','noodle','oil','sauce','cooking','cereal','water','juice','chocolate','bread','pasta','tea','soap','shampoo','toothpaste','detergent','diaper','pet']
def discover():
    r = httpx.get('https://www.lazada.co.th/sitemap-products-order-last-30days-morethan0.xml', timeout=15)
    root = ET.fromstring(r.text)
    ns = {'sm': 'http://www.sitemaps.org/schemas/sitemap/0.9'}
    locs = [loc.text for loc in root.findall('.//sm:loc', ns)]
    print(f'Found {len(locs)} sub-sitemaps')
    grocery_urls = []
    for i, loc in enumerate(locs[:5]):
        print(f'Processing {i+1}/{min(5,len(locs))}: {loc}')
        r2 = httpx.get(loc, timeout=15)
        sroot = ET.fromstring(r2.text)
        for url_elem in sroot.findall('.//sm:url', ns):
            loc_el = url_elem.find('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')
            if loc_el is not None and loc_el.text and any(kw in loc_el.text.lower() for kw in GROCERY_KW):
                grocery_urls.append(loc_el.text)
    with open('lazada_th_grocery_urls.jsonl', 'w') as f:
        for url in grocery_urls:
            f.write(json.dumps({'url': url}) + chr(10))
    print(f'Found {len(grocery_urls)} grocery URLs, saved')
if __name__ == '__main__':
    discover()
