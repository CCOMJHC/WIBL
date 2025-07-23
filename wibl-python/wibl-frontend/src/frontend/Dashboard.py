import time
from dash import Dash, dcc, html
from django_plotly_dash import DjangoDash
import dash
import os
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import httpx
import asyncio

lr_margin = 50
graphWidth = 200
graphHeight = 100

# Create placeholder values
uploadNumber = go.Figure(go.Indicator(
    mode='number+delta',
    value=0,
    delta={'reference': 0, 'valueformat': '.0f'},
    title={'text': 'Uploaded', 'font': {'size': 20}},
    domain={'x': [0, 1], 'y': [0, 1]},
    number={'valueformat': '.0f', 'font': {'size': 50}}
))
uploadNumber.update_layout(autosize=False, width=2 * graphWidth, height= 1.3 * graphHeight,
                           margin=dict(l=40, r=0, b=0, t=30))

emptySubmissionsDf = pd.DataFrame(columns=['date', 'submissions'])
submissionGraph = px.line(emptySubmissionsDf, x='date', y='submissions')
#
submissionGraph.update_layout(autosize=False, xaxis_title='Days', yaxis_title='Files Submitted',
                              width=2 * graphWidth, height=5 * graphHeight, margin=dict(l=0, r=0, t=0, b=0))

convertedGauge = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=0,
    title={'text': 'Converted'},
    number={'suffix': '%'},
    delta={'reference': 0, 'valueformat': '0.1f', 'suffix': '%'},
    domain={'x': [0, 1], 'y': [0, 1]},
    gauge={'axis': {'range': [None, 100], 'tick0': 0, 'dtick': 20}}
))

convertedGauge.update_layout(autosize=False, width=1.2 * graphWidth, height=1.18 * graphHeight,
                             margin=dict(l=lr_margin, r=lr_margin, b=0, t=40))

emptyLocationDf = pd.DataFrame(columns=['longitude', 'latitude'])
locationGraph = px.scatter_geo(emptyLocationDf, lon='longitude', lat='latitude', projection='natural earth')

locationGraph.update_layout(autosize=False, height=1.2 * graphHeight, margin=dict(l=0, r=0, t=0, b=0))

validatedGauge = go.Figure(go.Indicator(
    mode='gauge+number+delta',
    value=0,
    title={'text': 'Validated'},
    number={'suffix': '%'},
    delta={'reference': 0, 'valueformat': '.1f', 'suffix': '%'},
    domain={'x': [0, 1], 'y': [0, 1]},
    gauge={'axis': {'range': [None, 100], 'tick0': 0, 'dtick': 20}}
))

validatedGauge.update_layout(autosize=False, width=1.2 * graphWidth, height=1.18 * graphHeight,
                             margin=dict(l=lr_margin, r=lr_margin, b=0, t=40))

submittedGauge = go.Figure(go.Indicator(
    mode='gauge+number+delta',
    value=0,
    title={'text': 'Submitted'},
    number={'suffix': '%'},
    delta={'reference': 0, 'valueformat': '.1f', 'suffix': '%'},
    domain={'x': [0, 1], 'y': [0, 1]},
    gauge={'axis': {'range': [None, 100], 'tick0': 0, 'dtick': 20}}
))

submittedGauge.update_layout(autosize=False, width=1.2 * graphWidth, height=1.18 * graphHeight,
                             margin=dict(l=lr_margin, r=lr_margin, b=0, t=40))

totalSizeNumber = go.Figure(go.Indicator(
    mode='number+delta',
    value=0,
    delta={'reference': 0, 'valueformat': '.2f', 'suffix': 'GB'},
    title={'text': 'Total Size', 'font': {'size': 15}},
    number={'valueformat': '.2f', 'suffix': 'GB', 'font': {'size': 30}},
    domain={'x': [0, 1], 'y': [0, 1]}
))

totalSizeNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight,
                              margin=dict(l=lr_margin, r=lr_margin, b=0, t=10))

totalObsNumber = go.Figure(go.Indicator(
    mode='number+delta',
    value=0,
    delta={'reference': 0, 'valueformat': '.2f', 'suffix': 'M'},
    title={'text': 'Total Observations', 'font': {'size': 15}},
    number={'valueformat': '.2f', 'suffix': 'M', 'font': {'size': 30}},
    domain={'x': [0, 1], 'y': [0, 1]}
))

totalObsNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight,
                             margin=dict(l=lr_margin, r=lr_margin, t=10, b=0))

obsUsedGauge = go.Figure(go.Indicator(
    mode='gauge+number+delta',
    value=0,
    title={'text': 'Observations Used', 'font': {'size': 15}},
    number={'suffix': '%'},
    delta={'reference': 0, 'valueformat': '.1f', 'suffix': '%'},
    domain={'x': [0, 1], 'y': [0, 1]},
    gauge={'axis': {'range': [None, 100], 'tick0': 0, 'dtick': 20}}
))

obsUsedGauge.update_layout(autosize=False, width=graphWidth, height=graphHeight,
                           margin=dict(l=lr_margin, r=lr_margin, b=0, t=35))

totalObserversNumber = go.Figure(go.Indicator(
    mode='number+delta',
    value=0,
    delta={'reference': 0, 'valueformat': '.0f'},
    title={'text': 'Total Observers', 'font': {'size': 18}},
    number={'valueformat': '.0f', 'font': {'size': 35}},
    domain={'x': [0, 1], 'y': [0, 1]}
))

totalObserversNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight,
                                   margin=dict(l=lr_margin - 20, r=lr_margin + 10, t=50, b=0))

noReportsNumber = go.Figure(go.Indicator(
    mode='number+delta',
    value=0,
    delta={'reference': 20, 'valueformat': '.0f'},
    title={'text': 'Zero Reports<br>Last Month', 'font': {'size': 18}},
    number={'valueformat': '.0f', 'font': {'size': 35}},
    domain={'x': [0, 1], 'y': [0, 1]}
))

noReportsNumber.update_layout(autosize=False, width=graphWidth, height= 1.2 * graphHeight,
                              margin=dict(l=lr_margin - 20, r=lr_margin + 10, t=60, b=0))

emptyObserverDf = pd.DataFrame(columns=['observer', 'files', 'soundings'])

observerFileCountGraph = px.line(emptyObserverDf, x='observer', y='files')

observerFileCountGraph.update_layout(autosize=False, xaxis_title='Observer Name', yaxis_title='Files Submitted',
                                     width=1.8 * graphWidth, height=5 * graphHeight,
                                     margin=dict(l=lr_margin, r=lr_margin, t=0, b=0))

observerSndCountGraph = px.line(emptyObserverDf, x='observer', y='soundings')

observerSndCountGraph.update_layout(autosize=False, xaxis_title='Observer Name', yaxis_title='Soundings Submitted',
                                    width=1.8 * graphWidth, height=5 * graphHeight,
                                    margin=dict(l=lr_margin, r=lr_margin, t=0, b=0))

config = {'displayModeBar': False}

app = DjangoDash("Dashboard")

