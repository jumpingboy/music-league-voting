import pdb
import os
import json
import shutil

import browser_cookie3
import requests

retries = 0
valid_choice = False
choices_string = "\n".join(["1. Firefox", "2. Chrome", "3. I'll download results manually, set up a league folder for me."])
while retries < 3 and not valid_choice:
    retries += 1
    choice = input(f"\nWhich browser have you used to log into MusicLeague?\n\n{choices_string}\n\nType a number, then hit enter (or type ctrl + c to exit): ")
    if choice.strip() == '1':
        valid_choice = True
        cookie_jar = browser_cookie3.firefox(domain_name=".app.musicleague.com")
    elif choice.strip() == '2':
        valid_choice = True
        cookie_jar = browser_cookie3.chrome(domain_name=".app.musicleague.com")
        if not cookie_jar:
            cwd = os.getcwd()
            if "C:\\Users" in cwd:
                user_name = cwd.split('\\', 3)[2]
                for profile_num in range(1, 7):
                    filepath_to_try = f"C:\\Users\\{user_name}\\AppData\\Local\\Google\\Chrome\\User Data\\{profile_num}\\Network\\Cookies"
                    if os.path.exists(filepath_to_try):
                        cookie_jar = browser_cookie3.chrome(domain_name=".musicleague.com", cookie_file=filepath_to_try)
                        if cookie_jar:
                            break
            elif "/Users/" in cwd:
                user_name = cwd.split('/', 3)[2]
                for profile_num in range(1, 7):
                    filepath_to_try = f"/Users/{user_name}/Library/Application Support/Google/Chrome/Profile {profile_num}/Cookies"
                    if os.path.exists(filepath_to_try):
                        cookie_jar = browser_cookie3.chrome(domain_name=".musicleague.com", cookie_file=filepath_to_try)
                        if cookie_jar:
                            break
    elif choice.strip() == '3':
        valid_choice = True
        league_name = input("What is the name of this league?: ")
        import time
        league_name = league_name if league_name else f"league-{int(time.time())%1000000}"
        league_folderpath = os.path.join("leagues",league_name)
        members_json_path = os.path.join(league_folderpath, "members.json")
        name_map_json_path = os.path.join(league_folderpath, "name_map.json")
        tracks_json_path = os.path.join(league_folderpath, "tracks.json")
        results_folderpath = os.path.join(league_folderpath, "results")
        if not os.path.exists(f"leagues"):
            os.mkdir("leagues")
        if not os.path.exists(league_folderpath):
            os.mkdir(league_folderpath)
        if not os.path.exists(members_json_path):
            with open(members_json_path, 'w') as f:
                pass
        if not os.path.exists(name_map_json_path):
            shutil.copy('name_map_example.json', name_map_json_path)
        if not os.path.exists(results_folderpath):
            os.mkdir(results_folderpath)
            with open(os.path.join(results_folderpath, 'round_1.json'), 'w') as f:
                pass
        print(f"\nCreated empty league folder and placeholder files at {league_folderpath}.\nFollow instructions in README.md to download results manually.\n")
        exit()

    else:
        if retries >= 3:
            print("\nI didn't understand that input, exiting.\n")
            exit()
        else:
            print("\nI didn't understand that input, please try again and enter a number.\n")

if not cookie_jar:
    if choice == 1:
        print(f"No MusicLeague cookies found in Firefox.\nTry logging into MusicLeague in Chrome and try again.\n")
    elif choice == 2:
        print(f"No MusicLeague cookies found in any Chrome profiles.\nTry logging into MusicLeague in Firefox and try again.\n")
    exit()

headers = {'Content-Type': 'application/json'}

league_id = None
league_name = None
default_league_info_path = os.path.join('leagues', 'default_league_info.json')
if os.path.exists(default_league_info_path):
    with open(default_league_info_path, 'r') as f:
        try:
            league_info = json.loads(f.read())
            league_id = league_info['league_id']
            league_name = league_info['league_name']
        except:
            pass

if not league_id:
    me_url = "https://app.musicleague.com/api/v1/me"
    me_response = requests.get(me_url, cookies=cookie_jar, headers=headers)
    try:
        user_id = me_response.json()['id']
    except:
        print("Seems like the cookie wasn't valid. Try logging into MusicLeague in the other browser and try again.\n")
        exit()

    leagues_url = f"https://app.musicleague.com/api/v1/users/{user_id}/leagues"
    leagues_response = requests.get(leagues_url, cookies=cookie_jar, headers=headers)
    leagues = leagues_response.json()
    league_ids = [league['id'] for league in leagues]
    if len(league_ids) > 1:
        league_names = [league['name'] for league in leagues]
        league_choices_str = "\n".join([f"{i+1}. {name}" for i, name in enumerate(league_names)])
        league_choice = input(f"\nWhich league do you want to download results for?\n{league_choices_str}\n(Type the number, then hit enter): ")
        league_id = league_ids[int(league_choice)-1]
        league_name = league_names[int(league_choice)-1]
        print("This will be your default league for future downloads. To change your default league, delete the 'default_league_info.json' file inside the 'leagues' folder.")
        with open(default_league_info_path, 'w+') as f:
            f.write(json.dumps({'league_id': league_id, 'league_name': league_names[int(league_choice)-1]}))

    else:
        league_id = league_ids[0]
        league_name = leagues[0]['name']

