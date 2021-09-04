import requests
import json
import pandas as pd
import numpy as np
import csv
from datetime import datetime
from bs4 import BeautifulSoup
from urllib.request import urlopen
import utils
from const import API_URLS, USER_PAYLOAD


class FPL:
    def __init__(self):
        self.session = requests.Session()
        self.login()
        self.pull_all_data()

    def pull_all_data(self):
        self.all_data = utils.get_static_data()
        self.get_team_data()
        self.get_fixture_data()
        self.update_team_data_performance()
        self.get_player_data()
        self.get_my_team_data()
        

    def get_fixture_data(self):
        fixtures_columns = [
            'kickoff_time',
            'team_h',
            'team_a',
            'team_h_score',
            'team_a_score',
            'team_h_difficulty',
            'team_a_difficulty',
            'event'
        ]
        r = requests.get(API_URLS['FPL_URL']+API_URLS['FIXTURES_SUBURL'])
        self.fixture_data = pd.DataFrame(r.json())
        self.fixture_data['team_h'] = self.fixture_data['team_h'].map(utils.get_team_mapping(self.all_data))
        self.fixture_data['team_a'] = self.fixture_data['team_a'].map(utils.get_team_mapping(self.all_data))
        self.fixture_data = self.fixture_data[fixtures_columns]
        self.fixture_data['kickoff_time'] = pd.to_datetime(self.fixture_data['kickoff_time'])

    def get_team_data(self):
        team_data_columns = [
            'name',
            'position',
            'points',
            'played',
            'win',
            'loss',
            'draw',
            'strength',
            'avg_strength'
        ]
        self.team_data = pd.DataFrame(self.all_data['teams'])
        self.team_data['avg_strength'] = (self.team_data['strength_overall_home'] + self.team_data['strength_overall_away']) / 2
        self.team_data = self.team_data[team_data_columns]
        self.team_data.sort_values(by='position', inplace=True)
    
    def get_my_team_data(self):
        my_team_data_columns = [
            'name',
            'position_y',
            'substitute',
            'team',
            'form',
            'total_points',
            'points_per_game',
            'value',
            'now_cost',
            'chance_of_playing_this_round',
            'minutes'
        ]
        self.my_team_data = pd.DataFrame(utils.fetch(
            self.session, API_URLS['FPL_URL']+API_URLS['MY_TEAM_SUBURL'])['picks']
            )
        self.my_team_data = self.my_team_data.merge(self.player_data, 
            left_on='element',
            right_on='id',
            how='left'
        )
        self.my_team_data['substitute'] = np.where(self.my_team_data['position_x']<=11,0,1)
        self.my_team_data = self.my_team_data[my_team_data_columns]
        self.my_team_data['opponents'] = self.my_team_data['team'].map(self.get_this_gameweeks_opponents())
        self.my_team_data['next_opponents'] = self.my_team_data['team'].map(self.get_next_gameweeks_opponents())

        
    def get_player_data(self):
        player_columns = [
            'name',
            'position',
            'team',
            'minutes',
            'form',
            'now_cost',
            'total_points',
            'points_per_game',
            'chance_of_playing_this_round',
            'ict_index_rank',
            'id'
        ]
        self.player_data = pd.DataFrame(self.all_data['elements'])
        self.player_data['name'] = self.player_data['first_name'] + ' ' + self.player_data['second_name']
        self.player_data['team'] = self.player_data['team'].map(utils.get_team_mapping(self.all_data))
        self.player_data['position'] = self.player_data['element_type'].map(utils.get_position_mapping(self.all_data))
        self.player_data = self.player_data[player_columns]
        self.player_data['value'] = self.player_data['total_points'] / self.player_data['now_cost']
        self.player_data = self.player_data.merge(
            self.team_data[['name','played']], left_on='team', right_on='name', suffixes=("","_team")
            )
        self.player_data.rename(columns={'played':'played_team'}, inplace=True)
        self.player_data.drop(columns=['name_team'], inplace=True)
        self.player_data['minutes_per_game'] = self.player_data['minutes'] / self.player_data['played_team']
        self.player_data['form'] = self.player_data['form'].astype(float)

    def get_match_outcomes(self):
        self.fixture_data['team_h_win'] = np.where(
            self.fixture_data['team_h_score']>self.fixture_data['team_a_score'],
            1,
            0)
        self.fixture_data['team_a_win'] = np.where(
            self.fixture_data['team_a_score']>self.fixture_data['team_h_score'],
            1,
            0)

        self.fixture_data['team_h_points'] = 0
        self.fixture_data['team_a_points'] = 0

        self.fixture_data.loc[self.fixture_data['team_h_win']>self.fixture_data['team_a_win'],'team_h_points'] = 3
        self.fixture_data.loc[self.fixture_data['team_h_win']==self.fixture_data['team_a_win'],'team_h_points'] = 1
        self.fixture_data.loc[self.fixture_data['team_h_win']<self.fixture_data['team_a_win'],'team_h_points'] = 0

        self.fixture_data.loc[self.fixture_data['team_a_win']>self.fixture_data['team_h_win'],'team_a_points'] = 3
        self.fixture_data.loc[self.fixture_data['team_a_win']==self.fixture_data['team_h_win'],'team_a_points'] = 1
        self.fixture_data.loc[self.fixture_data['team_a_win']<self.fixture_data['team_h_win'],'team_a_points'] = 0

    def update_team_data_performance(self):
        self.get_match_outcomes()
        now = datetime.now()
        current_time = now.strftime("%H:%M:%S")  
        for team in self.team_data['name'].unique():
            fixtures = self.fixture_data[(self.fixture_data['kickoff_time']<current_time)&((self.fixture_data['team_h']==team)|(self.fixture_data['team_a']==team))].copy()
            fixtures['home'] = fixtures['team_h'] == team
            fixtures['away'] = fixtures['team_a'] == team

            games_played = fixtures.shape[0]
            games_won = np.where((fixtures['team_h_points']==3)&(fixtures['home']),1,0).sum()
            games_won += np.where((fixtures['team_a_points']==3)&(fixtures['away']),1,0).sum()
            games_drawn = np.where((fixtures['team_h_points']==1)&(fixtures['home']),1,0).sum()
            games_drawn += np.where((fixtures['team_a_points']==1)&(fixtures['away']),1,0).sum()
            games_lost = np.where((fixtures['team_h_points']==0)&(fixtures['home']),1,0).sum()
            games_lost += np.where((fixtures['team_a_points']==0)&(fixtures['away']),1,0).sum()
            points = 3 * games_won + games_drawn
            
            self.team_data.loc[self.team_data['name']==team,['played']] = games_played
            self.team_data.loc[self.team_data['name']==team,['points']] = points
            self.team_data.loc[self.team_data['name']==team,['win']] = games_won
            self.team_data.loc[self.team_data['name']==team,['loss']] = games_lost
            self.team_data.loc[self.team_data['name']==team,['draw']] == games_drawn

        self.team_data['position'] = self.team_data['points'].rank(ascending=False)
        self.team_data.sort_values(by='position', ascending=True, inplace=True)
        self.team_data.reset_index(inplace=True, drop=True)

    def get_current_gameweek(self):
        self.current_gameweek = None
        for event in self.all_data['events']:
            if event['is_current']:
                self.current_gameweek = event['id']
            
            if self.current_gameweek:
                break
        
        if not self.current_gameweek:
            self.current_gameweek = 0

    def get_current_gameweeks_fixtures(self):
        self.get_current_gameweek()
        return self.fixture_data[self.fixture_data['event'] == self.current_gameweek]

    def get_teams_playing_this_week(self):
        teams = []
        i = 0
        for _, row in self.get_current_gameweeks_fixtures().iterrows():
            teams.append([row['team_h'],row['team_a']])
            i+=1
        
        return sorted(teams)

    def get_next_gameweeks_fixtures(self):
        self.get_current_gameweek()
        return self.fixture_data[self.fixture_data['event'] == self.current_gameweek + 1]

    def get_teams_playing_next_week(self):
        teams = []
        i = 0
        for _, row in self.get_next_gameweeks_fixtures().iterrows():
            teams.append([row['team_h'],row['team_a']])
            i+=1
        
        return sorted(teams)

    def get_this_gameweeks_opponents(self):
        opponents = {}
        for team in self.get_teams_playing_this_week():
            opponents[team[0]] = team[1]
            opponents[team[1]] = team[0]
        return opponents
    
    def get_next_gameweeks_opponents(self):
        opponents = {}
        for team in self.get_teams_playing_next_week():
            opponents[team[0]] = team[1]
            opponents[team[1]] = team[0]
        return opponents

    def show_good_players(self, **kwargs):
        filter1 = self.player_data['chance_of_playing_this_round'].isna()
        for k,v in kwargs.items():
            filter1 &= self.player_data[k] > v
            continue

        return self.player_data[filter1]

    def login(self):
        self.session.post(API_URLS['LOGIN_URL'], data=USER_PAYLOAD)
        
        

