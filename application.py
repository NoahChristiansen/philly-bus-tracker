from dash import Dash, html, Output, Input, dcc
import json
import dash_leaflet as dl
# import dash_leaflet.express as dlx
from dash_extensions.javascript import assign, arrow_function
import datetime as dt

from gtfs_tools import (
    check_static_updates,
    # transitview_to_df,
    get_bus_positions_from_transitview,
    # feed_to_dict,
    get_lines_json,
    # get_bus_lines,
    #  get_bus_positions,
    colors)

check_static_updates()

lines_df = get_lines_json('./data/all_bus_routes.json')

use_icon = assign("""function (feature, latlng) {
        return L.circleMarker(latlng, {
            radius: 8,
            weight: 1,
            color: feature.properties.color,
            fillColor: feature.properties.color,
            opacity: 1,
            fillOpacity: 1
            });
    }""")
lines_style = assign("""function (feature, context) {
        return {
            color : feature.properties.color,
            opacity : 0.7
        };
    }""")

app = Dash(__name__, prevent_initial_callbacks=True)

server = app.server
# app.scripts.config.serve_locally = True

app.layout = html.Div(children = [
    html.H2('Philadelphia Real Time Bus Tracker'),
    html.Div(children = [
    html.Div(children = [
        html.Div(children = [
            dcc.Dropdown(id = 'route_dropdown',
                    options = list(colors.keys()),
                    value = [],
                    placeholder = "Select a bus route", multi = True
                    )
            ])],
            style = {'flex':1, 'height':'50vh'}
    ),
    html.Div(
        children = [dl.Map(children = [
            dl.LayersControl(children = [
                dl.BaseLayer(children = [
                                dl.TileLayer(url='https://stamen-tiles-{s}.a.ssl.fastly.net/toner-lite/{z}/{x}/{y}{r}.png', minZoom=0, maxZoom=20),
                            ], name = 'Stamen Toner-Lite', checked = False),
                dl.BaseLayer(children = [
                    dl.TileLayer(url='https://stamen-tiles-{s}.a.ssl.fastly.net/toner/{z}/{x}/{y}{r}.png', minZoom=0, maxZoom=20),
                ], name = 'Stamen Toner', checked = False),
                dl.BaseLayer(children = [
                    dl.TileLayer(url='https://{s}.basemaps.cartocdn.com/light_all/{z}/{x}/{y}{r}.png', minZoom=0, maxZoom=20),
                ], name = 'Carto Light', checked = True),  
                dl.Overlay(dl.LayerGroup(dl.GeoJSON(
                    data = json.loads(lines_df.to_json(drop_id = True)),
                    id = 'lines-geojson',
                    zoomToBounds = True,
                    options = {'style': lines_style},
                    children = [dl.Popup(id = 'lines-popup')],
                    hoverStyle = arrow_function(dict(weight=5, color='#00ffcf', opacity = 0.8, dashArray='')))),
                    id = 'lines', name = 'bus-lines', checked = True),
                dl.Overlay(dl.LayerGroup(dl.GeoJSON(
                    data = get_bus_positions_from_transitview(),
                    options=dict(pointToLayer=use_icon),
                    cluster = True,
                    superClusterOptions={"radius": 100, "minPoints":7}, zoomToBoundsOnClick=True,
                    children = [dl.Tooltip(id = 'tooltip', opacity = 0.9)], id = 'geojson')),
                    id = 'points', name = 'bus-points', checked = True)
            ])
        ],
        center=(39.92, -75.15),
        zoom = 13
        )],
        style={'flex': 4, 'height':'100vh'}
    ),
    dcc.Interval(id='interval1', interval= 30 * 1000, n_intervals=0)
    ],
     style={'display': 'flex'}
)])

@app.callback(Output("lines-popup", "children"),
                     [Input("lines-geojson", "click_feature")])
def update_line_popup(feature):
    if feature is None:
        return None
    elif "route_id" in feature['properties']:
        return [
            html.P(html.B(f"Bus Line: {feature['properties']['route_id']}")),
            html.P(f"Line Name: {feature['properties']['route_name']}")
        ]
    else:
        return None

@app.callback(Output("tooltip", "children"),
                     [Input("geojson", "hover_feature")])
def update_vehicle_tooltip(feature):
    if feature is None:
        return None
    elif "route_id" in feature['properties']:
        return [
            html.P(html.B(f"Bus: {feature['properties']['route_id']}")),
            # html.P(f"Destination: {feature['properties']['trip_headsign']}")
            html.P(f"Destination: {feature['properties']['destination']}"),
            html.P(f"Direction: {feature['properties']['Direction']}"),
            html.P(f"Next Stop: {feature['properties']['next_stop_name']}"),
            html.P(f"Late: {feature['properties']['late']} minutes"),
            html.P(f"Estimated Seat Availability: {feature['properties']['estimated_seat_availability']}"),
            html.P(f"Time Since Last Update: {feature['properties']['Offset']} minutes, {feature['properties']['Offset_sec']} seconds"),
            html.P(f"Last Retrieved: {dt.datetime.fromtimestamp(feature['properties']['timestamp']).strftime('%I:%M:%S %p')}")
        ]
    else:
        return None

@app.callback(
    Output(component_id='lines-geojson', component_property= 'data'),
    Input('route_dropdown', "value"),
)
def update_bus_lines(
    value
    ):
    print("Updating route lines.")
    if len(value) > 0:
        return json.loads(lines_df.loc[lines_df['route_id'].isin(value), :].to_json(drop_id = True))
    else:
        return json.loads(lines_df.to_json(drop_id = True))

@app.callback(
    Output(component_id='geojson', component_property= 'data'),
    Input(component_id='interval1', component_property= 'n_intervals'),
    Input('route_dropdown', "value"),
    # Input(component_id='btn', component_property='n_clicks'),
)
def update_bus_interval(
    n_intervals,
    value
    # n_clicks
    ):
    print(f"Updating vehicle locations. ({dt.datetime.now().strftime('%I:%M:%S %p')})")
    if len(value) > 0:
        # return get_bus_positions(route_ids = value)
        return get_bus_positions_from_transitview(route_ids = value)
    else:
        # return get_bus_positions()
        return get_bus_positions_from_transitview()


if __name__ == '__main__':
    app.run_server(host = "0.0.0.0", port = 8050)