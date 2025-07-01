import requests
import json
import geopandas as gpd
import sys

def download_geojson(api_url, output_filename, expected_keys=None, required_fields=None):
    response = requests.get(api_url)
    if response.status_code == 200:
        data = response.json()

        # Basic structure check
        if expected_keys:
            for key in expected_keys:
                if key not in data:
                    raise ValueError(f"Key '{key}' not found in dataset {output_filename}. Structure may have changed.")
            print(f"All expected keys found in {output_filename}.")

        # Check for features
        if 'features' not in data or len(data['features']) < 1:
            raise ValueError(f"No features found in dataset {output_filename}. Data may be empty or structure changed.")

        # Check schema fields
        if required_fields:
            sample_properties = data['features'][0]['properties']
            for field in required_fields:
                if field not in sample_properties:
                    raise ValueError(f"Field '{field}' missing in {output_filename} properties schema.")

        # Save the data
        with open(output_filename, "w") as f:
            json.dump(data, f, indent=2)
        print(f"Data successfully retrieved and saved to {output_filename}.")

    else:
        raise ConnectionError(f"Failed to retrieve data from {api_url}. Status code: {response.status_code}")

def process_transit_data():
    # Download California transit routes GeoJSON
    transit_url = "https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHrailroad/CA_Transit_Routes/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson"
    download_geojson(
        transit_url,
        "california_transit_routes.geojson",
        expected_keys=['type', 'features']                   #CAN CHANGE!!!!!
    )

    # Load transit data
    ca_transit = gpd.read_file("california_transit_routes.geojson")

    # Download California county boundaries GeoJSON
    boundaries_url = "https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services/California_County_Boundaries/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson"
    download_geojson(
        boundaries_url,
        "all_ca_boundaries.geojson",
        expected_keys=['type', 'features'],
        required_fields=['COUNTY_NAME', 'ISLAND']
    )

    # Load boundaries and filter to LA County excluding Channel Islands
    boundaries = gpd.read_file("all_ca_boundaries.geojson")
    la_boundary = boundaries[(boundaries["COUNTY_NAME"] == "Los Angeles") & (boundaries["ISLAND"].isnull())]

    # Reproject transit data to match LA boundary CRS
    ca_transit = ca_transit.to_crs(la_boundary.crs)

    # Get LA County geometry
    la_geom = la_boundary.geometry.iloc[0]

    # Clip transit lines to LA County boundary
    transit_clipped = gpd.clip(ca_transit, la_geom)
    transit_clipped.to_file("transit_clipped_to_la.geojson", driver="GeoJSON")
    print("Clipped transit data saved as transit_clipped_to_la.geojson.")

    # Convert geometry to WKT and save as CSV
    transit_clipped["geometry"] = transit_clipped["geometry"].apply(lambda geom: geom.wkt)
    transit_clipped.to_csv("transit_final_clipped.csv", index=False)
    print("Final clipped transit data saved as transit_final_clipped.csv.")

def main(argv):
    if len(argv) == 0:
        process_transit_data()
    else:
        print("No command-line options implemented yet.")

if __name__ == "__main__":
    main(sys.argv[1:])
