import matplotlib.pyplot as plt
import networkx as nx
import pandas as pd

from similarity import calc_similarity_scores

similarity_scores = calc_similarity_scores()
min_score = min(score['score'] for scores in similarity_scores.values() for score in scores)
max_score = max(score['score'] for scores in similarity_scores.values() for score in scores)
score_range = max_score - min_score

G = nx.Graph()

for member_name, member_scores in similarity_scores.items():
    for score_dict in member_scores:
        optimal_distance = round((-1 * (score_dict['score'] - min_score + 0.1)) + score_range + 2.1, 2)
        G.add_edge(member_name, score_dict['name'], weight=optimal_distance)

pos = nx.kamada_kawai_layout(G, dim=2)

fig, ax = plt.subplots(1, figsize=(15, 10))

for i, node_name in enumerate(G.nodes):
    x, y = pos[node_name]
    node_color = '#6fd7f8'

    ax.scatter(x, y, c=node_color, label=node_name, s=1800)
    ax.text(x, y, node_name, color='black', fontsize=12, ha='center', va='center')

ax.axis('off')

plt.show()