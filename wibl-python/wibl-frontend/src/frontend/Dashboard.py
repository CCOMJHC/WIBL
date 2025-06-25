from dash import Dash, dcc, html
from django_plotly_dash import DjangoDash
import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np

lr_margin=50
graphWidth=300
graphHeight=200

n_observers = 186
n_submit_days = 60

def getData():
    test_json_response = {
        "WiblFileCount" : 20,
        "GeojsonFileCount": 10,
        "SizeTotal" : 200,
        "DepthTotal" : 100,
        "ConvertedTotal" : 10,
        "ProcessingFailedTotal" : 0,
        "UploadFailedTotal" : 0,
        "ValidatedTotal" : 0,
        "SubmittedTotal" : 0,
        "ObserverTotal": 120,
        "SoundingTotal" : 10
    }
    obs_x_axis = np.arange(test_json_response['ObserverTotal'])
    Observer_df = pd.DataFrame(data={'observer': obs_x_axis, 'files': test_json_response['WiblFileCount'],
                                     'soundings': test_json_response['SoundingTotal']})

    sub_x_axis = x_axis = -n_submit_days + 1 + np.arange(n_submit_days)
    Submit_df = pd.DataFrame(data = {'date' : sub_x_axis, 'submissions': test_json_response['WiblFileCount']})





def generateObserverFileData(nobs: int) -> pd.DataFrame:
    x_axis = np.arange(nobs)
    rng = np.random.default_rng()
    fileCount = rng.integers(low=0, high=500, size=nobs)
    sndCount = rng.integers(low=2000, high=10000, size=nobs)
    sndCount *= fileCount
    df = pd.DataFrame(data={'observer': x_axis, 'files': fileCount, 'soundings': sndCount})
    return df

observerData = generateObserverFileData(n_observers)
totalObservations = observerData['soundings'].sum()

def generateSubmitData(nobs: int) -> pd.DataFrame:
    x_axis = -n_submit_days + 1 + np.arange(nobs)
    rng = np.random.default_rng()
    submissions = rng.integers(low=5, high=50, size=nobs)
    df = pd.DataFrame(data={'date': x_axis, 'submissions': submissions})
    return df

submissionData = generateSubmitData(n_submit_days)

def generateLocationData(nobs: int) -> pd.DataFrame:
    rng = np.random.default_rng()
    x_axis = -180 + rng.integers(low=0, high=360, size=nobs)
    y_axis = -60 + rng.integers(low=0, high=120, size=nobs)
    df = pd.DataFrame(data={'longitude': x_axis, 'latitude': y_axis})
    return df

locationData = generateLocationData(submissionData['submissions'].iloc[-1])

uploadNumber = go.Figure(go.Indicator(
    mode = 'number+delta',
    value = 14350,
    delta = {'reference': 11232, 'valueformat': '.0f'},
    title = {'text': 'Uploaded', 'font': {'size': 20}},
    domain = {'x': [0,1], 'y': [0,1]},
    number = {'valueformat': '.0f', 'font': {'size': 60}}
))
uploadNumber.update_layout(autosize=False, width=2*graphWidth, height=graphHeight, margin=dict(l=0,r=0,b=0,t=0))

submissionGraph = px.line(submissionData, x='date', y='submissions')
submissionGraph.update_layout(autosize=False, width=2*graphWidth, height=graphHeight, margin=dict(l=0,r=0,t=0,b=0),
                                xaxis_title='Days', yaxis_title='Files Submitted')
locationGraph = px.scatter_geo(locationData, lon='longitude', lat='latitude', projection='natural earth')
locationGraph.update_layout(autosize=False, height=1.2*graphHeight, margin=dict(l=0,r=0,t=0,b=0))

convertedGauge = go.Figure(go.Indicator(
    mode = "gauge+number+delta",
    value = 80,
    title = {'text': 'Converted'},
    number = {'suffix': '%'},
    delta = {'reference': 75, 'valueformat': '0.1f', 'suffix': '%'},
    domain = {'x': [0, 1], 'y': [0, 1]},
    gauge = { 'axis': {'range': [None,100], 'tick0': 0, 'dtick': 20 } }
))
convertedGauge.update_layout(autosize=False, width=graphWidth, height=1.25*graphHeight, margin=dict(l=lr_margin,r=lr_margin,b=0,t=0))

validatedGauge = go.Figure(go.Indicator(
    mode='gauge+number+delta',
    value=100,
    title = {'text': 'Validated'},
    number = {'suffix': '%'},
    delta = {'reference': 95, 'valueformat': '.1f', 'suffix': '%'},
    domain = {'x': [0,1], 'y': [0,1]},
    gauge = { 'axis': {'range': [None,100], 'tick0': 0, 'dtick': 20 } }
))
validatedGauge.update_layout(autosize=False, width=graphWidth, height=1.25*graphHeight, margin=dict(l=lr_margin,r=lr_margin,b=0,t=0))

submittedGauge = go.Figure(go.Indicator(
    mode='gauge+number+delta',
    value=90,
    title = {'text': 'Submitted'},
    number = {'suffix': '%'},
    delta = {'reference': 95, 'valueformat': '.1f', 'suffix': '%'},
    domain = {'x': [0,1], 'y': [0,1]},
    gauge = { 'axis': {'range': [None,100], 'tick0': 0, 'dtick': 20 } }
))
submittedGauge.update_layout(autosize=False, width=graphWidth, height=1.25*graphHeight, margin=dict(l=lr_margin,r=lr_margin,b=0,t=0))

