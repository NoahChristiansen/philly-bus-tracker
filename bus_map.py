#!/usr/bin/env/ python
import numpy as np
import geopandas as gpd
import folium
from folium.plugins import MarkerCluster, FastMarkerCluster
import datetime

# from google.transit import gtfs_realtime_pb2
# from google.protobuf.json_format import MessageToDict
import requests
import pandas as pd
import os
import shutil
from zipfile import ZipFile
import sys
import json

import psycopg2
from matplotlib import cm
from matplotlib.colors import rgb2hex

from shapely.geometry import Point, LineString, MultiLineString
from shapely import ops

with open('credentials.json', 'r') as f:
    creds = json.load(f)

with open('./data/route_colors.json', 'r') as f:
    colors = json.load(f)

## GTFS Data from https://www3.septa.org/#/

url_dict = dict(
    bus_alerts = 'https://www3.septa.org/gtfsrt/septa-pa-us/Service/rtServiceAlerts.pb',
    bus_trip_updates = 'https://www3.septa.org/gtfsrt/septa-pa-us/Trip/rtTripUpdates.pb',
    bus_vehicle_position_updates = 'https://www3.septa.org/gtfsrt/septa-pa-us/Vehicle/rtVehiclePosition.pb',
    regional_rail_alerts = 'https://www3.septa.org/gtfsrt/septarail-pa-us/Service/rtServiceAlerts.pb',
    regional_rail_trip_updates = 'https://www3.septa.org/gtfsrt/septarail-pa-us/Trip/rtTripUpdates.pb',
    regional_rail_vehicle_position_updates = 'https://www3.septa.org/gtfsrt/septarail-pa-us/Vehicle/rtVehiclePosition.pb'
)

def create_route_color_json(color_map = "Spectral"):
    with psycopg2.connect(**creds) as connection:
            connection.autocommit = True
            with connection.cursor() as cursor:
                cursor.execute(f"""
                        SELECT DISTINCT route_id
                        FROM routes
                    """)
                column_names = [d[0] for d in cursor.description]
                routes = gpd.GeoDataFrame(cursor.fetchall(), columns = column_names)
    str_list = []
    num_list = []
    for id in routes['route_id']:
        try:
            num_list.append(int(id))
        except:
            str_list.append(id)

    routes_list = sorted(num_list) + sorted(str_list)

    cmap = cm.get_cmap(color_map,len(routes_list))
    hex_colors = [rgb2hex(rgb) for rgb in cmap(np.arange(1,len(routes_list),1))]

    color_dict = {str(i):c for i,c in zip(routes_list,hex_colors)}

    with open("./data/route_colors.json", 'w') as f:
        json.dump(color_dict, f)

def feed_to_dict(endpoint = "bus_vehicle_position_updates"):
    url = url_dict[endpoint]
    feed = gtfs_realtime_pb2.FeedMessage()
    response = requests.get(url)
    feed.ParseFromString(response.content)
    feed_dict = MessageToDict(feed)

    row_list = []
    for entity in feed_dict['entity']:
        row = {
            'id' : entity['id'],
            'trip_id' : entity['vehicle'].get('trip',dict()).get("tripId",""),
            'route_id' : entity['vehicle'].get('trip',dict()).get("routeId",""),
            # 'start_date' : entity['vehicle'].get('trip',dict()).get("startDate",""),
            'latitude' : entity['vehicle']['position'].get("latitude",""),
            'longitude' : entity['vehicle']['position'].get("longitude",""),
            # 'bearing' : entity['vehicle']['position'].get("bearing",""),
            'speed' : entity['vehicle']['position'].get("speed",""),
            'current_stop_seq' : entity['vehicle'].get('currentStopSequence',""),
            # 'current_status' : entity['vehicle'].get('currentStatus',""),
            # 'timestamp' : entity['vehicle'].get('timestamp',""),
            'stop_id' : entity['vehicle'].get('stopId',"")
        }
        row_list.append(row)

    df = gpd.GeoDataFrame(row_list)
    # df['datetime'] = df['timestamp'].apply(lambda row: dt.fromtimestamp(int(row)))
    df['geometry'] = df[['longitude', 'latitude']].apply(Point, axis = 1)
    # df['geometry'] = [Point(lon,lat) for lat,lon in  zip(df['latitude'], df['longitude'])]
    df['speed'] = df['speed'].replace('',0).astype(float)
    df = df.set_crs('epsg:4326')
    
    return df.loc[df['route_id']!='']

