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

lr_margin=50
graphWidth=300
graphHeight=200

# Create placeholder values
uploadNumber = go.Figure(go.Indicator(
        mode='number+delta',
        value=0,
        delta={'reference': 0, 'valueformat': '.0f'},
        title={'text': 'Uploaded', 'font': {'size': 20}},
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'valueformat': '.0f', 'font': {'size': 60}}
    ))
uploadNumber.update_layout(autosize=False, width=2 * graphWidth, height=graphHeight,
                           margin=dict(l=0, r=0, b=0, t=0))

emptySubmissionsDf = pd.DataFrame(columns=['date', 'submissions'])
submissionGraph = px.line(emptySubmissionsDf, x='date', y='submissions')
submissionGraph.update_layout(autosize=False, width=2 * graphWidth, height=graphHeight,
                              margin=dict(l=0, r=0, t=0, b=0),
                              xaxis_title='Days', yaxis_title='Files Submitted')

convertedGauge = go.Figure(go.Indicator(
    mode="gauge+number+delta",
    value=0,
    title={'text': 'Converted'},
    number={'suffix': '%'},
    delta={'reference': 0, 'valueformat': '0.1f', 'suffix': '%'},
    domain={'x': [0, 1], 'y': [0, 1]},
    gauge={'axis': {'range': [None, 100], 'tick0': 0, 'dtick': 20}}
))
convertedGauge.update_layout(autosize=False, width=graphWidth, height=1.25 * graphHeight,
                             margin=dict(l=lr_margin, r=lr_margin, b=0, t=0))

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
validatedGauge.update_layout(autosize=False, width=graphWidth, height=1.25 * graphHeight,
                             margin=dict(l=lr_margin, r=lr_margin, b=0, t=0))

submittedGauge = go.Figure(go.Indicator(
    mode='gauge+number+delta',
    value=0,
    title={'text': 'Submitted'},
    number={'suffix': '%'},
    delta={'reference': 0, 'valueformat': '.1f', 'suffix': '%'},
    domain={'x': [0, 1], 'y': [0, 1]},
    gauge={'axis': {'range': [None, 100], 'tick0': 0, 'dtick': 20}}
))
submittedGauge.update_layout(autosize=False, width=graphWidth, height=1.25 * graphHeight,
                             margin=dict(l=lr_margin, r=lr_margin, b=0, t=0))

totalSizeNumber = go.Figure(go.Indicator(
    mode='number+delta',
    value=0,
    delta={'reference': 0, 'valueformat': '.2f', 'suffix': 'GB'},
    title={'text': 'Total Size', 'font': {'size': 20}},
    number={'valueformat': '.2f', 'suffix': 'GB', 'font': {'size': 60}},
    domain={'x': [0, 1], 'y': [0, 1]}
))
totalSizeNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight,
                              margin=dict(l=lr_margin, r=lr_margin, b=0, t=0))

totalObsNumber = go.Figure(go.Indicator(
    mode='number+delta',
    value=0,
    delta={'reference': 0, 'valueformat': '.2f', 'suffix': 'M'},
    title={'text': 'Total Observations', 'font': {'size': 20}},
    number={'valueformat': '.2f', 'suffix': 'M', 'font': {'size': 60}},
    domain={'x': [0, 1], 'y': [0, 1]}
))
totalObsNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight,
                             margin=dict(l=lr_margin, r=lr_margin, t=0, b=0))

obsUsedGauge = go.Figure(go.Indicator(
    mode='gauge+number+delta',
    value=0,
    title={'text': 'Observations Used'},
    number={'suffix': '%'},
    delta={'reference': 0, 'valueformat': '.1f', 'suffix': '%'},
    domain={'x': [0, 1], 'y': [0, 1]},
    gauge={'axis': {'range': [None, 100], 'tick0': 0, 'dtick': 20}}
))
obsUsedGauge.update_layout(autosize=False, width=graphWidth, height=graphHeight,
                           margin=dict(l=lr_margin, r=lr_margin, b=0, t=0))

