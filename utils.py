import requests

import pandas as pd
import numpy as np
import json

from const import API_URLS, HEADERS

def get_static_data():
    r = requests.get(API_URLS['FPL_URL']+API_URLS['PLAYER_SUMMARY_SUBURL'])
    return r.json()

def get_team_mapping(static_data):
    team_mapping = {}

    for team in static_data['teams']:
        team_mapping[team['id']] = team['name']
    
    return team_mapping

def get_position_mapping(static_data):
    position_mapping = {}

    for position in static_data['element_types']:
        position_mapping[position['id']] = position['singular_name']

    return position_mapping

def get_player_mapping(player_data):
    player_mapping = {}

    for _, player in player_data.iterrows():
        player_mapping[player['id']] = player['name'] 

    return player_mapping

def fetch(session, url):
    with session.get(url, headers=HEADERS) as response:
        result = response.json()
        return result