rounds_url = f"https://app.musicleague.com/api/v1/leagues/{league_id}/rounds"
rounds_response = requests.get(rounds_url, cookies=cookie_jar, headers=headers)
rounds = rounds_response.json()
round_ids = [round['id'] for round in rounds if round['status'] == 'COMPLETE']

def track_lookup(tracks):
    def artist_names(track):
        return ', '.join([artist['name'] for artist in track['artists']])
    track_lookup = {track['uri']: {
            'title': track['name'],
            'artist': artist_names(track)
            } for track in tracks}
    return track_lookup


cwd = os.getcwd()
if os.path.exists(f'{cwd}/leagues/{league_name}/results'):
    downloaded_rounds_count = len(os.listdir(f'{cwd}/leagues/{league_name}/results'))
    if len(os.listdir(f'{cwd}/leagues/{league_name}/results')) == len(round_ids):
        print(f"\nResults already up to date.\n(To re-download any files or folders inside 'leagues', delete them and run this script again.)")
    else:
        new_rounds = round_ids[downloaded_rounds_count-1:]
        new_track_ids = []
        for round_num, round in enumerate(new_rounds, downloaded_rounds_count):
            results_url = f"https://app.musicleague.com/api/v1/leagues/{league_id}/rounds/{round}/results"
            results_response = requests.get(results_url, cookies=cookie_jar, headers=headers)
            results = results_response.json()
            track_ids = [song['submission']['spotifyUri'].replace('spotify:track:','') for song in results['standings']]
            new_track_ids += track_ids
            with open(f"leagues/{league_name}/results/round_{round_num}.json", 'w+') as f:
                f.write(json.dumps(results))
        if os.path.exists(f"{cwd}/leagues/{league_name}/tracks.json"):
            tracks_url = f"https://app.musicleague.com/api/v1/tracks?ids={','.join(new_track_ids)}"
            tracks_response = requests.get(tracks_url, cookies=cookie_jar, headers=headers)
            tracks = tracks_response.json()['tracks']
            lookup = track_lookup(tracks)
            with open(f"leagues/{league_name}/tracks.json", 'r') as f:
                existing_lookup = json.loads(f.read())
            lookup.update(existing_lookup)
            with open(f"leagues/{league_name}/tracks.json", 'w') as f:
                f.write(json.dumps(lookup, indent=4))
        else:
            pass #If tracks.json doesn't exist, all tracks will be fetched at once at the end of the script


if not os.path.exists(f"{cwd}/leagues/"):
    os.mkdir("leagues")
if not os.path.exists(f"{cwd}/leagues/{league_name}"):
    os.mkdir(f"leagues/{league_name}")
if not os.path.exists(f"{cwd}/leagues/{league_name}/results"):
    os.mkdir(f"leagues/{league_name}/results")
results_folderpath = f"{cwd}/leagues/{league_name}/results"

if not os.listdir(f"{cwd}/leagues/{league_name}/results"):
    print(f"\nDownloading results for {league_name} for all rounds...")
    for round_num, round_id in enumerate(round_ids):
        results_url = f"https://app.musicleague.com/api/v1/leagues/{league_id}/rounds/{round_id}/results"
        results_response = requests.get(results_url, cookies=cookie_jar, headers=headers)
        results = results_response.json()
        with open(f"leagues/{league_name}/results/round_{round_num+1}.json", 'w+') as f:
            f.write(json.dumps(results))
    print("Results downloaded.")
if not os.path.exists(f"{cwd}/leagues/{league_name}/members.json"):
    print(f"\nDownloading members for {league_name}...")
    members_url = f"https://app.musicleague.com/api/v1/leagues/{league_id}/members"
    members_response = requests.get(members_url, cookies=cookie_jar, headers=headers)
    members = members_response.json()
    with open(f"leagues/{league_name}/members.json", 'w+') as f:
        f.write(json.dumps(members))
    print("Members downloaded.")
if not os.path.exists(f"{cwd}/leagues/{league_name}/name_map.json"):
    print(f"\nGenerating name map for {league_name}...")
    with open(f"leagues/{league_name}/members.json", 'r') as f:
        members = json.loads(f.read())
        name_map = {member['user']['name']: member['user']['name'] for member in members}
    with open(f"leagues/{league_name}/name_map.json", 'w+') as f:
        f.write(json.dumps(name_map, indent=4))
    print("Name map generated.")
if not os.path.exists(f"{cwd}/leagues/{league_name}/tracks.json"):
    track_ids = []
    print(f"\nDownloading track names for {league_name}...")
    result_files = os.listdir(results_folderpath)

    result_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))

    for file in result_files:
        with open(os.path.join(results_folderpath, file)) as f:        
            results = json.loads(f.read())
            track_ids += [song['submission']['spotifyUri'].replace('spotify:track:','') for song in results['standings']]
                
    track_url = f"https://app.musicleague.com/api/v1/tracks?ids={','.join(track_ids)}"
    track_response = requests.get(track_url, cookies=cookie_jar, headers=headers)
    tracks = track_response.json()['tracks']
    lookup = track_lookup(tracks)
    with open(f"leagues/{league_name}/tracks.json", 'w+') as f:
        f.write(json.dumps(lookup, indent=4))
    print("Track names downloaded.")

print("\n")