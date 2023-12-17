import random
import pdb

from matplotlib import pyplot as plt
import networkx as nx

from similarity import calc_similarity_scores
import random

similarity_scores = calc_similarity_scores()

G = nx.Graph()

for member_name, member_scores in similarity_scores.items():
    for score_dict in member_scores:
        G.add_edge(member_name, score_dict['name'], weight = (-1 * (score_dict['score'] + 16)) + 52)

pos = nx.kamada_kawai_layout(G, dim=3)

node_pos = [pos[node] for node in G.nodes]

fig = plt.figure(figsize=(15, 10))
ax = fig.add_subplot(111, projection='3d')

node_colors = ['#ff3535', '#ffa135', '#ffcf35', '#9fff35', '#4acb4abc', '#00a8a5', '#4bd2ff', '#006eff', '#5535ff', '#9f35ff', '#ff35ff', '#ff9bc3']

zmax = max([z for x, y, z in node_pos])
zmin = min([z for x, y, z in node_pos])
zrange = zmax - zmin

for i, node in enumerate(G.nodes):
    x, y, z = node_pos[i]
    node_color = node_colors[i]

    ax.scatter(x, y, z, c=node_color, label=node, s=200)
    ax.text(x, y, z-(0.1 * zrange), node, color='black', fontsize=12, ha='center', va='center')

ax.set_xticklabels([])
ax.set_yticklabels([])
ax.set_zticklabels([])
ax.legend()

plt.show()