app.layout = html.Div([
    dcc.Interval(
        id='interval-component',
        interval=5000,
        n_intervals=0
    ),
    html.Div([
        html.Div([
            html.Div([
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
                ], style={'margin-right': 50, 'width': 170}),
                html.Div([
                    html.Div(id="countdown-display"),
                    dcc.Interval(
                        id='countdown-tick',
                        interval=1000,
                        n_intervals=0
                    ),
                    html.Div(id='update-output')
                ], style={'margin-top': 10})
            ], style={'display': 'flex', 'font-family': 'Verdana', 'font-size': 13}),
            html.Div([
                dcc.Graph(id="upload-Number", figure=uploadNumber, config=config),
            ], style={'height': '130px'}),
            html.Div([
                dcc.Graph(id="submission-Graph", figure=submissionGraph)
            ], style={'height': '180px'}),
            dcc.Graph(id="location-Graph", figure=locationGraph)
        ], style={'display': 'flex', 'flex-direction': 'column', 'justify-content': 'center', 'height' : '617.250px',
                  'width': '446.398px'}),
        html.Div([
            dcc.Graph(id="converted-Gauge", figure=convertedGauge, config=config),
            dcc.Graph(id="validated-Gauge", figure=validatedGauge, config=config),
            dcc.Graph(id="submitted-Gauge", figure=submittedGauge, config=config)
        ], style={'display': 'flex', 'flex-direction': 'column', 'justify-content': 'center'}),
        html.Div([
            html.Fieldset([
                html.Legend('WIBL Files', style={'font-size': 15, 'font-family': 'Verdana'}),
                html.Div([
                    dcc.Graph(id="total-Size-Number", figure=totalSizeNumber, config=config),
                    dcc.Graph(id="total-Obs-Number", figure=totalObsNumber, config=config),
                    dcc.Graph(id="obs-Used-Gauge", figure=obsUsedGauge, config=config)
                ], style={'display': 'flex'})
            ], style={'border-width': '5px', 'width': '670px'}),
            html.Fieldset([
                html.Legend('Observers', style={'font-size': 15, 'font-family': 'Verdana'}),
                html.Div([
                    html.Div([
                        html.Div([
                            dcc.Graph(id="total-Observers-Number", figure=totalObserversNumber, config=config)
                        ], style={'width': '180px'}),
                        dcc.Graph(id="observer-File-Count-Graph", figure=observerFileCountGraph)
                    ], style={'display': 'flex', 'height': '200px'}),
                    html.Div([
                        html.Div([
                            dcc.Graph(id="no-Reports-Number", figure=noReportsNumber, config=config)
                        ], style={'width': '180px'}),
                        html.Div([
                            dcc.Graph(id="observer-Snd-Count-Graph", figure=observerSndCountGraph)
                        ], style={'width': '490px', 'height': '150px'})
                    ], style={'display': 'flex', 'height': '250px'})
                ], style={'height': '395.039px'})
            ], style={'border-width': '5px', 'width': '670px'})
        ], style={'width' : '670px'})
    ], style={'display': 'flex', 'margin-top' : '10px'})
], style={'overflow' : 'hidden'})


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


    uploadNumber.data[0].value = wibl_file_count

    newSubmissionGraph = px.line(file_date_df, x='date', y='submissions')
    newSubmissionGraph.update_layout(autosize=False, width=2 * graphWidth, height=1.7 * graphHeight,
                                     margin=dict(l=0, r=0, t=0, b=0),
                                     xaxis_title='Days', yaxis_title='Files Submitted')

    convertedGauge.data[0].value = (converted_total / wibl_file_count) * 100

    newLocationGraph = px.scatter_geo(emptyLocationDf, lon='longitude', lat='latitude', projection='natural earth')
    newLocationGraph.update_layout(autosize=False, height=2 * graphHeight, width=2 * graphWidth, margin=dict(l=15, r=0, t=20, b=0))

    validatedGauge.data[0].value = (validated_total / geojson_file_count) * 100

    submittedGauge.data[0].value = (submitted_total / geojson_file_count) * 100

    totalSizeNumber.data[0].value = size_total

    totalObsNumber.data[0].value = (observations_total / 100000)

    obsUsedGauge.data[0].value = 10

    totalObserversNumber.data[0].value = observer_total

    noReportsNumber.data[0].value = zero_reports_total

    newObserverFileCountGraph = px.line(observer_file_total_df, x='observer', y='files')
    newObserverFileCountGraph.update_layout(autosize=False, width=2.4 * graphWidth, height=1.7 * graphHeight,
                                         margin=dict(l=lr_margin, r=lr_margin, t=0, b=0),
                                         xaxis_title='Observer Name', yaxis_title='Files Submitted')

    newObserverSndCountGraph = px.line(observer_file_total_df, x='observer', y='soundings')
    newObserverSndCountGraph.update_layout(autosize=False, width=2.4 * graphWidth, height=1.7 * graphHeight,
                                        margin=dict(l=lr_margin, r=lr_margin, t=10, b=0),
                                        xaxis_title='Observer Name', yaxis_title='Soundings Submitted')

    return {
        "submissionGraph": newSubmissionGraph,
        "locationGraph": newLocationGraph,
        "observerFileCountGraph": newObserverFileCountGraph,
        "observerSndCountGraph": newObserverSndCountGraph
    }


@app.callback(
    dash.dependencies.Output('submission-Graph', 'figure'),
    dash.dependencies.Output('location-Graph', 'figure'),
    dash.dependencies.Output('observer-File-Count-Graph', 'figure'),
    dash.dependencies.Output('observer-Snd-Count-Graph', 'figure'),
    [dash.dependencies.Input('interval-component', 'n_intervals')]
)
def update_dashboard(n):
    figures = asyncio.run(loadData())
    return (figures['submissionGraph'], figures['locationGraph'], figures['observerFileCountGraph'],
            figures['observerSndCountGraph'])


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
