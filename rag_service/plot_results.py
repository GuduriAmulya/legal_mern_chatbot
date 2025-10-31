import json
import matplotlib.pyplot as plt
import numpy as np

# Load results
with open("benchmark_results.json") as f:
    data = json.load(f)

# Figure 1: Overall Comparison
fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 5))

# Bar chart: Hybrid vs Vector
methods = ['Hybrid\n(BM25 + Vector)', 'Vector-Only']
accuracies = [data['hybrid_accuracy'] * 100, data['vector_accuracy'] * 100]
colors = ['#1e6fb8', '#94a3b8']

ax1.bar(methods, accuracies, color=colors, edgecolor='black', linewidth=1.5)
ax1.set_ylabel('Hit@3 Accuracy (%)', fontsize=12, fontweight='bold')
ax1.set_title('Retrieval Method Comparison', fontsize=14, fontweight='bold')
ax1.set_ylim(0, 100)
ax1.grid(axis='y', alpha=0.3)

for i, v in enumerate(accuracies):
    ax1.text(i, v + 2, f'{v:.1f}%', ha='center', fontweight='bold', fontsize=11)

# Difficulty breakdown
difficulties = ['Easy', 'Medium', 'Hard']
hybrid_scores = [data['by_difficulty'][d.lower()]['hybrid'] * 100 for d in difficulties]
vector_scores = [data['by_difficulty'][d.lower()]['vector'] * 100 for d in difficulties]

x = np.arange(len(difficulties))
width = 0.35

ax2.bar(x - width/2, hybrid_scores, width, label='Hybrid', color='#1e6fb8', edgecolor='black')
ax2.bar(x + width/2, vector_scores, width, label='Vector-Only', color='#94a3b8', edgecolor='black')

ax2.set_ylabel('Hit@3 Accuracy (%)', fontsize=12, fontweight='bold')
ax2.set_title('Performance by Question Difficulty', fontsize=14, fontweight='bold')
ax2.set_xticks(x)
ax2.set_xticklabels(difficulties)
ax2.legend(loc='upper right')
ax2.set_ylim(0, 100)
ax2.grid(axis='y', alpha=0.3)

plt.tight_layout()
plt.savefig('benchmark_results.png', dpi=300, bbox_inches='tight')
print("✓ Plot saved to benchmark_results.png")
plt.show()

# Figure 2: Publication-Quality Plot
fig, ax = plt.subplots(figsize=(10, 6))

difficulties = ['Easy\n(Exact Citations)', 'Medium\n(Conceptual)', 'Hard\n(Multi-Article)']
hybrid_scores = [
    data['by_difficulty']['easy']['hybrid'] * 100,
    data['by_difficulty']['medium']['hybrid'] * 100,
    data['by_difficulty']['hard']['hybrid'] * 100
]
vector_scores = [
    data['by_difficulty']['easy']['vector'] * 100,
    data['by_difficulty']['medium']['vector'] * 100,
    data['by_difficulty']['hard']['vector'] * 100
]

x = np.arange(len(difficulties))
width = 0.35

bars1 = ax.bar(x - width/2, hybrid_scores, width, label='Hybrid (BM25 + Vector)', 
               color='#1e6fb8', edgecolor='black', linewidth=1.5)
bars2 = ax.bar(x + width/2, vector_scores, width, label='Vector-Only', 
               color='#94a3b8', edgecolor='black', linewidth=1.5)

# Add value labels on bars
for bars in [bars1, bars2]:
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2., height + 2,
                f'{height:.1f}%', ha='center', va='bottom', fontweight='bold', fontsize=10)

ax.set_ylabel('Hit@3 Accuracy (%)', fontsize=13, fontweight='bold')
ax.set_xlabel('Question Type', fontsize=13, fontweight='bold')
ax.set_title('Retrieval Performance by Question Difficulty', fontsize=15, fontweight='bold')
ax.set_xticks(x)
ax.set_xticklabels(difficulties, fontsize=11)
ax.legend(loc='upper right', fontsize=11)
ax.set_ylim(0, 110)
ax.grid(axis='y', alpha=0.3, linestyle='--')

plt.tight_layout()
plt.savefig('benchmark_results.png', dpi=300, bbox_inches='tight')
print("✓ Plot saved to benchmark_results.png")
plt.show()
