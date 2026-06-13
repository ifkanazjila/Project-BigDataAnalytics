from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.ml.feature import StringIndexer, VectorAssembler, StandardScaler
from pyspark.ml.clustering import KMeans
from pyspark.ml.evaluation import ClusteringEvaluator
from pyspark.ml import Pipeline
import os

spark = SparkSession.builder \
    .appName("GlintsKMeansClustering") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")
print("SparkSession berhasil dibuat.")
print(f"Versi Spark: {spark.version}")

df = spark.read.csv(
    r"C:\ANALITIK BIG DATA\output\glints_cleaned.csv",
    header=True,
    inferSchema=True
)

df_clean = df.filter(
    (F.col("job_title") != "Tidak ditemukan") &
    (F.col("company_name") != "Tidak ditemukan")
).fillna({
    "location": "Tidak diketahui",
    "salary_range": "Tidak disebutkan",
    "experience_level": "Tidak disebutkan",
    "education_req": "Tidak disebutkan"
})

df_clean = df_clean.withColumn(
    "keyword_category",
    F.when(F.lower(F.col("job_title")).contains("data"), "Data")
     .when(F.lower(F.col("job_title")).contains("software"), "Software")
     .when(F.lower(F.col("job_title")).contains("analyst"), "Analyst")
     .when(F.lower(F.col("job_title")).contains("engineer"), "Engineer")
     .otherwise("IT Umum")
)

df_clean = df_clean.withColumn(
    "has_salary",
    F.when(F.col("salary_range") != "Tidak disebutkan", 1).otherwise(0)
)

print(f"\nTotal data untuk clustering: {df_clean.count()} baris")

print("\n=== FEATURE ENGINEERING ===")

indexer_location = StringIndexer(
    inputCol="location",
    outputCol="location_idx",
    handleInvalid="keep"
)
indexer_edu = StringIndexer(
    inputCol="education_req",
    outputCol="edu_idx",
    handleInvalid="keep"
)
indexer_category = StringIndexer(
    inputCol="keyword_category",
    outputCol="category_idx",
    handleInvalid="keep"
)
assembler = VectorAssembler(
    inputCols=["location_idx", "edu_idx", "category_idx", "has_salary"],
    outputCol="features_raw"
)

scaler = StandardScaler(
    inputCol="features_raw",
    outputCol="features",
    withMean=True,
    withStd=True
)

print("\n=== ELBOW METHOD - MENCARI K OPTIMAL ===")

prep_pipeline = Pipeline(stages=[
    indexer_location, indexer_edu, indexer_category,
    assembler, scaler
])
prep_model = prep_pipeline.fit(df_clean)
df_features = prep_model.transform(df_clean)

costs = []
k_range = range(2, 8)

for k in k_range:
    kmeans_temp = KMeans(
        featuresCol="features",
        predictionCol="cluster",
        k=k,
        seed=42,
        maxIter=20
    )
    model_temp = kmeans_temp.fit(df_features)
    cost = model_temp.summary.trainingCost
    costs.append((k, round(cost, 2)))
    print(f"  K={k} | WSSSE (Within-Cluster Sum of Squared Errors): {cost:.2f}")

print("\nRekomendasi: Pilih K di titik 'siku' (penurunan mulai melambat)")

print("\n=== TRAINING K-MEANS DENGAN K=4 ===")

kmeans = KMeans(
    featuresCol="features",
    predictionCol="cluster",
    k=4,
    seed=42,
    maxIter=50
)

kmeans_model = kmeans.fit(df_features)

df_clustered = kmeans_model.transform(df_features)

print(f"Training selesai. Jumlah cluster: {kmeans_model.summary.k}")
print(f"WSSSE final: {kmeans_model.summary.trainingCost:.4f}")

print("\n=== EVALUASI MODEL ===")

evaluator = ClusteringEvaluator(
    featuresCol="features",
    predictionCol="cluster",
    metricName="silhouette"
)
silhouette = evaluator.evaluate(df_clustered)
print(f"Silhouette Score: {silhouette:.4f}")
print("(Nilai mendekati 1.0 = cluster sangat baik terpisah)")

print("\n=== PROFIL SETIAP CLUSTER ===")

df_clustered.createOrReplaceTempView("clustered_jobs")

print("\n-- Distribusi anggota per cluster --")
spark.sql("""
    SELECT
        cluster,
        COUNT(*) AS jumlah_lowongan
    FROM clustered_jobs
    GROUP BY cluster
    ORDER BY cluster
""").show()

print("\n-- Kategori pekerjaan dominan per cluster --")
spark.sql("""
    SELECT
        cluster,
        keyword_category,
        COUNT(*) AS jumlah
    FROM clustered_jobs
    GROUP BY cluster, keyword_category
    ORDER BY cluster, jumlah DESC
""").show(20)

print("\n-- Lokasi dominan per cluster --")
spark.sql("""
    SELECT
        cluster,
        location,
        COUNT(*) AS jumlah
    FROM clustered_jobs
    GROUP BY cluster, location
    ORDER BY cluster, jumlah DESC
""").show(20)

print("\n-- Persyaratan pendidikan per cluster --")
spark.sql("""
    SELECT
        cluster,
        education_req,
        COUNT(*) AS jumlah
    FROM clustered_jobs
    GROUP BY cluster, education_req
    ORDER BY cluster, jumlah DESC
""").show(20)

print("\n-- Transparansi gaji per cluster --")
spark.sql("""
    SELECT
        cluster,
        SUM(has_salary) AS ada_gaji,
        COUNT(*) AS total,
        ROUND(SUM(has_salary) * 100.0 / COUNT(*), 1) AS pct_ada_gaji
    FROM clustered_jobs
    GROUP BY cluster
    ORDER BY cluster
""").show()

os.makedirs("output", exist_ok=True)

df_result = df_clustered.select(
    "job_title", "company_name", "location",
    "keyword_category", "education_req",
    "salary_range", "has_salary", "cluster"
)

df_result.toPandas().to_csv(
    "output/glints_clustered.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nHasil clustering disimpan ke: output/glints_clustered.csv")

spark.stop()
print("SparkSession ditutup.")