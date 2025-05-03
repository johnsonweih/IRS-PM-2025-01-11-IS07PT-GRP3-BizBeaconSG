import json
import csv
from bs4 import BeautifulSoup

def extract_bounds(geojson_file):
    with open(geojson_file, 'r') as f:
        data = json.load(f)

    results = []

    for feature in data['features']:
        properties = feature['properties']
        description_html = properties.get('Description', '')

        # Parse HTML content inside the Description field
        soup = BeautifulSoup(description_html, 'html.parser')
        table_data = {}

        for row in soup.find_all('tr'):
            cells = row.find_all(['th', 'td'])
            if len(cells) == 2:
                key = cells[0].get_text(strip=True)
                value = cells[1].get_text(strip=True)
                table_data[key] = value

        subzone = table_data.get('SUBZONE_N')
        planning_area = table_data.get('PLN_AREA_N')
        region = table_data.get('REGION_N')

        geometry = feature['geometry']
        coords = []
        full_coords = None  # This will hold the original structure for saving
        gtype = geometry['type']
        if gtype == 'Polygon':
            full_coords = geometry['coordinates']
            for ring in full_coords:
                coords.extend(ring)
        elif gtype == 'MultiPolygon':
            full_coords = geometry['coordinates']
            for polygon in full_coords:
                for ring in polygon:
                    coords.extend(ring)
        else:
            continue

        longitudes = [coord[0] for coord in coords]
        latitudes = [coord[1] for coord in coords]

        result = {
            'subzone': subzone,
            'planning_area': planning_area,
            'region': region,
            'min_longitude': min(longitudes),
            'max_longitude': max(longitudes),
            'min_latitude': min(latitudes),
            'max_latitude': max(latitudes),
            'geometry_type' : gtype,
            'coordinates': json.dumps(full_coords)  # Convert list to JSON string
        }

        results.append(result)

    # Save results to a CSV file
    csv_file = "planning_areas_with_coords.csv"
    with open(csv_file, mode='w', newline='', encoding='utf-8') as f:
        fieldnames = ['subzone', 'planning_area', 'region', 'min_longitude', 'max_longitude', 'min_latitude', 'max_latitude', 'geometry_type', 'coordinates']
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)

    print(f"Done! Saved {len(results)} records to {csv_file}.")

extract_bounds("subzone_boundaries.geojson")