totalObserversNumber = go.Figure(go.Indicator(
    mode='number+delta',
    value=0,
    delta={'reference': 0, 'valueformat': '.0f'},
    title={'text': 'Total Observers', 'font': {'size': 20}},
    number={'valueformat': '.0f', 'font': {'size': 60}},
    domain={'x': [0, 1], 'y': [0, 1]}
))
totalObserversNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight,
                                   margin=dict(l=lr_margin, r=lr_margin, t=0, b=0))

noReportsNumber = go.Figure(go.Indicator(
    mode='number+delta',
    value=0,
    delta={'reference': 20, 'valueformat': '.0f'},
    title={'text': 'Zero Reports/Last Month', 'font': {'size': 20}},
    number={'valueformat': '.0f', 'font': {'size': 60}},
    domain={'x': [0, 1], 'y': [0, 1]}
))
noReportsNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight,
                              margin=dict(l=lr_margin, r=lr_margin, t=0, b=0))

emptyObserverDf = pd.DataFrame(columns=['observer', 'files','soundings'])

observerFileCountGraph = px.line(emptyObserverDf, x='observer', y='files')
observerFileCountGraph.update_layout(autosize=False, width=2 * graphWidth, height=graphHeight,
                                     margin=dict(l=lr_margin, r=lr_margin, t=0, b=0),
                                     xaxis_title='Observer Name', yaxis_title='Files Submitted')

observerSndCountGraph = px.line(emptyObserverDf, x='observer', y='soundings')
observerSndCountGraph.update_layout(autosize=False, width=2 * graphWidth, height=graphHeight,
                                    margin=dict(l=lr_margin,r=lr_margin,t=0,b=0),
                                    xaxis_title='Observer Name', yaxis_title='Soundings Submitted')

app = DjangoDash("Dashboard")

app.layout = html.Div([
    html.Button("Refresh Data", id="refresh-button"),
    html.H1(children='Current Status', style={'textAlign': 'center', 'font-family': 'Verdana'}),
    html.Div([
        html.Div([
            dcc.Graph(id="upload-Number", figure=uploadNumber),
            dcc.Graph(id = "submission-Graph", figure=submissionGraph),
            dcc.Graph(id = "location-Graph", figure=locationGraph)
        ], style={'display': 'flex', 'flex-direction': 'column', 'justify-content': 'center'}),
        html.Div([
            dcc.Graph(id="converted-Gauge", figure=convertedGauge),
            dcc.Graph(id="validated-Gauge", figure=validatedGauge),
            dcc.Graph(id="submitted-Gauge", figure=submittedGauge)
        ], style={'display': 'flex', 'flex-direction': 'column', 'justify-content': 'center'}),
        html.Div([
            html.Fieldset([
                html.Legend('WIBL Files', style={'font-size': 20, 'font-family': 'Verdana'}),
                html.Div([
                    dcc.Graph(id="total-Size-Number", figure=totalSizeNumber),
                    dcc.Graph(id="total-Obs-Number", figure=totalObsNumber),
                    dcc.Graph(id="obs-Used-Gauge", figure=obsUsedGauge)
                ], style={'display': 'flex'})
            ], style={'border-width': '5px'}),
            html.Fieldset([
                html.Legend('Observers', style={'font-size': 20, 'font-family': 'Verdana'}),
                html.Div([
                html.Div([
                    dcc.Graph(id="total-Observers-Number", figure=totalObserversNumber),
                    dcc.Graph(id="no-Reports-Number", figure=noReportsNumber)
                ], style={
                    'flex': '1',
                    'height': '100%',
                    'display': 'flex',
                    'flexDirection': 'column'
                }),
                html.Div([
                    dcc.Graph(id="observer-File-Count-Graph", figure=observerFileCountGraph),
                    dcc.Graph(id="observer-Snd-Count-Graph", figure=observerSndCountGraph)
                ], style={
                    'flex': '1',
                    'height': '100%',
                    'display': 'flex',
                    'flexDirection': 'column'
                })
                ], style={'display': 'flex', 'height' : '500px'})
            ], style={'border-width': '5px'})
        ])
    ], style={'display': 'flex'})
])

