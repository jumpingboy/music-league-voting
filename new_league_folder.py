import pdb
import os
import shutil
import time


league_name = input("Enter the name of your league: ")
league_name = league_name if league_name else f"league-{int(time.time())%1000000}"
league_folderpath = os.path.join("leagues",league_name)
name_map_json_path = os.path.join(league_folderpath, "name_map.json")
league_settings_json_path = os.path.join(league_folderpath, "league_settings.json")
if not os.path.exists(f"leagues"):
    os.mkdir("leagues")
if not os.path.exists(league_folderpath):
    os.mkdir(league_folderpath)
if not os.path.exists(name_map_json_path):
    shutil.copy('name_map_example.json', name_map_json_path)
if not os.path.exists(league_settings_json_path):
    shutil.copy('league_settings_example.json', league_settings_json_path)

print(f"\nCreated empty league folder and placeholder files at {league_folderpath}.\nFollow instructions in README.md to download results manually.\n")