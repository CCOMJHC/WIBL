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

empty_graph = go.Figure()
empty_gauge = go.Figure()
empty_number = go.Figure()


# empty_graph.update_layout(autosize=False, width=2 * graphWidth, height=graphHeight,
#                                margin=dict(l=0, r=0, b=0, t=0))
#
# empty_gauge.update_layout(autosize=False, width=graphWidth, height=1.25 * graphHeight,
#                                  margin=dict(l=lr_margin, r=lr_margin, b=0, t=0))
#
# empty_number.update_layout(autosize=False, width=graphWidth, height=graphHeight,
#                                        margin=dict(l=lr_margin, r=lr_margin, t=0, b=0))
app = DjangoDash("Dashboard")

app.layout = html.Div([
    html.Button("Refresh Data", id="refresh-button"),
    html.H1(children='Current Status', style={'textAlign': 'center', 'font-family': 'Verdana'}),
    html.Div([
        html.Div([
            dcc.Graph(id="upload-Number", figure=empty_number),
            dcc.Graph(id = "submission-Graph", figure=empty_graph),
            dcc.Graph(id = "location-Graph", figure=empty_graph)
        ], style={'display': 'flex', 'flex-direction': 'column', 'justify-content': 'center'}),
        html.Div([
            dcc.Graph(id="converted-Gauge", figure=empty_gauge),
            dcc.Graph(id="validated-Gauge", figure=empty_gauge),
            dcc.Graph(id="submitted-Gauge", figure=empty_gauge)
        ], style={'display': 'flex', 'flex-direction': 'column', 'justify-content': 'center'}),
        html.Div([
            html.Fieldset([
                html.Legend('WIBL Files', style={'font-size': 20, 'font-family': 'Verdana'}),
                html.Div([
                    dcc.Graph(id="total-Size-Number", figure=empty_number),
                    dcc.Graph(id="total-Obs-Number", figure=empty_number),
                    dcc.Graph(id="obs-Used-Gauge", figure=empty_gauge)
                ], style={'display': 'flex'})
            ], style={'border-width': '5px'}),
            html.Fieldset([
                html.Legend('Observers', style={'font-size': 20, 'font-family': 'Verdana'}),
                html.Div([
                html.Div([
                    dcc.Graph(id="total-Observers-Number", figure=empty_number),
                    dcc.Graph(id="no-Reports-Number", figure=empty_number)
                ], style={
                    'flex': '1',
                    'height': '100%',
                    'display': 'flex',
                    'flexDirection': 'column'
                }),
                html.Div([
                    dcc.Graph(id="observer-File-Count", figure=empty_number),
                    dcc.Graph(id="observer-Snd-Count", figure=empty_number)
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
    observer_total = manager_res['ObserverTotal']

    uploadNumber = go.Figure(go.Indicator(
        mode='number+delta',
        value=wibl_file_count,
        delta={'reference': 0, 'valueformat': '.0f'},
        title={'text': 'Uploaded', 'font': {'size': 20}},
        domain={'x': [0, 1], 'y': [0, 1]},
        number={'valueformat': '.0f', 'font': {'size': 60}}
    ))
    uploadNumber.update_layout(autosize=False, width=2 * graphWidth, height=graphHeight,
                               margin=dict(l=0, r=0, b=0, t=0))

    submissionGraph = px.line(file_date_df, x='date', y='submissions')
    submissionGraph.update_layout(autosize=False, width=2 * graphWidth, height=graphHeight,
                                  margin=dict(l=0, r=0, t=0, b=0),
                                  xaxis_title='Days', yaxis_title='Files Submitted')

    convertedGauge = go.Figure(go.Indicator(
        mode="gauge+number+delta",
        value=(converted_total / wibl_file_count) * 100,
        title={'text': 'Converted'},
        number={'suffix': '%'},
        delta={'reference': 0, 'valueformat': '0.1f', 'suffix': '%'},
        domain={'x': [0, 1], 'y': [0, 1]},
        gauge={'axis': {'range': [None, 100], 'tick0': 0, 'dtick': 20}}
    ))
    convertedGauge.update_layout(autosize=False, width=graphWidth, height=1.25 * graphHeight,
                                 margin=dict(l=lr_margin, r=lr_margin, b=0, t=0))

    locationData = generateLocationData(file_date_df['submissions'].iloc[-1])

    locationGraph = px.scatter_geo(locationData, lon='longitude', lat='latitude', projection='natural earth')
    locationGraph.update_layout(autosize=False, height=1.2 * graphHeight, margin=dict(l=0, r=0, t=0, b=0))

    validatedGauge = go.Figure(go.Indicator(
        mode='gauge+number+delta',
        value=(validated_total / geojson_file_count) * 100,
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
        value=(submitted_total / geojson_file_count) * 100,
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
        value=size_total,
        delta={'reference': 0, 'valueformat': '.2f', 'suffix': 'GB'},
        title={'text': 'Total Size', 'font': {'size': 20}},
        number={'valueformat': '.2f', 'suffix': 'GB', 'font': {'size': 60}},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    totalSizeNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight,
                                  margin=dict(l=lr_margin, r=lr_margin, b=0, t=0))

    totalObsNumber = go.Figure(go.Indicator(
        mode='number+delta',
        value=depth_total,
        delta={'reference': 0, 'valueformat': '.2f', 'suffix': 'M'},
        title={'text': 'Total Observations', 'font': {'size': 20}},
        number={'valueformat': '.2f', 'suffix': 'M', 'font': {'size': 60}},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    totalObsNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight,
                                 margin=dict(l=lr_margin, r=lr_margin, t=0, b=0))

    obsUsedGauge = go.Figure(go.Indicator(
        mode='gauge+number+delta',
        value=10,
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
        value=observer_total,
        delta={'reference': 0, 'valueformat': '.0f'},
        title={'text': 'Total Observers', 'font': {'size': 20}},
        number={'valueformat': '.0f', 'font': {'size': 60}},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    totalObserversNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight,
                                       margin=dict(l=lr_margin, r=lr_margin, t=0, b=0))

    noReportsNumber = go.Figure(go.Indicator(
        mode='number+delta',
        value=13,
        delta={'reference': 20, 'valueformat': '.0f'},
        title={'text': 'Zero Reports/Last Month', 'font': {'size': 20}},
        number={'valueformat': '.0f', 'font': {'size': 60}},
        domain={'x': [0, 1], 'y': [0, 1]}
    ))
    noReportsNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight,
                                  margin=dict(l=lr_margin, r=lr_margin, t=0, b=0))

    observerFileCount = px.line(observer_file_total_df, x='observer', y='files')
    observerFileCount.update_layout(autosize=False, width=2 * graphWidth, height=graphHeight,
                                    margin=dict(l=lr_margin, r=lr_margin, t=0, b=0),
                                    xaxis_title='Observer Name', yaxis_title='Files Submitted')

    observerSndCount = px.line(observer_file_total_df, x='observer', y='soundings')
    observerSndCount.update_layout(autosize=False, width=2*graphWidth, height=graphHeight,
                                   margin=dict(l=lr_margin,r=lr_margin,t=0,b=0),
                                    xaxis_title='Observer Name', yaxis_title='Soundings Submitted')

    return {
        "uploadNumber": uploadNumber,
        "submissionGraph" : submissionGraph,
        "locationGraph" : locationGraph,
        "convertedGauge" : convertedGauge,
        "validatedGauge" : validatedGauge,
        "submittedGauge" : submittedGauge,
        "totalSizeNumber" : totalSizeNumber,
        "totalObsNumber" : totalObsNumber,
        "obsUsedGauge" : obsUsedGauge,
        "noReportsNumber" : noReportsNumber,
        "observerFileCount" : observerFileCount,
        "totalObserversNumber" : totalObserversNumber,
        "observerSndCount" : observerSndCount
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
    dash.dependencies.Output('observer-File-Count', 'figure'),
    dash.dependencies.Output('observer-Snd-Count', 'figure'),
    [dash.dependencies.Input('refresh-button', 'n_clicks')]
)
def update_dashboard(click):
    figures = asyncio.run(createApp())
    return (figures['uploadNumber'], figures['submissionGraph'], figures['locationGraph'], figures['convertedGauge'],
            figures['validatedGauge'], figures['submittedGauge'], figures['totalSizeNumber'], figures['totalObsNumber'],
            figures['obsUsedGauge'], figures['totalObserversNumber'], figures['noReportsNumber'], figures['observerFileCount'],
            figures['observerSndCount'])



