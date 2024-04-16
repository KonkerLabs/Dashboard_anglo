from flask import Flask, render_template, redirect, url_for, session, request, send_file, jsonify, make_response
from flask_oauthlib.client import OAuth
from flask_session import Session
from dash import Dash, html
from dash.dependencies import Input, Output
from dash import Dash, html, dcc, dash_table, callback, Input, Output, State
import plotly.express as px
import pandas as pd
from PIL import Image
from dash import callback, Input, Output, State
from datetime import datetime, timedelta
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
import pyowm
import base64
from io import BytesIO
import numpy as np
import uuid
from urllib.parse import quote
from urllib.parse import urlparse, urlunparse
from functools import wraps

import requests
import json
import sys
import os
from dotenv import load_dotenv
import time


UPDATE_INTERVAL = 15 * 60 * 1000 # Update time in milisseconds (15 min)

def request_from_API(uri):
    load_dotenv()
    TOKEN = os.environ.get('TOKEN')
    headers = {'Authorization': TOKEN}
    url_base_api = 'http://129.148.56.204:5000/api/v1/'

    try:
        response = requests.get(url=url_base_api+uri, headers=headers)
        if response.status_code == 200:
            data = response.json()
            payload = data["payload"]
            return payload

            if not data:
                print("No data available.")
        else:
            logging.error(f"Bad response - Status code: {response.status_code}")
    except Exception as e:
        print("An error occurred while fetching data.")


external_stylesheets = ['https://codepen.io/chriddyp/pen/bWLwgP.css', '/static/styles.css']
pil_img = Image.open("logo-blavk.png")
# Adicione a definição do button_style aqui
button_style = {
    'margin-top': '20px',
    'background-color': 'black',
    'color': 'white',
    'border': '0.5px solid white',
    'padding': '10px',
    'cursor': 'pointer'
}

app = Flask(__name__)
app.config["SECRET_KEY"] = "9P39loaIYctJ"
app.config['SESSION_TYPE'] = 'filesystem'  # Use the filesystem to store session data
Session(app)  # Initialize the Session extension

# Configuração do Azure OAuth
oauth = OAuth(app)
azure = oauth.remote_app(
    'azure',
    consumer_key='832378f7-5fee-4713-af36-a88afc95c134',
    consumer_secret='wa48Q~WEShjsG6qZntEIuu~h-4B.Cnb5Iu2n1aTD',
    request_token_params={'scope': 'user.read'},
    base_url='https://graph.microsoft.com/v1.0/',
    request_token_url=None,
    access_token_method='POST',
    access_token_url='https://login.microsoftonline.com/6495f1e2-0d47-4be2-826d-bef88fc09df3/oauth2/v2.0/token',
    authorize_url='https://login.microsoftonline.com/6495f1e2-0d47-4be2-826d-bef88fc09df3/oauth2/v2.0/authorize'
)

# Criação do aplicativo Dash
dash_app = Dash(__name__, server=app, url_base_pathname='/dashboard/')


owm = pyowm.OWM('fa47fceaf9e211df22cedbb5c4f2b456')  # Substitua pela sua chave real do OWM
mgr = owm.weather_manager()

# Dicionário para armazenar dados
data_dict = {'Measurement date': [],
             'Measurement time': [],
             'Mass (kTon)': [],
             'Temperature (°C)': [],
             'Measurement': []
            }

# Start the scheduler for updating data every 1 minute
scheduler = BackgroundScheduler()

def get_temperature():
    observation = mgr.weather_at_place("Belo Horizonte,BR")
    w = observation.weather
    return w.temperature('celsius')['temp']

# Update data_dict with current time, temperature, and random Mass values
def update_data():
    current_time_zero=datetime.now()
    new_time=current_time_zero
    temperature = get_temperature()

    try:
        payload = request_from_API('?limit=10')

        for item in payload:
            ts   = item["_ts"]
            time = pd.to_datetime(ts, unit='s', utc=True).tz_convert('America/Sao_Paulo')

            if time in data_dict['Measurement date']:
                pass
            else:
                current_time_zero=datetime.now()
                new_time=current_time_zero
                temperature = get_temperature()

                mass = item["instantaneous_mass"]
                #date = datetime.utcfromtimestamp(ts).strftime('%Y-%m-%d')
                date = time.strftime('%d-%m-%Y')  # Formatar a data como DD-MM-AAAA
                time_str = time.strftime('%H:%M:%S')  # Formatar a hora como HH:MM:SS

                # Append new data to the dictionary
                data_dict['Measurement date'].insert(0, date)
                data_dict['Measurement time'].insert(0, time_str)
                data_dict['Mass (kTon)'].insert(0, mass)
                data_dict['Temperature (°C)'].insert(0, temperature)
                data_dict['Measurement'].insert(0, time)

    except Exception as e:
        print("An error occurred while fetching data: using old data.")


