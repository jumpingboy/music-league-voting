import json
from pprint import pprint
import pdb

import numpy as np
from jinja2 import Template
import os
import os
import json

default_league_json_path = os.path.join('leagues','default_league_info.json')
if os.path.exists(default_league_json_path):
    with open(default_league_json_path) as f:
        league_name = json.loads(f.read())['league_name']
        league_folderpath = os.path.join('leagues',league_name)
else:
    league_folders = [item_name for item_name in os.listdir('leagues') if os.path.isdir(os.path.join('leagues', item_name))]
    if len(league_folders) > 1:
        league_choices = '\n'.join([f'{i+1}: {league_name}' for i, league_name in enumerate(league_folders)])
        league_choice = input(f'Which league would you like to generate a table for? {league_choices}\nType a number, then hit enter')
        league_folderpath = os.path.join('leagues', league_folders[int(league_choice) - 1])
    else:
        league_folderpath = os.path.join('leagues', league_folders[0])


def calc_similarity_scores(results):
    members_json_path = os.path.join(league_folderpath, 'members.json')
    
    with open(members_json_path) as f:
        members = json.load(f)

    scores = {}
    member_ids = [member['user']['id'] for member in members]
    member_name_lookup = {member['user']['id']: member['user']['name'] for member in members}

    name_map = None
    name_map_json_path = os.path.join(league_folderpath, 'name_map.json')
    if os.path.exists(name_map_json_path):
        with open(name_map_json_path, 'r') as f:
            name_map = json.loads(f.read())

        for member_id, member_name in member_name_lookup.items():
            if member_name in name_map.keys():
                member_name_lookup[member_id] = name_map[member_name]

    track_lookup = None
    tracks_json_path = os.path.join(league_folderpath, 'tracks.json')
    if os.path.exists(tracks_json_path):
        with open(tracks_json_path) as f:
            track_lookup = json.load(f)
    for member in members:
        this_member_id = member['user']['id']
        this_member_scores = {}
        other_member_ids = [id for id in member_ids if id != this_member_id]
        for other_member_id in other_member_ids:
            if other_member_id in scores.keys():
                this_member_scores[other_member_id] = scores[other_member_id][this_member_id]
                continue

            this_member_scores[other_member_id] = []

            for song in results:
                def parse_vote_stats_for_song(this_member_id, other_member_id, song):
                    votes_by_id = {vote['voterId']: vote['weight'] for vote in song['votes']}
                    song_match = {}
                    submitter_id = song['submission']['submitterId']
                    this_member_voted = this_member_id in votes_by_id.keys()
                    this_member_vote = votes_by_id[this_member_id] if this_member_voted else 0
                    other_member_voted = other_member_id in votes_by_id.keys()
                    other_member_vote = votes_by_id[other_member_id] if other_member_voted else 0
                    crowd_votes = [vote['weight'] for vote in song['votes'] if vote['voterId'] not in [this_member_id, other_member_id]]
                    
                    def crowd_rms(crowd_votes, pair_votes):
                        crowd_ignorers_count = len(member_ids) - 2 - len(crowd_votes)
                        if len(pair_votes) == 1:
                            crowd_ignorers_count += 1
                        crowd_votes += [0] * crowd_ignorers_count
                        crowd_vote_diffs = [abs(vote - pair_vote) for vote in crowd_votes for pair_vote in pair_votes]
                        return np.sqrt(np.square(crowd_vote_diffs).mean())
                    
                    if submitter_id == this_member_id:
                        song_match['type'] = 'submitter'
                        song_match['weight'] = other_member_vote
                        song_match['crowd_vote_rms'] = crowd_rms(crowd_votes, [other_member_vote])
                    elif submitter_id == other_member_id:
                        song_match['type'] = 'submitter'
                        song_match['weight'] = this_member_vote
                        song_match['crowd_vote_rms'] = crowd_rms(crowd_votes, [this_member_vote])
                    else:
                        this_member_upvoted = this_member_vote > 0
                        other_member_upvoted = other_member_vote > 0
                        song_match['crowd_vote_rms'] = crowd_rms(crowd_votes, [this_member_vote, other_member_vote])
                        
                        if this_member_voted and other_member_voted:
                            if this_member_upvoted and other_member_upvoted:
                                song_match['type'] = 'both_up'
                                song_match['weight'] = votes_by_id[this_member_id] + votes_by_id[other_member_id]
                                song_match['diff'] = abs(votes_by_id[this_member_id] - votes_by_id[other_member_id])
                            elif not this_member_upvoted and not other_member_upvoted:
                                song_match['type'] = 'both_down'
                                song_match['weight'] = -1
                            else:
                                song_match['type'] = 'up_down'
                                song_match['weight'] = abs(votes_by_id[this_member_id] - votes_by_id[other_member_id])
                        elif not this_member_voted and not other_member_voted:
                            song_match['type'] = 'both_ignore'
                            song_match['weight'] = 0
                        else:
                            song_match['type'] = 'in_out'
                            song_match['weight'] = votes_by_id[this_member_id] if this_member_voted else votes_by_id[other_member_id]
                    if track_lookup:
                        song_match['song_info'] = track_lookup[song['submission']['spotifyUri']]
                    return song_match
                
                song_vote_stats = parse_vote_stats_for_song(this_member_id, other_member_id, song)
                this_member_scores[other_member_id].append(song_vote_stats)

        scores[this_member_id] = this_member_scores

    similarity_scores = {}


    for this_member_id, member_scores in scores.items():
        similarity_scores[this_member_id] = {}
        for other_member_id, other_member_scores in member_scores.items():
            if other_member_id in similarity_scores.keys():
                similarity_scores[this_member_id][other_member_id] = similarity_scores[other_member_id][this_member_id]
                continue
            member_score = 0
            for vote in other_member_scores:
                vote_score = 0
                # weight 1 to 10
                against_the_crowd_bonus = vote['crowd_vote_rms']
                if vote['type'] == 'submitter' and vote['weight'] > 0:
                    vote_score += np.sqrt(vote['weight'] - 1) * 1.2 + 3 + against_the_crowd_bonus
                # weight 1 to 10
                elif vote['type'] == 'both_up':
                    vote_score += np.sqrt(vote['weight'] - 1 - vote['diff']/1.5) * 1.4 + 2 + against_the_crowd_bonus
                elif vote['type'] == 'both_down':
                    vote_score += 5 + (against_the_crowd_bonus/3)
                elif vote['type'] == 'both_ignore':
                    vote_score += 1 + against_the_crowd_bonus

                elif vote['type'] == 'submitter' and vote['weight'] == 0:
                    vote_score += -2
                elif vote['type'] == 'submitter' and vote['weight'] < 0:
                    vote_score += -5
                # weight 2 to 11
                elif vote['type'] == 'up_down':
                    vote_score += np.sqrt(vote['weight'] - 1) * -1.4 - 3

                elif vote['type'] == 'in_out':
                    if vote['weight'] < 1:
                        vote_score += -1
                    else:
                        vote_score += np.sqrt(vote['weight'] - 1) * -1.2 - 1
                vote['score'] = round(vote_score,1)
                member_score += vote_score

            similarity_scores[this_member_id][other_member_id] = round(member_score, 1)

    similarity_scores_names = {}
    for member_id, member_scores in similarity_scores.items():
        similarity_scores_names[member_name_lookup[member_id]] = {}
        for other_member_id, other_member_score in member_scores.items():
            similarity_scores_names[member_name_lookup[member_id]][member_name_lookup[other_member_id]] = other_member_score


    sorted_similarity_scores_names = {}
    for member, scores in similarity_scores_names.items():
        sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        sorted_similarity_scores_names[member] = [{'name': name, 'score': score} for name, score in sorted_scores]

    return sorted_similarity_scores_names


