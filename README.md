# Music League Voting Similarity
Compare voting similarity of all members of a [Music League](https://app.musicleague.com/) and generate a simple HTML output

![Sample HTML output](./images/example_table.jpg)

### Python Setup:
1. Clone the repo
    ```
    git clone https://github.com/jumpingboy/music-league-voting.git
    ```
2. Install [poetry](https://python-poetry.org/docs/#installation) and [pyenv](https://github.com/pyenv/pyenv#installation) (or your python version manager of choice)
3. Install the python version for this repo, tell poetry where to find it, install dependencies, and launch a shell in the environment you just created
    ```
    pyenv install 3.11:latest
    poetry env use <path_to_python>
    poetry install
    poetry shell
    ```
4. Poetry tip: To set your poetry virtual environment as the Python interpreter in your IDE, you usually need the full path to the Python version in your virtual environment. When you run `poetry shell` you will see something like 
    `/Users/bob-loblaw/Library/Caches/pypoetry/virtualenvs/music-league-voting-1hfJBfdf-py3.9/bin/activate`
    Change `activate` to `python`, and that's your path.
    You can also find the path to your virtualenv with `poetry show -v`, then just add `/bin/python` to the end, and that's your path.

### Import Data:
1. Create a folder called `results` and an empty file inside called `round_1.json` 
2. Create an empty `members.json` file in the root directory of this repo
3. Log into Music League and click on the Results page for Round 1 of your league
4. Open the developer console in your browser. In the Network tab, look for calls to `members` and `results` endpoints
![Network Tab Screenshot](./images/network_tab_screenshot.jpg)
5. Copy the `members` response into `members.json`
6. Copy the `results` response in `results/round_1.json`
7. Optional: If you want to translate some members' Music League display names into shorter or more familiar names, copy `name_map_example.json` to a new file called `name_map.json` and fill it out accordingly.

