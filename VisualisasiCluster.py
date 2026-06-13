import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
import os

INPUT_FILE = "output/glints_clustered.csv"
OUTPUT_DIR = "output/visualisasi"
os.makedirs(OUTPUT_DIR, exist_ok=True)

df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
print(f"Data berhasil dimuat: {len(df)} baris")
print(f"Cluster unik: {sorted(df['cluster'].unique())}")

COLORS = ["#2E75B6", "#ED7D31", "#A9D18E", "#FF4B4B"]
CLUSTER_LABELS = {
    0: "Cluster 0",
    1: "Cluster 1",
    2: "Cluster 2",
    3: "Cluster 3"
}

fig, ax = plt.subplots(figsize=(8, 5))

cluster_counts = df["cluster"].value_counts().sort_index()
bars = ax.bar(
    [f"Cluster {i}" for i in cluster_counts.index],
    cluster_counts.values,
    color=COLORS[:len(cluster_counts)],
    edgecolor="white",
    linewidth=1.2
)

for bar, val in zip(bars, cluster_counts.values):
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        bar.get_height() + 0.5,
        str(val),
        ha="center", va="bottom",
        fontsize=12, fontweight="bold"
    )

ax.set_title("Distribusi Jumlah Lowongan per Cluster", fontsize=14, fontweight="bold", pad=15)
ax.set_xlabel("Cluster", fontsize=12)
ax.set_ylabel("Jumlah Lowongan", fontsize=12)
ax.set_ylim(0, cluster_counts.max() * 1.15)
ax.grid(axis="y", alpha=0.3, linestyle="--")
ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/chart1_distribusi_cluster.png", dpi=150, bbox_inches="tight")
plt.close()
print("Chart 1 disimpan: chart1_distribusi_cluster.png")

fig, ax = plt.subplots(figsize=(10, 6))

category_cluster = df.groupby(["cluster", "keyword_category"]).size().unstack(fill_value=0)
categories = category_cluster.columns.tolist()
cat_colors = ["#1F4E79", "#2E75B6", "#A9C6E8", "#ED7D31", "#FFB347"]

bottom = np.zeros(len(category_cluster))
for i, cat in enumerate(categories):
    vals = category_cluster[cat].values
    bars = ax.bar(
        [f"Cluster {c}" for c in category_cluster.index],
        vals,
        bottom=bottom,
        label=cat,
        color=cat_colors[i % len(cat_colors)],
        edgecolor="white",
        linewidth=0.8
    )
    for bar, val, bot in zip(bars, vals, bottom):
        if val >= 3:
            ax.text(
                bar.get_x() + bar.get_width() / 2,
                bot + val / 2,
                str(val),
                ha="center", va="center",
                fontsize=9, color="white", fontweight="bold"
            )
    bottom += vals

ax.set_title("Distribusi Kategori Pekerjaan per Cluster", fontsize=14, fontweight="bold", pad=15)
ax.set_xlabel("Cluster", fontsize=12)
ax.set_ylabel("Jumlah Lowongan", fontsize=12)
ax.legend(title="Kategori", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=10)
ax.grid(axis="y", alpha=0.3, linestyle="--")
ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/chart2_kategori_per_cluster.png", dpi=150, bbox_inches="tight")
plt.close()
print("Chart 2 disimpan: chart2_kategori_per_cluster.png")

fig, ax = plt.subplots(figsize=(11, 6))

top_locations = df["location"].value_counts().head(5).index.tolist()
df_loc = df[df["location"].isin(top_locations)]
loc_cluster = df_loc.groupby(["cluster", "location"]).size().unstack(fill_value=0)

n_clusters = len(loc_cluster)
n_locs = len(loc_cluster.columns)
x = np.arange(n_clusters)
width = 0.8 / n_locs
loc_colors = ["#1F4E79", "#2E75B6", "#70AD47", "#ED7D31", "#FF4B4B"]

for i, loc in enumerate(loc_cluster.columns):
    offset = (i - n_locs / 2) * width + width / 2
    bars = ax.bar(
        x + offset,
        loc_cluster[loc].values,
        width=width * 0.9,
        label=loc,
        color=loc_colors[i % len(loc_colors)],
        edgecolor="white"
    )

