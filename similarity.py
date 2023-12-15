import json
from pprint import pprint
import pdb

import numpy as np
import pandas as pd
from jinja2 import Template
import os
import matplotlib.pyplot as plt

with open('members.json') as f:
    members = json.load(f)

with open('results/round_1.json') as f:
    results = json.load(f)

scores = {}
member_ids = [member['user']['id'] for member in members]
member_name_lookup = {member['user']['id']: member['user']['name'] for member in members}

if os.path.exists('name_map.json'):
    with open('name_map.json') as f:
        name_map = json.load(f)
    
    for member_id, member_name in member_name_lookup.items():
        if member_name in name_map.keys():
            member_name_lookup[member_id] = name_map[member_name]

for member in members:
    this_member_id = member['user']['id']
    this_member_scores = {}
    other_member_ids = [id for id in member_ids if id != this_member_id]
    for other_member_id in other_member_ids:
        if other_member_id in scores.keys():
            this_member_scores[other_member_id] = scores[other_member_id][this_member_id]
            continue

        this_member_scores[other_member_id] = []

        for song in results['standings']:
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
            this_member_scores[other_member_id].append(song_match)

    scores[this_member_id] = this_member_scores

# rms = []
# weight = []

# for member_scores in scores.values():
#     for other_member_scores in member_scores.values():
#         for vote in other_member_scores:
#             if vote['type'] == 'both_ignore':
#                 weight.append(vote['weight'])
#                 rms.append(vote['crowd_vote_rms'])

# plt.hist(rms, bins=20)
# plt.show()

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


# all_vote_scores = []
# for member_scoreset in scores.values():
#     for other_member_id, other_member_voteset in member_scoreset.items():
#         for vote in other_member_voteset:
#             all_vote_scores.append(vote['score'] if 'score' in vote.keys() else 0)
# plt.hist(all_vote_scores, bins=20)
# plt.show()

# for member_id, member_scores in similarity_scores.items():
#     most_similar_other_member_id = max(member_scores, key=member_scores.get)
#     most_similar_other_member_score = member_scores[most_similar_other_member_id]
#     this_member_name = member_name_lookup[member_id]
#     other_member_name = member_name_lookup[most_similar_other_member_id]
#     print(f'{this_member_name} is most similar to {other_member_name} with a score of {most_similar_other_member_score}')
#     for vote in scores[member_id][most_similar_other_member_id]:
#         print(f'{vote["type"]} {(15-len(vote["type"])) * " "}{vote["weight"]}  {vote["score"]}, {round(vote["crowd_vote_rms"],1)}')

# for member_id, member_scores in similarity_scores.items():
#     print('\n',member_name_lookup[member_id])
#     for other_member_id, other_member_score in sorted(member_scores.items(), key=lambda item: item[1], reverse=True):
#         print(f'   {other_member_score}: {member_name_lookup[other_member_id]}')


similarity_scores_names = {}
for member_id, member_scores in similarity_scores.items():
    similarity_scores_names[member_name_lookup[member_id]] = {}
    for other_member_id, other_member_score in member_scores.items():
        similarity_scores_names[member_name_lookup[member_id]][member_name_lookup[other_member_id]] = other_member_score


sorted_similarity_scores_names = {}
for member, scores in similarity_scores_names.items():
    sorted_scores = sorted(scores.items(), key=lambda x: x[1], reverse=True)
    sorted_similarity_scores_names[member] = [{'name': name, 'score': score} for name, score in sorted_scores]


with open('similarity_table_template.html.jinja2') as file_:
    template = Template(file_.read())

max_score = max(score['score'] for scores in sorted_similarity_scores_names.values() for score in scores)
min_score = min(score['score'] for scores in sorted_similarity_scores_names.values() for score in scores)
rendered_template = template.render(similarity_scores=sorted_similarity_scores_names, max=max_score, min=min_score)


with open('similarity_table.html', 'w+') as file_:
    file_.write(rendered_template)


