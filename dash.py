# This is a sample Python script.

# Press Shift+F10 to execute it or replace it with your code.
# Press Double Shift to search everywhere for classes, files, tool windows, actions, and settings.

import Strava_functions
import dash
import dash_core_components as dcc
import dash_html_components as html
from dash.dependencies import Input, Output
import plotly.express as px
import plotly.graph_objects as go

# Get the data to plot out of the postGRE Strava database
cart = Strava_functions.get_strava_activities("12210119")

# Define the Dash app
app = dash.Dash(__name__)

# Start making the layout of the app
app.layout = html.Div([

    # Title Row
    html.Div([
            html.Div(className='col-md-2'),
            html.Div(children=[
                html.H1(children='Strava Dashboard')],
                className='col-md-8',
                style={'textAlign': 'center', 'color': 'white'}),
            html.Div(className='col-md-2')
        ],
        className='row-eq-height',
        style={'background-color': '#385448'}
    ),

    # Row containing the Dropdown
    html.Div([
            html.Div(className='col-md-2'),
            html.Div(children=[
                dcc.Dropdown(id='graph-type',
                             options=[{'label': i, 'value': i} for i in cart['type'].unique()],
                             value='Run')],
                style={'width': '48%', 'display': 'inline-block', 'color': '#ffffff'}),
            html.Div(className='col-md-1'),
            html.Div(children=[
                dcc.Dropdown(id='year-select',
                             options=[{'label': i, 'value': i} for i in cart.year_month.dt.year.unique()],
                             value=2020)],
                style={'width': '48%', 'display': 'inline-block', 'color': '#ffffff'}),
            html.Div(className='col-md-2'),
        ],
        className='row-eq-height',
        style={'background-color': '#385448', 'color': 'white'}),

    # Row containing the indicators
    html.Div([
            html.Div(children=[dcc.Graph(id='run_indicator')], className="col-md-4"),
            html.Div(children=[dcc.Graph(id='bike_indicator')], className="col-md-4"),
            html.Div(children=[dcc.Graph(id='swim_indicator')], className="col-md-4")
        ],
        className='row-eq-height',
        style={'background-color': '#385448'}),

    # Row containing the Bar Chart
    html.Div([
            html.Div(className='col-md-1'),
            html.Div(children=[dcc.Graph(id='distance-barchart')], className="col-md-10"),
            html.Div(className='col-md-1')
        ],
        className='row-eq-height',
        style={'background-color': '#385448'}),

    # Row containing link to Github and Twitter

    html.Div([
           html.Div(className='col-md-2'),
           html.Div(children=
                    [html.A([
                              html.Img(
                               src='/assets/twitter.png',
                               style={
                                'height' : '100%',
                                'width' : '10%',
                                'float' : 'right',
                                'position' : 'relative',
                                'padding-top' : 0,
                                'padding-right' : 0
                               }
                        )
                    ], href='https://twitter.com/AndriesDraux')], className="col-md-4"),
           html.Div(children=
                    [html.A([
                              html.Img(
                               src='/assets/github2.png',
                               style={
                                'height' : '100%',
                                'width' : '10%',
                                'float' : 'left',
                                'position' : 'relative',
                                'padding-top' : 0,
                                'padding-right' : 0
                               }
                        )
                    ], href='https://github.com/AndriesDraux')],className='col-md-4'),
           html.Div(className='col-md-2')
        ],
        className='row-eq-height',
        style={'background-color': '#385448'})

    ])

# Start defining the callback functions for making the graphs interactive

# Callback for the Barchart
@app.callback(
    Output('distance-barchart', 'figure'),
    Input('graph-type', 'value'),
    Input('year-select', 'value'))
def update_barchart(sport_type, year):
    type_data = cart.loc[(cart['type'] == sport_type) & (cart.year_month.dt.year == year)]
    months_ticks = cart.year_month.loc[cart.year_month.dt.year == year]

    fig = px.bar(type_data, x='year_month', y='distance_in_km')
    fig.update_yaxes(ticksuffix=" km", title_text="", color='white')
    fig.update_xaxes(tickvals=months_ticks, tickformat="%b", title_text="", color='white')
    fig.update_layout(xaxis_range=['{}-12-01'.format(int(year)-1), '{}-12-31'.format(year)] ,
                      plot_bgcolor= '#385448', paper_bgcolor= '#385448')

    return fig

# Callback for the Run Indicator
@app.callback(
    Output('run_indicator', 'figure'),
    Input('year-select', 'value'))

def update_run_indicator(year):
    cart['year'] = cart.year_month.dt.year
    run_data = cart.loc[(cart['type'] == "Run") & (cart.year_month.dt.year == year)]. \
        groupby('year', as_index=False).agg({'distance_in_km': 'sum', 'distance': 'sum'})

    fig = go.Figure(go.Indicator(
        mode="number",
        value= run_data.distance_in_km[0],
        title=dict(text = "Total km Run in {}".format(year)),
        number={"font": {"size": 56}}
    ))
    fig.update_layout(height=200, font=dict(color = "white"), paper_bgcolor='#385448')
    return fig

# Callback for the Bike indicator
@app.callback(
    Output('bike_indicator', 'figure'),
    Input('year-select', 'value'))

def update_bike_indicator(year):
    cart['year'] = cart.year_month.dt.year
    bike_data = cart.loc[(cart['type'] == "Ride") & (cart.year_month.dt.year == year)]. \
        groupby('year', as_index=False).agg({'distance_in_km': 'sum', 'distance': 'sum'})

    fig = go.Figure(go.Indicator(
        mode="number",
        value=bike_data.distance_in_km[0],
        title="Total km Biked in {}".format(year),
        number={"font": {"size": 56}}
    ))
    fig.update_layout(height=200, font=dict(color = "white"), paper_bgcolor='#385448')
    return fig

# Callback for the Swim indicator
@app.callback(
    Output('swim_indicator', 'figure'),
    Input('year-select', 'value'))

def update_swim_indicator(year):
    cart['year'] = cart.year_month.dt.year
    swim_data = cart.loc[(cart['type'] == "Swim") & (cart.year_month.dt.year == year)]. \
        groupby('year', as_index=False).agg({'distance_in_km': 'sum', 'distance': 'sum'})

    fig = go.Figure(go.Indicator(
        mode="number",
        value=swim_data.distance_in_km[0],
        title="Total km Swum in {}".format(year),
        number={"font": {"size": 56}}
    ))
    fig.update_layout(height=200, font=dict(color = "white"), paper_bgcolor='#385448')
    return fig

# Press the green button in the gutter to run the script.
if __name__ == '__main__':
    app.run_server(debug=True)