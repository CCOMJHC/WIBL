import time
from dash import Dash, dcc, html
import dash
import os
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import httpx
import asyncio
from viewflow.contrib.plotly import Dashboard, material


app = Dashboard(
    app_name="dashboard",
    title='Current Status',
    icon="public",
    layout=material.PageGrid([
        html.Div([
            # interval dropdown
            html.Div([
                html.Label("Update Interval"),
                dcc.Dropdown(
                    id='interval-dropdown',
                    options=[
                        {'label': '5 seconds', 'value': 5000},
                        {'label': '30 seconds', 'value': 30000},
                        {'label': '1 minute', 'value': 60000},
                        {'label': '5 minutes', 'value': 300000},
                    ],
                    value=60000
                )
            ], className="box"),

            # Countdown
            html.Div([
                html.Div(id="countdown-display"),
                dcc.Interval(id='countdown-tick', interval=1000, n_intervals=0),
                html.Div(id='update-output'),
            ]),

        ], className="columns"),

        html.Div([
            # upload number, submission graph, location graph
            html.Div([
                dcc.Graph(id="upload-Number"),
                dcc.Graph(id="submission-Graph"),
                dcc.Graph(id="location-Graph")
            ], className='column'),

            # converted, validated, submitted gauges
            html.Div([
                dcc.Graph(id="converted-Gauge"),
                dcc.Graph(id="validated-Gauge"),
                dcc.Graph(id="submitted-Gauge")
            ], className='column'),

            # Third column with WIBL Files and Observers boxes
            html.Div([
                html.Div([
                    html.Legend('WIBL Files'),
                    html.Div([
                        dcc.Graph(id="total-Size-Number"),
                        dcc.Graph(id="total-Obs-Number"),
                        dcc.Graph(id="obs-Used-Gauge")
                    ])
                ], className="box"),

                html.Div([
                    html.Legend('Observers'),
                    html.Div([
                        html.Div([
                            dcc.Graph(id="total-Observers-Number"),
                            dcc.Graph(id="no-Reports-Number")
                        ]),
                        html.Div([
                            dcc.Graph(id="observer-File-Count-Graph"),
                            dcc.Graph(id="observer-Snd-Count-Graph")
                        ])
                    ])
                ], className="box")
            ], className='column')
        ], className="columns")
    ])
)


async def getData():
    manager_url: str = os.environ.get('MANAGEMENT_URL', "http://manager:5000")

    client = httpx.AsyncClient()
    response = await client.get(manager_url + "/statistics")
    if response.status_code == 200:
        return response.json()
    else:
        return None


