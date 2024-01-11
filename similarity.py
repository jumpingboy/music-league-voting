import json
from pprint import pprint
import pdb

import numpy as np
from jinja2 import Template
import os
import os
import json


def calc_similarity_scores(results):
    with open('members.json') as f:
        members = json.load(f)

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

            for song in results:
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

    return sorted_similarity_scores_names


def votes_by_round_array(scale_down_round_1=False):
    result_files = os.listdir('results')

    result_files.sort(key=lambda x: int(x.split('_')[1].split('.')[0]))


    votes_by_round = []
    for file in result_files:
        with open(os.path.join('results', file)) as f:
            results = json.load(f)['standings']
            if scale_down_round_1 and file == 'round_1.json':
                voters = {}
                for song in results:
                    # print(f"https://open.spotify.com/{song['submission']['spotifyUri'].replace('spotify:','').replace(':','/')}")
                    for vote in song['votes']:
                        if vote['weight'] > 0:
                            if vote['voterId'] in [
                                    '269304c187a644419153c0df978977f1',
                                    'f3f58fb8ad33471b87c8e07e1756bbe6',
                                    'd3a42ba3861e4fc6a1dc62b602e61aac',
                                    '676fde1822cb4ca6826a66bc5f9ace91',
                                    '07605f32dc0f47acbb497f6d9d69b3fb',
                                    '4319516bfd3c429d8d1baf51b5425b89',
                                    'c4a142d760d146fa97b0edd56e4fa1f8'
                                ]:
                                if vote['weight'] == 2:
                                    vote['weight'] = 1
                                elif vote['weight'] == 3:
                                    vote['weight'] = 2
                                elif vote['weight'] == 5:
                                    vote['weight'] = 3
                            

                #             if vote['voterId'] not in voters.keys():
                #                 voters[vote['voterId']] = [[vote['weight'], vote['spotifyUri']]]
                #             else:
                #                 voters[vote['voterId']].append([vote['weight'], vote['spotifyUri']])
                # with open('members.json') as f:
                #     members = json.load(f)
                # member_name_lookup = {member['user']['id']: member['user']['name'] for member in members}
                # spotify_song_lookup = {
                #     'spotify:track:16nJl8NnriCJxraco5Zssm': 'Better Git It in Your Soul - Mingus',
                #     'spotify:track:1WOwGVtrVWtV3WW7X4TZoB': 'Public Service Announcement - JAY-Z',
                #     'spotify:track:3tj1cKu9SOnchX6twBKn30': 'Interior People - King Gizzard & The Lizard Wizard',
                #     'spotify:track:3tCCH9aaiKRmwOjvIKq76d': 'Shawty - Remi Wolf',
                #     'spotify:track:3iRfVcDbAhkhxwJuw2cPSv': 'Solid Gone - Pert Near Sandstone',
                #     'spotify:track:4ZReuzjoiFMVWwly2NccJh': 'Limited World - Cory Wong, Caleb Hawley',
                #     'spotify:track:5pvYvvO0IDkuK1FDWPWMXy': 'Apollo\'s Mood - The Olympians',
                #     'spotify:track:6Ln5KqJbn672z67ZowD2pu': 'Camarillo Brillo - Frank Zappa, The Mothers',
                #     'spotify:track:4NXmcUMQauqEtDYDgP0MEi': 'Prélude à l\'après-midi d\'un faune - Debussy',
                #     'spotify:track:0YQznyH9mJn6UTwWFHqy4b': 'El Bandido - Nicolas Jaar',
                #     'spotify:track:5JRMqkR82k2fdDEAim9SCN': 'Peach - Kevin Abstract',
                #     'spotify:track:3iNJUrTTqODoKapRzameCI': 'Hell - Clown Core'
                #     }
                # for voterId, vote_stats in voters.items():
                #     vote_total = 0
                #     for vote_stat in vote_stats:
                #         vote_total += vote_stat[0]
                #     if vote_total > 6:
                #         # print(member_name_lookup[voterId])
                #         print(voterId)
                #         for vote_stat in vote_stats:
                #             pass
                #             # print(vote_stat[0], spotify_song_lookup[vote_stat[1]])


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


def render_similarity_table():
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

    with open('similarity_table_template.html.jinja2') as file_:
        template = Template(file_.read())

    rendered_template = template.render(
        similarity_scores=overall_scores,
        overall_max=overall_max_score,
        overall_min=overall_min_score,
        this_week_max = this_round_max,
        this_week_min = this_round_min,
        top_five = top_five,
        bottom_five = bottom_five,
        this_week=this_round_scores,
        this_week_number = len(votes_by_round_array())
    )


    with open('similarity_table.html', 'w+') as file_:
        file_.write(rendered_template)


if __name__ == "__main__":
    render_similarity_table()
    # vbr = votes_by_round_array(scale_down_round_1=True)
    # voters = {}
    # for round in vbr:
    #     for song in round:
    #         for vote in song['votes']:
    #             if vote['weight'] > 0:
    #                 if vote['voterId'] not in voters.keys():
    #                     voters[vote['voterId']] = [vote['weight']]
    #                 else:
    #                     voters[vote['voterId']].append(vote['weight'])

    # with open ('members.json') as f:
    #     members = json.load(f)
    # member_name_lookup = {member['user']['id']: member['user']['name'] for member in members}
    # if os.path.exists('name_map.json'):
    #     with open('name_map.json') as f:
    #         name_map = json.load(f)
        
    #     for member_id, member_name in member_name_lookup.items():
    #         if member_name in name_map.keys():
    #             member_name_lookup[member_id] = name_map[member_name]
    # for voter, votes in voters.items():
    #     votes.sort()
    #     votes.reverse()
    #     votes = [vote for vote in votes if vote > 1]
    #     print(member_name_lookup[voter], '|',sum(votes),'x', votes)



    # pprint(voters)