def create_gtfs_database(schema_file = 'create_gtfs_db.sql', credentials_path = 'credentials.json', gtfs_filepath = './google_bus/'):
    ## Get database credentials
    with open(credentials_path, 'r') as f:
        creds = json.load(f)

    ## Read list of gtfs static files and load into database tables
    file_list = os.listdir(gtfs_filepath)
    file_list.remove('fare_rules.txt')
    file_list.remove('fare_attributes.txt')

    ## Read schema file, and execute to create database tables
    with psycopg2.connect(**creds) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            with open(schema_file, 'r') as f:
                schema = f.read()
            cursor.execute(schema)
            print("Created GTFS database tables.")

            ## Load gtfs static files into database tables
            for file in file_list:
                with open(f"{gtfs_filepath}{file}", 'r') as f:
                    next(f) ## skips header row
                    cursor.copy_from(f, file.replace(".txt",""), sep = ',')
            print("All files have been loaded in database.")

def get_bus_lines(route_ids = 'all', filename = './data/all_bus_lines.geojson'):
    # if route_ids == 'all':
    #     route_ids = [i for i in feed_to_dict()['route_id'].unique()]

    print("Getting line information ...")
    with psycopg2.connect(**creds) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT s.*, t.route_id, r.route_long_name
                FROM shapes AS s
                LEFT JOIN trips AS t ON t.shape_id = s.shape_id
                LEFT JOIN routes AS r ON r.route_id = t.route_id
                GROUP BY s.shape_id, shape_pt_lat, shape_pt_lon, 
                shape_pt_sequence, t.route_id, r.route_long_name
            """)
            # WHERE r.route_id IN {(route_ids,'') if type(route_ids)==str else tuple(list(i for i in route_ids)+[''])}

            column_names = [d[0] for d in cursor.description]
            shapes = gpd.GeoDataFrame(cursor.fetchall(), columns = column_names)
            shapes['geometry'] = shapes[["shape_pt_lon","shape_pt_lat"]].apply(Point, axis = 1)

    print(f"Shapes acquired. Shapes shape: {shapes.shape}")

    line_list = []
    print(len(shapes['shape_id'].unique()))
    for i,shape_id in enumerate(shapes['shape_id'].unique()):
        line = shapes.loc[shapes['shape_id'] == shape_id,:].sort_values('shape_pt_sequence')

        if i % 50 == 0:
            print(f"Shape {i}")

        line_dict = {
            'shape_id' : shape_id,
            'route_id' : line['route_id'].unique()[0],
            'route_name' : line['route_long_name'].unique()[0],
            'geometry' : LineString(line['geometry'])
        }
        line_list.append(line_dict)

    line_df = gpd.GeoDataFrame(line_list)

    route_list = []
    for routeid in line_df['route_id'].dropna().unique():
        route_dict = {
            "route_id" : routeid,
            "route_name" :  line_df.loc[line_df['route_id'] == routeid, 'route_name'].iloc[0],
            "geometry" : ops.linemerge(MultiLineString(line_df.loc[line_df['route_id'] == routeid,"geometry"].values))
        }
        route_list.append(route_dict)

    line_df = gpd.GeoDataFrame(route_list)
    print('Making geometry column')
    line_df['geometry'] = [g['geometry'] for g in route_list]
    line_df = line_df.set_crs('epsg:4326')
    line_df['color'] = line_df['route_id'].map(colors)
    print(f"Line_df shape: {line_df.shape}")
    print(f"Saving geojson to {filename}")
    line_df.to_file(filename, driver = "GeoJSON")
    print(f"{filename} has been saved.")
    return line_df

def get_lines_json(filename = './data/all_bus_lines.geojson', force_download = False):
    if (not os.path.exists(filename)) or (force_download):
        print(f"Downloading lines data ...")
        lines = get_bus_lines(filename=filename)
    else:
        lines = gpd.read_file(filename)
    # lines_json = json.loads(lines.to_json(drop_id = True))
    return lines

def get_bus_positions(route_ids = 'all'):
    print("Getting current bus locations ...")
    feed_df = feed_to_dict()
    if route_ids == 'all':
        route_ids = feed_df['route_id'].unique()
    if type(route_ids) in (str, int):
        route_ids = str(route_ids)
        df = feed_df.loc[feed_df['route_id'] == route_ids]
    else:
        route_ids = [str(id) for id in route_ids]
        df = feed_df.loc[feed_df['route_id'].isin(route_ids)]

    with psycopg2.connect(**creds) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(f"""
                SELECT t.trip_id, t.direction_id,
                    t.trip_headsign, r.route_long_name
                FROM trips AS t
                JOIN routes AS r ON r.route_id = t.route_id
                WHERE t.route_id IN {(route_ids,'') if type(route_ids)==str else tuple(list(i for i in route_ids)+[''])}
            """)
            column_names = [d[0] for d in cursor.description]
            trips_routes = gpd.GeoDataFrame(cursor.fetchall(),columns = column_names)

    routes_df = pd.merge(df,trips_routes, on = "trip_id", how = "left",suffixes=(None,'_'))
    routes_df = routes_df.loc[routes_df['route_id']!='']
    routes_df['color'] = routes_df['route_id'].map(colors)

    return json.loads(routes_df.to_json(drop_id = True))

def transitview_to_df(url = "https://www3.septa.org/api/TransitViewAll/index.php"):
    response = requests.get(url)
    res_dict = response.json()

    row_list = []
    for route in res_dict['routes'][0]:
        for vehicle in res_dict['routes'][0][route]:
            vehicle['route_id'] = route
            row_list.append(vehicle)

    df = gpd.GeoDataFrame(row_list)
    df['geometry'] = df[['lng', 'lat']].astype(float).apply(Point, axis = 1)
    df.drop(columns = ['lat','lng','label'], inplace = True)
    df['color'] = df['route_id'].map(colors)
    return df.loc[df['route_id']!='']

def get_bus_positions_from_transitview(route_ids = 'all'):
    print("Getting current bus locations ...")
    feed_df = transitview_to_df()
    if route_ids == 'all':
        route_ids = feed_df['route_id'].unique()
        df = feed_df
    elif type(route_ids) in (str, int):
        route_ids = str(route_ids)
        df = feed_df.loc[feed_df['route_id'] == route_ids]
    else:
        route_ids = [str(id) for id in route_ids]
        df = feed_df.loc[feed_df['route_id'].isin(route_ids)]

    return json.loads(df.to_json(drop_id = True))

def check_static_updates():
    url = "https://api.github.com/repos/septadev/GTFS/releases/latest"
    res = requests.get("https://api.github.com/repos/septadev/GTFS/releases/latest")
    res_json = res.json()
    download_url = res_json['assets'][0]['browser_download_url']

    with open("./data/latest_static_update.json", 'r') as j:
        data = json.load(j)
    
    if download_url != data['lastUpdateURL']:
        print("Static Data is out of date. Updating static data files now.")
        response = requests.get(download_url, stream=True)
        with open("gtfs_public.zip", 'wb') as file:
            for chunk in response.iter_content(chunk_size=512):
                file.write(chunk)

        with ZipFile("./gtfs_public.zip", "r") as zip_folder:
            zip_folder.extractall(path = './')

        with ZipFile("./google_bus.zip", 'r') as bus_folder:
            bus_folder.extractall(path = "./google_bus/")

        with ZipFile("./google_rail.zip", 'r') as rail_folder:
            rail_folder.extractall(path = "./google_rail/")

        os.remove("./gtfs_public.zip")
        os.remove("./google_bus.zip")
        os.remove("./google_rail.zip")

        with open("./data/latest_static_update.json", 'w') as j:
            json.dump({
                'lastUpdateURL':download_url
            }, j)

        create_gtfs_database()
        get_bus_lines()
        create_route_color_json()
        
        shutil.rmtree('./google_bus/')
        shutil.rmtree('./google_rail/')
    else:
        print("Static data is up-to-date.")

#######################################
### OLDER FUNCTIONS (TO BE DELETED) ###
#######################################

def get_combined_route_data(route_ids = 'all'):
    feed_df = feed_to_dict()
    if route_ids == 'all':
        route_ids = feed_df['route_id'].unique()
    if type(route_ids) in (str, int):
        route_ids = str(route_ids)
        df = feed_df.loc[feed_df['route_id'] == route_ids]
    else:
        route_ids = [str(id) for id in route_ids]
        df = feed_df.loc[feed_df['route_id'].isin(route_ids)]

    with psycopg2.connect(**creds) as connection:
        connection.autocommit = True
        with connection.cursor() as cursor:
            cursor.execute(f"""
                    SELECT t.*, r.route_long_name
                    FROM trips AS t
                    JOIN routes AS r ON r.route_id = t.route_id
                    WHERE t.route_id IN {(route_ids,'') if type(route_ids)==str else tuple(list(i for i in route_ids)+[''])}
                """)
            column_names = [d[0] for d in cursor.description]
            trips_routes = gpd.GeoDataFrame(cursor.fetchall(),columns = column_names)

            shape_ids = trips_routes['shape_id'].unique()

            cursor.execute(f"""
                    SELECT s.*, r.route_id, r.route_long_name
                    FROM shapes AS s
                    JOIN trips AS t ON t.shape_id = s.shape_id
                    JOIN routes AS r ON r.route_id = t.route_id
                    WHERE s.shape_id IN {tuple(shape_ids)}
                """)

            column_names = [d[0] for d in cursor.description]
            shapes = gpd.GeoDataFrame(cursor.fetchall(),columns = column_names)

    line_list = []
    for shape_id in shapes['shape_id'].unique():
        line = shapes.loc[shapes['shape_id'] == shape_id,:].sort_values('shape_pt_sequence')

        line_dict = {
            'shape_id' : shape_id,
            'route_id' : line['route_id'].unique()[0],
            'route_name' : line['route_long_name'].unique()[0],
            'geometry' : LineString(line[["shape_pt_lon","shape_pt_lat"]].apply(Point, axis = 1))
        }
        line_list.append(line_dict)

    line_df = gpd.GeoDataFrame(line_list, geometry='geometry')
    line_df = line_df.set_crs('epsg:4326')

    routes_df = pd.merge(df,trips_routes, on = "trip_id", how = "left",suffixes=(None,'_'))
    routes_df = routes_df.loc[routes_df['route_id']!='',list(df.columns)+["trip_headsign"]]

    return line_df, routes_df

def generate_route_map(route_lines, route_points, filename = 'output'):
# ## Folium Map
    # m = line_df.loc[:,['geometry']].explore(
    #  style_kwds = {'opacity':0.75, 'weight':2},
    #  name="bus lines",
    #  zoom_start = 10 if len(route_ids) > 6 else 13
    # )

    # routes_df.drop(columns = ['datetime']).explore(
    #     m=m,
    #     color = 'grey',
    #     marker_kwds=dict(radius=4, fill=True),
    #     style_kwds=dict(
    #         fillOpacity=0.75, weight = 3,
    #         style_function = lambda bus:
    #          {"color":'red', "fillColor":"red"} if bus['properties']['speed'] <= 2 else {"color":"green", 'fillColor':'green'}),
    #     tooltip=["route_id","route_long_name","trip_headsign","current_status","current_stop_seq"],
    #     tooltip_kwds=dict(labels=True),
    #     name="buses"
    # )

    # folium.TileLayer('CartoDB positron', control=True).add_to(m)
    # folium.LayerControl().add_to(m)

    m = folium.Map(location = [39.938161, -75.161364], tiles = 'CartoDB positron', zoom_start = 13)

    route_lines.loc[:,['geometry']].explore(
        m = m,
        style_kwds = {'opacity':0.75, 'weight':2},
        name="bus lines", # name of the layer in the map,
        zoom_start = 10
    )

    marker_cluster = MarkerCluster(name = 'bus clusters').add_to(m)

    for i in route_points.index:
        
        html = f"""
        Route: {route_points.loc[i,'route_id']}<br>
        Route Name: {route_points.loc[i,'route_long_name']}<br>
        Current Status: {route_points.loc[i,'current_status']}
        """
        tooltip = folium.Tooltip(html)
        marker = folium.Marker(route_points.loc[i,['latitude','longitude']], tooltip = tooltip, icon = folium.Icon(color = 'orange', icon = 'bus', prefix = 'fa'))
        marker_cluster.add_child(marker)

    folium.TileLayer('CartoDB positron', control=True).add_to(m)
    folium.LayerControl().add_to(m)

    m.save(f"{filename}.html")

    return m

def main():
    arg_dict = dict(pair.split("=") for pair in sys.argv[1:])
    if len(arg_dict) == 0:
        generate_route_map(*get_combined_route_data())
    else:
        generate_route_map(*get_combined_route_data(**arg_dict))
    return os.system(f"start ./output.html")

if __name__ == "__main__":
    main()