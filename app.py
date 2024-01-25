from flask import Flask, render_template, redirect, url_for, session, request, jsonify, make_response
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
from urllib.parse import quote
from urllib.parse import urlparse, urlunparse
from functools import wraps



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
data_dict = {'Measurement': [], 'Mass (1000 x kg)': [], 'Temperature (°C)': [], 'Current Time': []}

# Sample data
dt = {"Measurement": [],
      "Mass (1000 x kg)": []}

df = pd.DataFrame(dt)
fig = px.line(df, x="Measurement", y="Mass (1000 x kg)", markers=True, template='plotly_dark',
              title="Real-time ore pile mass")



# Start the scheduler for updating data every 1 minute
scheduler = BackgroundScheduler()
def get_temperature():
    observation = mgr.weather_at_place("Belo Horizonte,BR")
    w = observation.weather
    return w.temperature('celsius')['temp']

def update_data():
    # Update data_dict with current time, temperature, and random Mass values
    current_time_zero=datetime.now()
    new_time=current_time_zero
    current_time = new_time.strftime("%H:%M:%S")
    temperature = get_temperature()
    random_mass = round(np.random.uniform(5, 20), 2)  # Substituir isso pelo método real de obtenção de massa aleatória

    # Verifica se a lista 'Measurement' está vazia
    if data_dict['Measurement']:
        next_time = max(data_dict['Measurement']) + 1
    else:
        next_time = 1

    # Append new data to the dictionary
    data_dict['Measurement'].append(next_time)
    data_dict['Mass (1000 x kg)'].append(random_mass)
    data_dict['Temperature (°C)'].append(temperature)
    data_dict['Current Time'].append(current_time)

update_data()
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
                html.H4(f"Username", id='user-full-name', style={'font-size': '17px'}),
                html.A(
                    html.Button("Download Data", id="download-button", style=button_style),
                    id="download-link",
                    download="data.xlsx",
                    href="",
                    target="_blank",
                    style={'margin-top': '10px'}
                ),
                html.A(
                    html.Button("Logout", id="logout-button", style=button_style),
                    href="/azure_logout",
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
                    interval=30 * 1000,
                    n_intervals=0
                ),
                dcc.Interval(
                    id='table-interval-component',
                    interval=30 * 1000,
                    n_intervals=0
                ),
                html.Div(
                    id='top-section',
                    style={'position': 'static', 'top': '5px', 'left': '23%', 'width': '100%', 'height': '10%'},
                    children=[
                        dash_table.DataTable(
                            id='table-data',
                            columns=[
                                {'name': 'Measurement', 'id': 'Measurement'},
                                {'name': 'Mass (1000 x kg)', 'id': 'Mass (1000 x kg)'},
                                {'name': 'Temperature (°C)', 'id': 'Temperature (°C)'},
                                {'name': 'Current Time', 'id': 'Current Time'}
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

    update_data()

    # Atualizar o gráfico com as novas informações
    new_fig = px.line(pd.DataFrame(data_dict),
                      x="Measurement", y="Mass (1000 x kg)",
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

    return pd.DataFrame(data_dict).to_dict('records'), new_fig


# Inline CSS styles
app.layout = html.Div(children=[
    dcc.Location(id='url', refresh=False),
    dcc.Interval(
        id='interval-component',
        interval=30*1000,  # em milissegundos, atualiza a cada 30 segundos
        n_intervals=0
    ),
    dcc.Interval(
        id='table-interval-component',
        interval=30*1000,  # em milissegundos, atualiza a cada minuto
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

import uuid
# Rota de logout do Azure AD
@app.route('/azure_logout')
def azure_logout():
    # Limpa a sessão Flask
    session.clear()

    # Set cache control headers to prevent caching
    response = make_response(redirect('/?rand=' + str(uuid.uuid4())))
    response.headers['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response.headers['Pragma'] = 'no-cache'
    response.headers['Expires'] = '0'
    response.delete_cookie('azure_token')

    # Construct the logout URL
    logout_url = 'https://login.microsoftonline.com/6495f1e2-0d47-4be2-826d-bef88fc09df3/oauth2/v2.0/logout?post_logout_redirect_uri='
    redirect_uri = url_for('page_logout', _external=True)
    logout_url += quote(redirect_uri)
    # Ensure the URI is properly encoded
    encoded_redirect_uri = quote(redirect_uri, safe='')
    # Append the encoded URI to the logout URL
    logout_url += encoded_redirect_uri
    # Redirect the user to the Azure AD logout URL
    return redirect(logout_url)

# Add your existing route for page_logout.html
@app.route('/pagina_logout')
def page_logout():
    # Add any logic or rendering for your page_logout.html page
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

    # Render the Dash app content if authenticated
    return dash_app.index()

# Rota de logout quando a aba é fechada
@app.route('/logout_on_close', methods=['GET'])
def logout_on_close():
    # Limpa a sessão Flask
    session.clear()
    return jsonify({'message': 'Logout successful on tab close'})

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


# Função para obter o token
@azure.tokengetter
def get_azure_oauth_token():
    return session.get('azure_token')

if __name__ == '__main__':
    app.run(debug=True)