async def loadData():
    manager_res = await getData()
    if not manager_res:
        return

    file_date_df = pd.DataFrame(manager_res['FileDateTotal'])
    observer_file_total_df = pd.DataFrame(manager_res['ObserverFileTotal'])
    wibl_file_count = manager_res['WIBLFileCount']
    geojson_file_count = manager_res['GeoJSONFileCount']
    converted_total = manager_res['ConvertedTotal']
    validated_total = manager_res['ValidatedTotal']
    submitted_total = manager_res['SubmittedTotal']
    size_total = manager_res['SizeTotal']
    observations_total = manager_res['ObservationsTotal']
    zero_reports_total = manager_res['ObserverZeroReportsTotal']
    observer_total = manager_res['ObserverTotal']

    location_geojson = manager_res['LocationData']
    example_location_data = [{'ST_AsGeoJSON':
                                  {"type": "Polygon", "coordinates": [
                                      [[-17.3335, -15.3985], [-17.3335, -20], [-25.3454, -20], [-25.3454, -15.3985],
                                       [-17.3335, -15.3985]]]}},
                             {'ST_AsGeoJSON':
                                  {"type": "Polygon",
                                   "coordinates": [
                                       [[30.3335, 14.3985], [30.3335, 5], [-25.3454, 5], [-25.3454, 14.3985],
                                        [30.3335, 14.3985]]]}},
                             {'ST_AsGeoJSON':
                                  {"type": "Polygon",
                                   "coordinates": [
                                       [[-12.3335, 120.3985], [-12.3335, 100], [-25.3454, 100], [-25.3454, 120.3985],
                                        [-12.3335, 120.3985]]]}},
                             {'ST_AsGeoJSON':
                                  {"type": "Polygon",
                                   "coordinates": [[[-110.3335, -110.3985], [-110.3335, -140], [-140.3454, -140],
                                                    [-140.3454, -110.3985], [-110.3335, -110.3985]]]}}]

    uploadNumber = go.Figure(go.Indicator(
        mode='number',
        value=wibl_file_count,
        title={'text': 'Uploaded'},
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'valueformat': '.0f'}
    ))

    newSubmissionGraph = px.line(file_date_df, x='date', y='submissions')
    newSubmissionGraph.update_layout(xaxis_title='Days', yaxis_title='Files Submitted')

    convertedGauge = go.Figure(go.Indicator(
        mode="gauge+number",
        value=(converted_total / wibl_file_count) * 100,
        title={'text': 'Converted'},
        number={'suffix': '%'},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={'axis': {'range': [None, 100], 'tick0': 0, 'dtick': 20}}
    ))

    newLocationGraph = px.scatter_geo(emptyLocationDf, lon='longitude', lat='latitude', projection='natural earth')
    newLocationGraph.update_layout(margin=dict(l=0, r=0, t=0, b=0))

    validatedGauge = go.Figure(go.Indicator(
        mode='gauge+number',
        value=(validated_total / geojson_file_count) * 100,
        title={'text': 'Validated'},
        number={'suffix': '%'},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={'axis': {'range': [None, 100], 'tick0': 0, 'dtick': 20}}
    ))

    submittedGauge = go.Figure(go.Indicator(
        mode='gauge+number',
        value=(submitted_total / geojson_file_count) * 100,
        title={'text': 'Submitted'},
        number={'suffix': '%'},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={'axis': {'range': [None, 100], 'tick0': 0, 'dtick': 20}}
    ))

    totalSizeNumber = go.Figure(go.Indicator(
        mode='number',
        value=size_total,
        title={'text': 'Total Size'},
        number={'valueformat': '.2f', 'suffix': 'GB'},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))

    totalObsNumber = go.Figure(go.Indicator(
        mode='number',
        value=(observations_total / 100000),
        title={'text': 'Total Observations'},
        number={'valueformat': '.2f', 'suffix': 'M'},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))

    obsUsedGauge = go.Figure(go.Indicator(
        mode='gauge+number',
        value=10,
        title={'text': 'Observations Used'},
        number={'suffix': '%'},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={'axis': {'range': [None, 100], 'tick0': 0, 'dtick': 20}}
    ))

    totalObserversNumber = go.Figure(go.Indicator(
        mode='number+delta',
        value=observer_total,
        delta={'reference': 0, 'valueformat': '.0f'},
        title={'text': 'Total Observers'},
        number={'valueformat': '.0f'},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))

    noReportsNumber = go.Figure(go.Indicator(
        mode='number+delta',
        value=zero_reports_total,
        delta={'reference': 20, 'valueformat': '.0f'},
        title={'text': 'Zero Reports/Last Month'},
        number={'valueformat': '.0f'},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))

    newObserverFileCountGraph = px.line(observer_file_total_df, x='observer', y='files')
    observerFileCountGraph.update_layout(xaxis_title='Observer Name', yaxis_title='Files Submitted')

    newObserverSndCountGraph = px.line(observer_file_total_df, x='observer', y='soundings')
    observerSndCountGraph.update_layout(xaxis_title='Observer Name', yaxis_title='Soundings Submitted')

    return {
        "uploadNumber": uploadNumber,
        "submissionGraph": newSubmissionGraph,
        "locationGraph": newLocationGraph,
        "convertedGauge": convertedGauge,
        "validatedGauge": validatedGauge,
        "submittedGauge": submittedGauge,
        "totalSizeNumber": totalSizeNumber,
        "totalObsNumber": totalObsNumber,
        "obsUsedGauge": obsUsedGauge,
        "noReportsNumber": noReportsNumber,
        "observerFileCountGraph": newObserverFileCountGraph,
        "totalObserversNumber": totalObserversNumber,
        "observerSndCountGraph": newObserverSndCountGraph
    }


@app.callback(
    dash.dependencies.Output('upload-Number', 'figure'),
    dash.dependencies.Output('submission-Graph', 'figure'),
    dash.dependencies.Output('location-Graph', 'figure'),
    dash.dependencies.Output('converted-Gauge', 'figure'),
    dash.dependencies.Output('validated-Gauge', 'figure'),
    dash.dependencies.Output('submitted-Gauge', 'figure'),
    dash.dependencies.Output('total-Size-Number', 'figure'),
    dash.dependencies.Output('total-Obs-Number', 'figure'),
    dash.dependencies.Output('obs-Used-Gauge', 'figure'),
    dash.dependencies.Output('total-Observers-Number', 'figure'),
    dash.dependencies.Output('no-Reports-Number', 'figure'),
    dash.dependencies.Output('observer-File-Count-Graph', 'figure'),
    dash.dependencies.Output('observer-Snd-Count-Graph', 'figure'),
    [dash.dependencies.Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    figures = asyncio.run(loadData())
    return (figures['uploadNumber'], figures['submissionGraph'], figures['locationGraph'], figures['convertedGauge'],
            figures['validatedGauge'], figures['submittedGauge'], figures['totalSizeNumber'], figures['totalObsNumber'],
            figures['obsUsedGauge'], figures['totalObserversNumber'], figures['noReportsNumber'],
            figures['observerFileCountGraph'], figures['observerSndCountGraph'])


@app.callback(
    dash.dependencies.Output('interval-component', 'interval'),
    [dash.dependencies.Input('interval-dropdown', 'value')]
)
def change_interval(val):
    seconds_left = val // 1000
    return val


@app.callback(
    dash.dependencies.Output('countdown-display', 'children'),
    [dash.dependencies.Input('countdown-tick', 'n_intervals'),
     dash.dependencies.State('interval-component', 'interval'),
     dash.dependencies.State('interval-component', 'n_intervals')]
)
def update_countdown(tick, current_interval, update_count):
    seconds = current_interval // 1000

    elapsed = tick % seconds
    seconds_left = seconds - elapsed
    return f"Next update in {seconds_left} seconds."


@app.callback(
    dash.dependencies.Output('update-output', 'children'),
    [dash.dependencies.Input('interval-component', 'n_intervals')]
)
def report_update(n):
    return f"Last Update at {time.strftime('%X')}"