ax.set_title("Distribusi Lokasi Dominan per Cluster", fontsize=14, fontweight="bold", pad=15)
ax.set_xlabel("Cluster", fontsize=12)
ax.set_ylabel("Jumlah Lowongan", fontsize=12)
ax.set_xticks(x)
ax.set_xticklabels([f"Cluster {c}" for c in loc_cluster.index])
ax.legend(title="Lokasi", bbox_to_anchor=(1.01, 1), loc="upper left", fontsize=10)
ax.grid(axis="y", alpha=0.3, linestyle="--")
ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/chart3_lokasi_per_cluster.png", dpi=150, bbox_inches="tight")
plt.close()
print("Chart 3 disimpan: chart3_lokasi_per_cluster.png")

fig, axes = plt.subplots(2, 2, figsize=(10, 8))
axes = axes.flatten()

for i, cluster_id in enumerate(sorted(df["cluster"].unique())):
    df_c = df[df["cluster"] == cluster_id]
    ada = df_c["has_salary"].sum()
    tidak = len(df_c) - ada
    sizes = [ada, tidak]
    labels = [f"Ada Gaji\n({ada})", f"Tidak Ada\n({tidak})"]
    colors_donut = [COLORS[i], "#D9D9D9"]

    wedges, texts, autotexts = axes[i].pie(
        sizes,
        labels=labels,
        colors=colors_donut,
        autopct="%1.1f%%",
        startangle=90,
        wedgeprops=dict(width=0.5),
        textprops={"fontsize": 10}
    )
    for at in autotexts:
        at.set_fontweight("bold")

    axes[i].set_title(f"Cluster {cluster_id} (n={len(df_c)})", fontsize=12, fontweight="bold")

fig.suptitle("Transparansi Informasi Gaji per Cluster", fontsize=14, fontweight="bold", y=1.01)
plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/chart4_gaji_per_cluster.png", dpi=150, bbox_inches="tight")
plt.close()
print("Chart 4 disimpan: chart4_gaji_per_cluster.png")

from sklearn.decomposition import PCA
from sklearn.preprocessing import LabelEncoder

df_enc = df.copy()
for col in ["location", "keyword_category", "education_req"]:
    le = LabelEncoder()
    df_enc[col + "_enc"] = le.fit_transform(df_enc[col].astype(str))

X = df_enc[["location_enc", "keyword_category_enc", "education_req_enc", "has_salary"]].values

pca = PCA(n_components=2, random_state=42)
X_2d = pca.fit_transform(X)

fig, ax = plt.subplots(figsize=(9, 6))

for cluster_id in sorted(df["cluster"].unique()):
    mask = df["cluster"].values == cluster_id
    ax.scatter(
        X_2d[mask, 0],
        X_2d[mask, 1],
        c=COLORS[cluster_id],
        label=f"Cluster {cluster_id}",
        alpha=0.7,
        s=60,
        edgecolors="white",
        linewidths=0.5
    )

ax.set_title("Visualisasi Cluster (PCA 2D)", fontsize=14, fontweight="bold", pad=15)
ax.set_xlabel(f"PC1 ({pca.explained_variance_ratio_[0]*100:.1f}% variance)", fontsize=11)
ax.set_ylabel(f"PC2 ({pca.explained_variance_ratio_[1]*100:.1f}% variance)", fontsize=11)
ax.legend(title="Cluster", fontsize=10)
ax.grid(alpha=0.3, linestyle="--")
ax.spines[["top", "right"]].set_visible(False)

plt.tight_layout()
plt.savefig(f"{OUTPUT_DIR}/chart5_scatter_pca.png", dpi=150, bbox_inches="tight")
plt.close()
print("Chart 5 disimpan: chart5_scatter_pca.png")

print("\n" + "="*50)
print("SEMUA CHART BERHASIL DISIMPAN")
print(f"Lokasi: {OUTPUT_DIR}/")
print("="*50)
print("\nDaftar file:")
for f_name in sorted(os.listdir(OUTPUT_DIR)):
    print(f"  - {f_name}")