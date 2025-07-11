import requests
import json
import geopandas as gpd
import sys

def download_and_save_geojson(url, output_filename, expected_keys=None):
    response = requests.get(url)
    if response.status_code == 200:
        data = response.json()

        # Check for expected keys
        if expected_keys:
            for key in expected_keys:
                if key not in data:
                    print(f"WARNING: Expected key '{key}' missing in response for {url}. The dataset structure may have changed.")

        # Check for 'features' and non-empty data
        if 'features' not in data or not data['features']:
            print(f"WARNING: No 'features' found or features list is empty in {url}. The dataset may be empty, moved, or deleted.")
        else:
            with open(output_filename, "w") as f:
                json.dump(data, f, indent=2)
            print(f"Data from {url} saved as {output_filename}.")
    else:
        print(f"ERROR: Failed to retrieve data from {url}. Status code: {response.status_code}")

def process_transit_and_stops():
    # Download transit routes
    transit_url = "https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHrailroad/CA_Transit_Routes/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson"
    download_and_save_geojson(transit_url, "california_transit_routes.geojson", expected_keys=['type', 'features'])
    ca_transit = gpd.read_file("california_transit_routes.geojson")

    # Download transit stops
    stops_url = "https://caltrans-gis.dot.ca.gov/arcgis/rest/services/CHrailroad/CA_Transit_Stops/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson"
    download_and_save_geojson(stops_url, "california_transit_stops.geojson", expected_keys=['type', 'features'])
    ca_stops = gpd.read_file("california_transit_stops.geojson")

    # Download LA County boundary
    boundary_url = "https://services1.arcgis.com/jUJYIo9tSA7EHvfZ/arcgis/rest/services/California_County_Boundaries/FeatureServer/0/query?outFields=*&where=1%3D1&f=geojson"
    download_and_save_geojson(boundary_url, "all_ca_boundaries.geojson", expected_keys=['type', 'features'])
    boundaries = gpd.read_file("all_ca_boundaries.geojson")
    la_boundary = boundaries[(boundaries["COUNTY_NAME"] == "Los Angeles") & (boundaries["ISLAND"].isnull())]

    # Reproject to match LA CRS
    ca_transit = ca_transit.to_crs(la_boundary.crs)
    ca_stops = ca_stops.to_crs(la_boundary.crs)

    la_geom = la_boundary.geometry.iloc[0]

    # Clip and save transit routes
    transit_clipped = gpd.clip(ca_transit, la_geom)
    transit_clipped.to_file("transit_clipped_to_la.geojson", driver="GeoJSON")
    print("Clipped transit routes saved as transit_clipped_to_la.geojson.")

    # Clip and save transit stops
    stops_clipped = gpd.clip(ca_stops, la_geom)
    stops_clipped.to_file("transit_stops_clipped_to_la.geojson", driver="GeoJSON")
    print("Clipped transit stops saved as transit_stops_clipped_to_la.geojson.")

    # Save transit routes as WKT CSV
    transit_clipped["geometry"] = transit_clipped["geometry"].apply(lambda geom: geom.wkt)
    transit_clipped.to_csv("transit_final_clipped.csv", index=False)
    print("Transit routes saved as transit_final_clipped.csv.")

    # Save transit stops as WKT CSV
    stops_clipped["geometry"] = stops_clipped["geometry"].apply(lambda geom: geom.wkt)
    stops_clipped.to_csv("transit_stops_final_clipped.csv", index=False)
    print("Transit stops saved as transit_stops_final_clipped.csv.")

def main(argv):
    if len(argv) == 0:
        process_transit_and_stops()
    else:
        print("No command-line options implemented yet.")

if __name__ == "__main__":
    main(sys.argv[1:])
