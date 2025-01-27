from flask import Flask, jsonify, request, render_template
# general data science library
import pandas as pd
import numpy as np

# pulling data from APIs, parsing JSON
import requests
import json


# interfacing w/ Cloud storage from python
from google.cloud import storage

# Plotting
import matplotlib.pyplot as plt
import seaborn as sns


app = Flask(__name__)

# Sample MLB data (replace with actual data from the hackathon)
mlb_data = {
    "teams": [
        {"name": "Arizona Diamondbacks", "id": 109},
        {"name": "Atlanta Braves", "id": 144},
        {"name": "Baltimore Orioles", "id": 110},
        {"name": "Boston Red Sox", "id": 111},
        {"name": "Chicago White Sox", "id": 145},
        {"name": "Chicago Cubs", "id": 112},
        {"name": "Cincinnati Reds", "id": 113},
        {"name": "Cleveland Guardians", "id": 114},
        {"name": "Colorado Rockies", "id": 115},
        {"name": "Detroit Tigers", "id": 116},
        {"name": "Houston Astros", "id": 117},
        {"name": "Kansas City Royals", "id": 118},
        {"name": "Los Angeles Angels", "id": 108},
        {"name": "Los Angeles Dodgers", "id": 119},
        {"name": "Miami Marlins", "id": 146},
        {"name": "Milwaukee Brewers", "id": 158},
        {"name": "Minnesota Twins", "id": 142},
        {"name": "New York Yankees", "id": 147},
        {"name": "New York Mets", "id": 121},
        {"name": "Oakland Athletics", "id": 133},
        {"name": "Philadelphia Phillies", "id": 143},
        {"name": "Pittsburgh Pirates", "id": 134},
        {"name": "San Diego Padres", "id": 135},
        {"name": "San Francisco Giants", "id": 137},
        {"name": "Seattle Mariners", "id": 136},
        {"name": "St. Louis Cardinals", "id": 138},
        {"name": "Tampa Bay Rays", "id": 139},
        {"name": "Texas Rangers", "id": 140},
        {"name": "Toronto Blue Jays", "id": 141},
        {"name": "Washington Nationals", "id": 120}
    ],
    "players": [
        {"name": "Aaron Judge", "team": "New York Yankees", "position": "OF"},
        {"name": "Mookie Betts", "team": "Los Angeles Dodgers", "position": "OF"},
        # ... more players
    ]
}


#@title Function to Load Newline Delimited JSON into Pandas DF
def load_newline_delimited_json(url):
    """Loads a newline-delimited JSON file from a URL into a pandas DataFrame.

    Args:
        url: The URL of the newline-delimited JSON file.

    Returns:
        A pandas DataFrame containing the data, or None if an error occurs.
    """
    try:
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes

        data = []
        for line in response.text.strip().split('\n'):
            try:
                data.append(json.loads(line))
            except json.JSONDecodeError as e:
                print(f"Skipping invalid JSON line: {line} due to error: {e}")

        return pd.DataFrame(data)
    except requests.exceptions.RequestException as e:
        print(f"Error downloading data: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

@app.route("/api/teams")
def get_teams():
    return jsonify(mlb_data["teams"])

@app.route("/api/players")
def get_players():
    return jsonify(mlb_data["players"])

def get_team_stats(team_id, season):
    url = f"https://statsapi.mlb.com/api/v1/teams/{team_id}/stats?season={season}" # Example using team endpoint
    response = requests.get(url)

    if response.status_code == 200:
        team_stats = response.json()
        # Extract specific stats like wins, losses, batting average, ERA, stolen bases, etc. from team_stats
        return team_stats.get("stats", [{}])[0].get("splits", [{}])[0].get("stat")  #Navigate JSON to the stats

    else:
        print(f"Error: {response.status_code}")  # Handle API errors
        return None
    

def get_current_season_from_standings():
    url = "https://statsapi.mlb.com/api/v1/standings" # No season parameter, will give current standings.
    response = requests.get(url)

    if response.status_code == 200:
        standings_data = response.json()
        print(standings_data)
        # The season is part of the records returned in the standings data
        # You'll need to examine the response structure to extract it correctly
        return standings_data['records'][0]['season'] # Extract season from first record.
    else:
        # Handle errors
        print(f"Error getting current MLB season from standings: {response.status_code}")
        return None
   


def get_current_mlb_season():
    url = "https://statsapi.mlb.com/api/v1/sports"
    response = requests.get(url)

    if response.status_code == 200:
        sports_data = response.json()
        for sport in sports_data['sports']:
            if sport['id'] == 1:  # MLB's sportId is 1
                return sport['currentSeason']  # Extract currentSeason
    else:
        # Handle errors (e.g., log the error, return a default value)
        print(f"Error getting current MLB Season: {response.status_code}")
        return None
    
@app.route("/api/team_performance")
def get_team_performance():
    df = fetch_mlb_team_performance_data()
    if df is not None:
        return jsonify(df.to_dict(orient="records"))
    return jsonify({"error": "Failed to fetch data"}), 500

def fetch_mlb_team_performance_data():
    url = "https://statsapi.mlb.com/api/v1/teams/stats"
    params = {
        "season": "2024",
        "group": "hitting,pitching,fielding",
        "stats": "season"
    }
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        teams_stats = data.get("stats", [])
        print(teams_stats)
        return pd.DataFrame(teams_stats)
    except requests.exceptions.RequestException as e:
        print(f"Error downloading data: {e}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred: {e}")
        return None

# Function to get team stats from JSON file
def get_team_stats_from_json(team_id):
    with open('data/2024.json', 'r') as file:
        data = json.load(file)
        team_stats = {}
        for group in data:
            
            group_name =group["group"]["displayName"]
            print(group_name)
            for split in group.get("splits", []):
                print(split)
                if split["team"]["id"] == team_id:
                    team_stats[group_name] = split["stat"]
        return team_stats

@app.route("/", methods=["GET", "POST"])
def compare_teams():
    if request.method == "POST":
        team1 = request.form.get("team1")
        team2 = request.form.get("team2")
        team1_name = next((team["name"] for team in mlb_data["teams"] if team["id"] == int(team1)), None)
        team2_name = next((team["name"] for team in mlb_data["teams"] if team["id"] == int(team2)), None)
        team1_logo = f'https://www.mlbstatic.com/team-logos/{team1}.svg'
        team2_logo = f'https://www.mlbstatic.com/team-logos/{team2}.svg'

        team1_stats = get_team_stats_from_json(team1)
        team2_stats = get_team_stats_from_json(team2)
       
        # Perform comparison logic here (example below)
        comparison_result = f"Comparing {team1_name} vs {team2_name}" 
        comparison_result += f"{team1_name} Stats: {team1_stats}\n"
        comparison_result += f"{team2_name} Stats: {team2_stats}"
        # return render_template("comparison.html", result=comparison_result, teams=mlb_data["teams"]) # Pass teams to template
        return render_template("comparison.html", result=comparison_result, team1=team1_name, team2=team2_name, team1_logo=team1_logo, team2_logo=team2_logo, teams=mlb_data["teams"])
    return render_template("comparison.html", teams=mlb_data["teams"]) # Pass teams to template

if __name__ == "__main__":
    app.run(debug=True)