def votes_by_round_array():
    result_files = os.listdir(f'{league_folderpath}/results')

    result_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))


    votes_by_round = []
    for file in result_files:
        with open(os.path.join(f'{league_folderpath}/results', file)) as f:
            results = json.load(f)['standings']

            votes_by_round.append(results)

    return votes_by_round


def cumulative_and_last_round_scores():
    cumulative_results = sum(votes_by_round_array(), [])
    last_round_results = votes_by_round_array()[-1]

    return calc_similarity_scores(cumulative_results), calc_similarity_scores(last_round_results)


def cumulative_scores_by_round_array():
    cumulative_results_by_round = []
    for round_results in votes_by_round_array():
        if not cumulative_results_by_round:
            cumulative_results_by_round.append(round_results)
        else:
            cumulative_results_by_round.append(cumulative_results_by_round[-1] + round_results)

    return [calc_similarity_scores(results_through_round) for results_through_round in cumulative_results_by_round]


def render_similarity_table(league_folderpath=league_folderpath):
    overall_scores, this_round_scores = cumulative_and_last_round_scores()

    def top_and_bottom(similarity_scores):
        all = []
        done_members = []

        for member, scores in similarity_scores.items():
            for score in scores:
                if score['name'] in done_members:
                    continue
                all.append({'member_a':member, 'member_b': score['name'], 'score': float(score['score'])})
            done_members.append(member)
        all.sort(key=lambda x: x['score'], reverse=True)

        top_five = all[:5]
        bottom_five_worst_first = all[-5:]
        bottom_five_worst_first.sort(key=lambda x: x['score'])
        return top_five, bottom_five_worst_first
    
    top_five, bottom_five = top_and_bottom(overall_scores)

    def max_min(results):
        max_score = float(max(score['score'] for scores in results.values() for score in scores))
        min_score = float(min(score['score'] for scores in results.values() for score in scores))
        return max_score, min_score

    overall_max_score, overall_min_score = max_min(overall_scores)
    this_round_max, this_round_min = max_min(this_round_scores)

    with open('table_template.html.jinja2') as file_:
        template = Template(file_.read())

    this_week_number = len(votes_by_round_array())

    rendered_template = template.render(
        similarity_scores=overall_scores,
        overall_max=overall_max_score,
        overall_min=overall_min_score,
        this_week_max = this_round_max,
        this_week_min = this_round_min,
        top_five = top_five,
        bottom_five = bottom_five,
        this_week=this_round_scores,
        this_week_number = this_week_number
    )

    table_output_folderpath = f'{league_folderpath}/table_output'
    if not os.path.exists(table_output_folderpath):
        os.mkdir(table_output_folderpath)


    with open(os.path.join(table_output_folderpath,f'round_{this_week_number}_similarity_table.html'), 'w+') as file_:
        file_.write(rendered_template)


if __name__ == "__main__":
    render_similarity_table()