totalSizeNumber = go.Figure(go.Indicator(
    mode='number+delta',
    value=35.02,
    delta={'reference': 34.87, 'valueformat': '.2f', 'suffix': 'GB'},
    title={'text': 'Total Size', 'font': {'size': 20}},
    number = {'valueformat': '.2f', 'suffix': 'GB', 'font': {'size': 60}},
    domain={'x': [0,1], 'y': [0,1]}
))
totalSizeNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight, margin=dict(l=lr_margin,r=lr_margin,b=0,t=0))

totalObsNumber = go.Figure(go.Indicator(
    mode='number+delta',
    value=totalObservations/1000000,
    delta={'reference': 0.9*totalObservations/1000000, 'valueformat': '.2f', 'suffix': 'M'},
    title={'text': 'Total Observations', 'font': {'size': 20}},
    number = {'valueformat': '.2f', 'suffix': 'M', 'font': {'size': 60}},
    domain={'x': [0,1], 'y': [0,1]}
))
totalObsNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight, margin=dict(l=lr_margin,r=lr_margin,t=0,b=0))

obsUsedGauge = go.Figure(go.Indicator(
    mode='gauge+number+delta',
    value=99,
    title = {'text': 'Observations Used'},
    number = {'suffix': '%'},
    delta = {'reference': 95, 'valueformat': '.1f', 'suffix': '%'},
    domain = {'x': [0,1], 'y': [0,1]},
    gauge = { 'axis': {'range': [None,100], 'tick0': 0, 'dtick': 20 } }
))
obsUsedGauge.update_layout(autosize=False, width=graphWidth, height=graphHeight, margin=dict(l=lr_margin,r=lr_margin,b=0,t=0))

totalObserversNumber = go.Figure(go.Indicator(
    mode='number+delta',
    value=n_observers,
    delta={'reference': 183, 'valueformat': '.0f'},
    title={'text': 'Total Observers', 'font': {'size': 20}},
    number = {'valueformat': '.0f', 'font': {'size': 60}},
    domain={'x': [0,1], 'y': [0,1]}
))
totalObserversNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight, margin=dict(l=lr_margin,r=lr_margin,t=0,b=0))

noReportsNumber = go.Figure(go.Indicator(
    mode='number+delta',
    value=13,
    delta={'reference': 20, 'valueformat': '.0f'},
    title={'text': 'Zero Reports/Last Month', 'font': {'size': 20}},
    number = {'valueformat': '.0f', 'font': {'size': 60}},
    domain={'x': [0,1], 'y': [0,1]}
))
noReportsNumber.update_layout(autosize=False, width=graphWidth, height=graphHeight, margin=dict(l=lr_margin,r=lr_margin,t=0,b=0))

observerFileCount = px.line(observerData, x='observer', y='files')
observerFileCount.update_layout(autosize=False, width=2*graphWidth, height=graphHeight, margin=dict(l=lr_margin,r=lr_margin,t=0,b=0),
                                xaxis_title='Observer Number', yaxis_title='Files Submitted')
observerSndCount = px.line(observerData, x='observer', y='soundings')
observerSndCount.update_layout(autosize=False, width=2*graphWidth, height=graphHeight, margin=dict(l=lr_margin,r=lr_margin,t=0,b=0),
                                xaxis_title='Observer Number', yaxis_title='Soundings Submitted')
app = DjangoDash("Dashboard")

app.layout = html.Div([
    html.H1(children='Current Status', style={'textAlign': 'center', 'font-family': 'Verdana'}),
    html.Div([
        html.Div([
            dcc.Graph(figure=uploadNumber),
            dcc.Graph(figure=submissionGraph),
            dcc.Graph(figure=locationGraph)
        ], style={'display': 'flex', 'flex-direction': 'column', 'justify-content': 'center'}),
        html.Div([
            dcc.Graph(figure=convertedGauge),
            dcc.Graph(figure=validatedGauge),
            dcc.Graph(figure=submittedGauge)
        ]),
        html.Div([
            html.Fieldset([
                html.Legend('WIBL Files', style={'font-size': 20, 'font-family': 'Verdana'}),
                html.Div([
                    dcc.Graph(figure=totalSizeNumber),
                    dcc.Graph(figure=totalObsNumber),
                    dcc.Graph(figure=obsUsedGauge)
                ], style={'display': 'flex'})
            ], style={'border-width': '5px'}),
            html.Fieldset([
                html.Legend('Observers', style={'font-size': 20, 'font-family': 'Verdana'}),
                html.Div([
                html.Div([
                    dcc.Graph(figure=totalObserversNumber),
                    dcc.Graph(figure=noReportsNumber)
                ]),
                html.Div([
                    dcc.Graph(figure=observerFileCount),
                    dcc.Graph(figure=observerSndCount)
                ])
                ], style={'display': 'flex'})
            ], style={'border-width': '5px'})
        ])
    ], style={'display': 'flex'})
])

