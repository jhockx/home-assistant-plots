print('Start influx script')

from datetime import datetime, date, timedelta
from time import sleep

import pandas as pd
import plotly.graph_objs as go
from influxdb import DataFrameClient

# Influxdb settings
host = ''
port = 8086
username = ''
password = ''
predicted_solar = {
    2020: {1: 98.07, 2: 161.26, 3: 272.15, 4: 325.21, 5: 364.55, 6: 358.59,
           7: 366.34, 8: 345.47, 9: 284.96, 10: 210.15, 11: 120.13, 12: 73.92}
}

# Pandas DataFrame results
client = DataFrameClient(host=host, port=port, username=username, password=password)
now = datetime.now()
first_day_of_the_month = pd.to_datetime(date(now.year, now.month, 1))
last_day_of_the_month = pd.to_datetime(date(now.year, now.month + 1, 1) - timedelta(days=1), utc=True)


def get_df_current_month(entity, unit, now, last_day_of_the_month):
    # Get daily data
    result = client.query(f"SELECT entity_id, value FROM homeassistant.infinite.{unit} WHERE entity_id = '{entity}' "
                          f"AND time >= now() - 31d")
    df = result[f'{unit}']
    df = df.sort_index().resample('D').max()

    # Filter data this month
    df = df[df.index.month == now.month]

    # Add empty value on the last day of the month for the plot (if it doesn't exist)
    if df.index[-1] != last_day_of_the_month:
        df = df.append(pd.DataFrame(index=[last_day_of_the_month], data=[[entity, 0]], columns=['entity_id', 'value']))
    return df


while True:
    print('Start loop...')

    # Build traces
    df = get_df_current_month('daily_electricity_usage_total', 'kWh', now, last_day_of_the_month)
    trace1 = go.Bar(name='Verbruik totaal', x=df.index, y=df['value'], marker_color='blue')
    df = get_df_current_month('daily_yield', 'kWh', now, last_day_of_the_month)
    trace2 = go.Bar(name='Opbrengst', x=df.index, y=df['value'], marker_color='limegreen')

    # Plotly build figure
    data = [trace1, trace2]
    layout = {
        "yaxis": dict(title='kWh'),
        "margin": dict(l=0, r=0, t=0, b=1),
        "legend_orientation": "h"
    }
    fig = go.Figure(data=data, layout=layout)
    fig.add_shape(
        # Predicted (mean) solar horizontal line
        type="line",
        x0=first_day_of_the_month,
        y0=predicted_solar[now.year][now.month] / last_day_of_the_month.day,
        x1=last_day_of_the_month,
        y1=predicted_solar[now.year][now.month] / last_day_of_the_month.day,
        line={"color": "gray", "width": 4}
    )
    fig.write_html("./current-month.html", config={'staticPlot': True})

    print('End loop...')
    sleep(300)