async def getData():
    manager_url: str = os.environ.get('MANAGEMENT_URL', "http://manager:5000")

    client = httpx.AsyncClient()
    response = await client.get(manager_url + "/statistics")
    if response.status_code == 200:
        return response.json()
    else:
        return None

def generateLocationData(nobs: int) -> pd.DataFrame:
    rng = np.random.default_rng()
    x_axis = -180 + rng.integers(low=0, high=360, size=nobs)
    y_axis = -60 + rng.integers(low=0, high=120, size=nobs)
    df = pd.DataFrame(data={'longitude': x_axis, 'latitude': y_axis})
    return df


async def createApp():
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
    depth_total = manager_res['DepthTotal']
    zero_reports_total = manager_res['ObserverZeroReportsTotal']
    observer_total = manager_res['ObserverTotal']
    location_data = pd.DataFrame(manager_res['LocationData'])

    uploadNumber.data[0].value = wibl_file_count


    newSubmissionGraph = px.line(file_date_df, x='date', y='submissions')
    newSubmissionGraph.update_layout(autosize=False, width=2 * graphWidth, height=graphHeight,
                                  margin=dict(l=0, r=0, t=0, b=0),
                                  xaxis_title='Days', yaxis_title='Files Submitted')

    convertedGauge.data[0].value = (converted_total / wibl_file_count) * 100

    newLocationGraph = px.scatter_geo(location_data, lon='longitude', lat='latitude', projection='natural earth')
    newLocationGraph.update_layout(autosize=False, height=1.2 * graphHeight, margin=dict(l=0, r=0, t=0, b=0))

    validatedGauge.data[0].value = (validated_total / geojson_file_count) * 100

    submittedGauge.data[0].value = (submitted_total / geojson_file_count) * 100

    totalSizeNumber.data[0].value = size_total

    totalObsNumber.data[0].value = depth_total

    obsUsedGauge.data[0].value = 10

    totalObserversNumber.data[0].value = observer_total

    noReportsNumber.data[0].value = zero_reports_total

    newObserverFileCountGraph = px.line(observer_file_total_df, x='observer', y='files')
    observerFileCountGraph.update_layout(autosize=False, width=2 * graphWidth, height=graphHeight,
                                         margin=dict(l=lr_margin, r=lr_margin, t=0, b=0),
                                         xaxis_title='Observer Name', yaxis_title='Files Submitted')

    newObserverSndCountGraph = px.line(observer_file_total_df, x='observer', y='soundings')
    observerSndCountGraph.update_layout(autosize=False, width=2 * graphWidth, height=graphHeight,
                                        margin=dict(l=lr_margin,r=lr_margin,t=0,b=0),
                                        xaxis_title='Observer Name', yaxis_title='Soundings Submitted')

    return {
        "uploadNumber": uploadNumber,
        "submissionGraph" : newSubmissionGraph,
        "locationGraph" : newLocationGraph,
        "convertedGauge" : convertedGauge,
        "validatedGauge" : validatedGauge,
        "submittedGauge" : submittedGauge,
        "totalSizeNumber" : totalSizeNumber,
        "totalObsNumber" : totalObsNumber,
        "obsUsedGauge" : obsUsedGauge,
        "noReportsNumber" : noReportsNumber,
        "observerFileCountGraph" : newObserverFileCountGraph,
        "totalObserversNumber" : totalObserversNumber,
        "observerSndCountGraph" : newObserverSndCountGraph
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
    [dash.dependencies.Input('refresh-button', 'n_clicks')]
)
def update_dashboard(click):
    figures = asyncio.run(createApp())
    return (figures['uploadNumber'], figures['submissionGraph'], figures['locationGraph'], figures['convertedGauge'],
            figures['validatedGauge'], figures['submittedGauge'], figures['totalSizeNumber'], figures['totalObsNumber'],
            figures['obsUsedGauge'], figures['totalObserversNumber'], figures['noReportsNumber'],
            figures['observerFileCountGraph'], figures['observerSndCountGraph'])