update_data()

num_values = 10 # Maximum of data displayed on the graph

df = pd.DataFrame(data_dict)

subset_df = df.tail(num_values)
fig = px.line(subset_df, x="Measurement", y="Mass (kTon)", markers=True, template='plotly_dark',
              title="Real-time ore pile mass")


dash_app.layout = html.Div(
    children=[
        html.Div(
            id='sidebar',
            className='sidebar',
            style={
                'position': 'fixed',
                'top': 0,
                'left': 0,
                'responsive': True,
                'width': '18%',
                'height': '100%',
                'background-color': 'black',
                'padding': '20px',
                'color': 'white',
                'font-family': 'Arial, sans-serif',
            },
            children=[
                html.Img(src=Image.open("dashboard.png"), style={'height': '20%', 'width': '110%'}),
                html.H3(f"Welcome,", style={'font-size': '20px'}),
                html.H4(f"Anglo American", id='user-full-name', style={'font-size': '17px'}),
                html.A(
                    html.Button("Download Data", id="download-button", style=button_style),
                    id="download-link",
                    download="data.csv",
                    href="/download_csv",
                    target="_blank",
                    style={'margin-top': '10px'}
                ),
                html.A(
                    html.Button("Logout", id="logout-button", style=button_style),
                    href="/do_logout",
                    style={'margin-bottom': '50px'}
                ),
            ],
        ),
        html.Div(
            id='info-container',
            style={
                'margin-left': '23%',
                'width': '100%',
                'height': '40%',
                'margin-right': 0,
                'overflowY': 'hidden',
                'overflowX': 'hidden',
                'padding': '0'
            },
            children=[
                dcc.Interval(
                    id='interval-component',
                    interval= UPDATE_INTERVAL,
                    n_intervals=0
                ),
                dcc.Interval(
                    id='table-interval-component',
                    interval= UPDATE_INTERVAL,
                    n_intervals=0
                ),
                html.Div(
                    id='top-section',
                    style={'position': 'static', 'top': '5px', 'left': '23%', 'width': '100%', 'height': '10%'},
                    children=[
                        dash_table.DataTable(
                            id='table-data',
                            columns=[
                                {'name': 'Measurement date', 'id': 'Measurement date'},
                                {'name': 'Time', 'id': 'Measurement time'},
                                {'name': 'Mass (kTon)', 'id': 'Mass (kTon)'},
                                {'name': 'Temperature (°C)', 'id': 'Temperature (°C)'},
                                
                            ],
                            data=pd.DataFrame(data_dict).to_dict('records'),
                            style_table={'height': 275, 'width': '99%'},
                            style_cell={'textAlign': 'center', 'minWidth': '100px', 'font_size': '18px',
                                        'font_family': 'Arial, sans-serif'},
                            fixed_rows={'headers': True, 'data': 0},
                            virtualization=True,
                            page_action='none',
                            style_header={'backgroundColor': 'lightgreen', 'color': 'black', 'font_size': '20px',
                                          'font_family': 'Arial, sans-serif'},
                            style_as_list_view=True
                        ),
                    ],
                ),

                html.Div(
                    id='bottom-section',
                    style={'position': 'fixed', 'bottom': 0, 'left': '23%', 'width': '75%', 'height': '55%'},
                    children=[
                        dcc.Graph(
                            id='example-graph',
                            responsive=True,
                            figure=fig,
                            style={'height': '95%', 'width': '100%'}
                        ),
                    ],
                ),
            ],
        ),
    ],
    className='dashboard-page',
    style={'display': 'flex', 'align-items': 'right', 'justify-content': 'center', 'margin-top': '5px'}
)


# Sample Dash callback for updating the DataTable and the Graph
@dash_app.callback([Output('table-data', 'data'), Output('example-graph', 'figure')],
                   [Input('interval-component', 'n_intervals')],
                   [State('user-full-name', 'children')])

