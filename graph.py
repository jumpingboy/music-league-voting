import json
import time
from functools import partial
import pdb


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
    ax.set_title(f'Round {round_num}')  # Set the title of the plot

    plt.show()
    return positions


cumulative_scores_by_round = cumulative_scores_by_round_array()

pos_by_round = []
for scores_through_round in cumulative_scores_by_round:
    if not pos_by_round:
        pos_by_round.append(positions(scores_through_round))
    else:
        pos_by_round.append(positions(scores_through_round, start_pos=pos_by_round[-1]))


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
    text_artists['title_artist'] = ax.set_title(f'After Round 1', fontsize=48)
    fig.tight_layout()
    
    animation_frames_per_round = 80
    freeze_frames_per_round = 40
    frames_per_round = animation_frames_per_round + freeze_frames_per_round

    def update_positions(frame_num):
        round_num = int(frame_num / frames_per_round + 1)
        alpha = max(frame_num % frames_per_round - freeze_frames_per_round, 0) / animation_frames_per_round
        if frame_num % frames_per_round < freeze_frames_per_round:
            text_artists['title_artist'].set_text(f'After Round {round_num}')
        else:
            text_artists['title_artist'].set_text('')

        x_array = []
        y_array = []
        this_round_pos = pos_by_round[round_num - 1]
        next_round_pos = pos_by_round[round_num] if round_num < len(pos_by_round) else this_round_pos
        for node_name, (x, y) in this_round_pos.items():
            next_round_x, next_round_y = next_round_pos[node_name]
            x = (1 - alpha) * x + alpha * next_round_x
            y = (1 - alpha) * y + alpha * next_round_y
            x_array.append(x)
            y_array.append(y)
            text_artists[node_name].set_position((x, y))

        sc.set_offsets(list(zip(x_array, y_array)))
        return sc
        
    total_frames = frames_per_round * (len(pos_by_round) - 1) + freeze_frames_per_round

    animation = FuncAnimation(fig, update_positions, frames=total_frames, interval=50, repeat=True)

    return animation

def save_animation(anim):
    ffWriter = FFMpegWriter(fps=24)
    timestring = int(time.time())
    anim.save(f'output/out-{timestring}.mp4', writer=ffWriter)

anim = make_animation(pos_by_round)
# save_animation(anim)
plt.show()

