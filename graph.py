import json
import time
import pdb
import os
import math

import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd
from matplotlib.animation import FuncAnimation, FFMpegWriter

from similarity import cumulative_scores_by_round_array


def positions(similarity_scores, start_pos=None):
    min_score = min(score['score'] for scores in similarity_scores.values() for score in scores)
    max_score = max(score['score'] for scores in similarity_scores.values() for score in scores)
    score_range = max_score - min_score

    G = nx.Graph()

    for member_name, member_scores in similarity_scores.items():
        for score_dict in member_scores:
            optimal_distance = round((-1 * (score_dict['score'] - min_score + 0.1)) + score_range + 2.1, 2)
            G.add_edge(member_name, score_dict['name'], weight=optimal_distance)

    pos = nx.kamada_kawai_layout(G, dim=2, pos=start_pos)
    return pos


def graph(positions, round_num):
    fig, ax = plt.subplots(1, figsize=(15, 10))

    for node_name, (x, y) in positions.items():
        node_color = '#6fd7f8'

        ax.scatter(x, y, c=node_color, label=node_name, s=1800)
        ax.text(x, y, node_name, color='black', fontsize=12, ha='center', va='center')

    ax.axis('off')
    ax.set_title(f'Round {round_num}')

    plt.show()
    return positions


def make_animation(pos_by_round):
    fig, ax = plt.subplots(1, figsize=(15, 10))

    all_values = []
    for pos in pos_by_round:
        all_values.extend(pos.values())
    min_x = min(x for x, _ in all_values)
    max_x = max(x for x, _ in all_values)
    min_y = min(y for _, y in all_values)
    max_y = max(y for _, y in all_values)
    range_x = max_x - min_x
    range_y = max_y - min_y
    ax.set_xlim(min_x - range_x * 0.08, max_x + range_x * 0.08)
    ax.set_ylim(min_y - range_y * 0.08, max_y + range_y * 0.08)

    x_array = []
    y_array = []

    text_artists = {}

    for node_name, (x, y) in pos_by_round[0].items():
        x_array.append(x)
        y_array.append(y)
        text_artists[node_name] = ax.text(x, y, node_name, color='black', fontsize=24, ha='center', va='center')

    node_color = '#6fd7f8'
    ax.axis('off')
    sc = ax.scatter(x_array, y_array, c=node_color, label=node_name, s=6000)
    text_artists['title_artist'] = ax.set_title(f'Round 1', fontsize=48)
    fig.tight_layout()
    
    # If there are more than 3 rounds, the first 60% of the rounds will be shown for less time than more recent rounds since most voters will have already seen the videos of the early rounds in previous weeks.
    num_total_rounds = len(pos_by_round)
    num_recent_rounds = math.ceil(num_total_rounds / 3) if num_total_rounds > 3 else num_total_rounds
    num_old_rounds = max(num_total_rounds - num_recent_rounds, 0)
    num_old_animated_rounds = max(num_old_rounds - 1, 0)
    
    def is_recent_round(round_num):
        return round_num > num_old_rounds
    
    first_round_freeze_frames = 30
    animation_frames_per_old_round = 30
    animation_frames_per_recent_round = 50
    freeze_frames_per_old_round = 15
    freeze_frames_per_recent_round = 30

    def ending_frame(round_num):
        if round_num == 1:
            return first_round_freeze_frames
        if is_recent_round(round_num):
            previous_old_animated_rounds = num_old_animated_rounds
            previous_recent_rounds = round_num - 1 - num_old_rounds if num_old_rounds else round_num - 2
        else:
            previous_old_animated_rounds = max(round_num - 2, 0)
            previous_recent_rounds = 0
        frames_per_old_animated_round = animation_frames_per_old_round + freeze_frames_per_old_round
        frames_per_recent_round = animation_frames_per_recent_round + freeze_frames_per_recent_round
        this_round_frames = frames_per_recent_round if is_recent_round(round_num) else frames_per_old_animated_round
        return first_round_freeze_frames + previous_old_animated_rounds * frames_per_old_animated_round + previous_recent_rounds * frames_per_recent_round + this_round_frames

    params_by_round = [
        {
            'anim_length': first_round_freeze_frames,
            'anim_start': 0,
        }
    ]
    params_by_round += [
        {
            'anim_length': animation_frames_per_recent_round if is_recent_round(round_num) else animation_frames_per_old_round,
            'anim_start': ending_frame(round_num - 1) if round_num > 1 else 0,
        } for round_num in range(2, num_total_rounds + 1)
    ]

    ending_frames = [ending_frame(round_num) for round_num in range(1, num_total_rounds + 1)]

    def round_num_from_frame_num(frame_num):
        for round_num, ending_frame in enumerate(ending_frames):
            if frame_num <= ending_frame:
                return round_num + 1

    def update_positions(frame_num):
        round_num = round_num_from_frame_num(frame_num)
        round_params = params_by_round[round_num - 1]
        alpha = min((frame_num - round_params['anim_start']) / round_params['anim_length'], 1) if round_num > 1 else 0
        text_artists['title_artist'].set_text(f'Round {round_num}')

        x_array = []
        y_array = []
        # When a particular round is being animated, the end positions are the positions for that round.
        start_pos = pos_by_round[round_num - 2] if round_num > 1 else pos_by_round[0]
        end_pos = pos_by_round[round_num - 1]
        for node_name, (x, y) in start_pos.items():
            next_round_x, next_round_y = end_pos[node_name]
            x = (1 - alpha) * x + alpha * next_round_x
            y = (1 - alpha) * y + alpha * next_round_y
            x_array.append(x)
            y_array.append(y)
            text_artists[node_name].set_position((x, y))

        sc.set_offsets(list(zip(x_array, y_array)))
        return sc
        
    total_frames = ending_frame(num_total_rounds)

    animation = FuncAnimation(fig, update_positions, frames=total_frames, interval=50, repeat=True)

    return animation


def save_animation(anim):
    ffWriter = FFMpegWriter(fps=24)
    timestring = int(time.time())
    
    output_dir = 'output'
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)
    
    anim.save(f'{output_dir}/out-{timestring}.mp4', writer=ffWriter)


if __name__ == '__main__':
    cumulative_scores_by_round = cumulative_scores_by_round_array()

    pos_by_round = []
    for scores_through_round in cumulative_scores_by_round:
        if not pos_by_round:
            pos_by_round.append(positions(scores_through_round))
        else:
            pos_by_round.append(positions(scores_through_round, start_pos=pos_by_round[-1]))

    anim = make_animation(pos_by_round)
    save_animation(anim)
    # plt.show()