def update_data_and_graph(n_intervals, user_full_name):
    # Check if the user is authenticated
    if 'azure_token' not in session or session['azure_token'] is None:
        # Redirect to the Azure AD login page if not authenticated
        return redirect(url_for('login'))

    # Fetch user information using Azure OAuth token
    user_info = azure.get('me')
    full_name = user_info.data.get('displayName', 'User')  # Get the user's display name

    #########update_data()

    # Atualizar o dataframe e o gráfico com os dados mais recentes
    new_df = pd.DataFrame(data_dict).sort_values(by='Measurement', ascending=True)
    subset_df = new_df.tail(num_values)

    # Atualizar o gráfico com as novas informações
    new_fig = px.line(subset_df.tail(num_values),
                      x="Measurement", y="Mass (kTon)",
                      markers=True, template='plotly_dark',
                      width=1000, height=350, title="Real-time ore pile mass")
    # Centralizar o título do gráfico
    new_fig.update_layout(
        title=dict(
            text="Real-time ore pile mass",
            x=0.5,  # Posição horizontal centralizada (0 a 1)
            y=0.95  # Posição vertical ajustada (0 a 1)
        )
    )


    # Altera a cor de fundo do novo gráfico para verde claro e o texto para preto
    new_fig.update_layout(plot_bgcolor='lightgreen', paper_bgcolor='lightgreen', font_color='black')

    # Adiciona as linhas de grade do eixo x e y
    new_fig.update_xaxes(showgrid=True, gridwidth=1, gridcolor='gray')
    new_fig.update_yaxes(showgrid=True, gridwidth=1, gridcolor='gray')

    # Altera a fonte das letras do gráfico e aumenta o tamanho da fonte
    new_fig.update_layout(font=dict(family="Arial, sans-serif", size=16))

    # Altera a cor da linha do gráfico para preto
    new_fig.update_traces(line=dict(color='black'))

    return new_df.to_dict('records'), new_fig


# Inline CSS styles
app.layout = html.Div(children=[
    dcc.Location(id='url', refresh=False),
    dcc.Interval(
        id='interval-component',
        interval= UPDATE_INTERVAL,
        n_intervals=0
    ),
    dcc.Interval(
        id='table-interval-component',
        interval= UPDATE_INTERVAL,
        n_intervals=0
    ),
    html.Div(id='page-content', style={'width': '20%', 'margin': '0', 'overflowX': 'hidden'}),])

# Rota inicial
@app.route('/')
def index():
    return render_template('index.html')

# Rota de login
@app.route('/login')
def login():
    return azure.authorize(callback=url_for('authorized', _external=True))

# Rota para lidar com o logout efetivo
@app.route('/do_logout')
def do_logout():
    # Limpar a sessão Flask
    session.clear()

    # URL de logout do Azure AD
    # Substitua YOUR_TENANT_ID pelo seu ID de Tenant do Azure AD
    azure_logout_url = (
        f"https://login.microsoftonline.com/YOUR_TENANT_ID/oauth2/logout"
        f"?post_logout_redirect_uri=http://localhost:5000/page_logout"
    )

    # Redirecionar para a URL de logout do Azure AD
    return redirect(azure_logout_url)

# Rota para renderizar a página de logout
@app.route('/page_logout')
def page_logout():
    # Renderizar a página de logout
    return render_template('page_logout.html')

# Rota autorizada
@app.route('/login/authorized')
def authorized():
    response = azure.authorized_response()
    if response is None or response.get('access_token') is None:
        return 'A autenticação falhou ou foi cancelada.'

    session['azure_token'] = (response['access_token'], '')

    # Redirect to the dashboard upon successful authentication
    return redirect(dash_app.config.url_base_pathname + '/')

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'azure_token' not in session or session['azure_token'] is None:
            # Se o usuário não estiver autenticado, redirecione para a página de login
            return redirect(url_for('login', next=request.url))
        return f(*args, **kwargs)
    return decorated_function

# Rota da dashboard protegida
@dash_app.callback(Output('dashboard-content', 'children'), [Input('dummy-input', 'value')],
                   [State('user-full-name', 'children')])
@login_required
def display_dashboard(value, user_full_name):
    # Renderizar o conteúdo do aplicativo Dash se autenticado
    return dash_app.index()


# Add a callback to set initial values for the Dash app layout
@dash_app.callback(Output('user-full-name', 'children'),
                   [Input('dummy-input', 'value')], prevent_initial_call=True)
def set_initial_values(value):
    # Check if the user is authenticated
    if 'azure_token' not in session or session['azure_token'] is None:
        return 'User'  # Set a default value for user_full_name if not authenticated

    # Fetch user information using Azure OAuth token
    user_info = azure.get('me')
    full_name = user_info.data.get('displayName', 'User')  # Get the user's display name

    return full_name

@app.route('/download_csv')
def download_csv():
    # Criar DataFrame a partir do data_dict
    df = pd.DataFrame(data_dict)

    # Criar um objeto BytesIO para armazenar os dados do arquivo CSV
    csv_output = BytesIO()

    # Salvar o DataFrame como um arquivo CSV na memória
    df.to_csv(csv_output, index=False, sep=',')

    # Definir o ponteiro de leitura para o início do arquivo
    csv_output.seek(0)

    # Retornar o arquivo CSV como uma resposta de download
    return send_file(csv_output,
                     attachment_filename='data.csv',
                     as_attachment=True)

# Função para obter o token
@azure.tokengetter
def get_azure_oauth_token():
    return session.get('azure_token')

if __name__ == '__main__':
    app.run(debug=True)
