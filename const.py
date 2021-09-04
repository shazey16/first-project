MY_ID = str(5779971)

USER_PAYLOAD = {
    'login': 'stevehayes16@icloud.com',
    'password': '02P3opl3',
    "app": "plfpl-web",
    "redirect_uri": "https://fantasy.premierleague.com/a/login"
}

API_URLS = {
    'LOGIN_URL':"https://users.premierleague.com/accounts/login/",
    'FPL_URL':"https://fantasy.premierleague.com/api/",
    'PLAYER_SUMMARY_SUBURL':"bootstrap-static/",
    'FIXTURES_SUBURL':'fixtures/',
    'MY_TEAM_SUBURL':'my-team/'+MY_ID+'/'
}

HEADERS = {"User-Agent": ""}