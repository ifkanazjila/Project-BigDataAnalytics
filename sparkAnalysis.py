from pyspark.sql import SparkSession
from pyspark.sql import functions as F

spark = SparkSession.builder \
    .appName("GlintsJobAnalysis") \
    .config("spark.sql.shuffle.partitions", "4") \
    .getOrCreate()

spark.sparkContext.setLogLevel("WARN")
print("SparkSession berhasil dibuat.")
print(f"Versi Spark: {spark.version}")

df = spark.read.csv(
    "Dataset_AnalitikBigData.csv",
    header=True,
    inferSchema=True,
    encoding="utf-8"
)

print("\n=== SKEMA DATASET ===")
df.printSchema()

print(f"\nTotal baris: {df.count()}")
print(f"Total kolom: {len(df.columns)}")

print("\n=== 5 BARIS PERTAMA ===")
df.show(5, truncate=50)

df_clean = df.filter(
    (F.col("job_title") != "Tidak ditemukan") &
    (F.col("company_name") != "Tidak ditemukan")
)

df_clean = df_clean.fillna({
    "location": "Tidak diketahui",
    "salary_range": "Tidak disebutkan",
    "experience_level": "Tidak disebutkan",
    "education_req": "Tidak disebutkan"
})

df_clean = df_clean.filter(
    (F.col("job_requirements").isNotNull()) &
    (F.col("job_requirements") != "Tidak ditemukan")
)

df_clean = df_clean.filter(
    (F.col("job_responsibilities").isNotNull()) &
    (F.col("job_responsibilities") != "Tidak ditemukan")
)

df_clean = df_clean.filter(
    (F.col("salary_range").isNotNull()) &
    (F.col("salary_range") != "Tidak disebutkan")
)

df_clean = df_clean.filter(
    (F.col("location").isNotNull()) &
    (F.col("location") != "Tidak ditemukan")
)

df_clean = df_clean.replace(
    "Tidak ditemukan",
    "Tidak diketahui",
    subset=["location"]
)

df_clean = df_clean.replace(
    "Tidak ditemukan",
    None,
    subset=[
        "job_requirements",
        "job_responsibilities"
    ]
)

df_clean = df_clean.filter(
    (F.col("job_requirements").isNotNull()) &
    (F.col("job_requirements") != "Tidak ditemukan") &
    (F.col("job_responsibilities").isNotNull()) &
    (F.col("job_responsibilities") != "Tidak ditemukan")
)

df_clean = df_clean.filter(
    (F.col("salary_range").isNotNull()) &
    (F.col("salary_range") != "Tidak disebutkan")
)

total = df_clean.count()

req_missing = df_clean.filter(
    F.col("job_requirements").isNull()
).count()

resp_missing = df_clean.filter(
    F.col("job_responsibilities").isNull()
).count()

print(f"Requirements kosong: {req_missing} ({req_missing/total*100:.2f}%)")
print(f"Responsibilities kosong: {resp_missing} ({resp_missing/total*100:.2f}%)")

df_clean = df_clean.withColumn(
    "keyword_category",
    F.when(F.lower(F.col("job_title")).contains("data"), "Data")
     .when(F.lower(F.col("job_title")).contains("software"), "Software")
     .when(F.lower(F.col("job_title")).contains("analyst"), "Analyst")
     .when(F.lower(F.col("job_title")).contains("engineer"), "Engineer")
     .otherwise("IT Umum")
)

print(f"\nData setelah pembersihan: {df_clean.count()} baris")
df_clean.show(5, truncate=40)

df_clean = df_clean.filter(
    F.col("job_requirements").isNotNull() |
    F.col("job_responsibilities").isNotNull()
)

df_clean.createOrReplaceTempView("glints_jobs")
print("\nTemporary view 'glints_jobs' berhasil dibuat.")

print("\n=== DISTRIBUSI LOWONGAN PER LOKASI ===")
spark.sql("""
    SELECT
        location,
        COUNT(*) AS jumlah_lowongan,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS persentase
    FROM glints_jobs
    GROUP BY location
    ORDER BY jumlah_lowongan DESC
""").show()

print("\n=== TOP 10 PERUSAHAAN DENGAN LOWONGAN TERBANYAK ===")
spark.sql("""
    SELECT
        company_name,
        COUNT(*) AS total_lowongan,
        COLLECT_LIST(DISTINCT location) AS kota_operasi
    FROM glints_jobs
    GROUP BY company_name
    ORDER BY total_lowongan DESC
    LIMIT 10
""").show(truncate=40)

print("\n=== DISTRIBUSI KATEGORI PEKERJAAN IT ===")
spark.sql("""
    SELECT
        keyword_category AS kategori,
        COUNT(*) AS jumlah,
        ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER(), 2) AS persen
    FROM glints_jobs
    GROUP BY keyword_category
    ORDER BY jumlah DESC
""").show()

print("\n=== ANALISIS KETERSEDIAAN INFORMASI GAJI ===")
spark.sql("""
    SELECT
        CASE
            WHEN salary_range != 'Tidak disebutkan' THEN 'Gaji Dicantumkan'
            ELSE 'Gaji Tidak Dicantumkan'
        END AS status_gaji,
        COUNT(*) AS jumlah_lowongan
    FROM glints_jobs
    GROUP BY status_gaji
    ORDER BY jumlah_lowongan DESC
""").show()

print("\n=== PERSYARATAN PENDIDIKAN PER KATEGORI PEKERJAAN ===")
spark.sql("""
    SELECT
        keyword_category,
        education_req,
        COUNT(*) AS jumlah
    FROM glints_jobs
    WHERE education_req != 'Tidak disebutkan'
    GROUP BY keyword_category, education_req
    ORDER BY keyword_category, jumlah DESC
""").show(20, truncate=30)

print("\n=== JUMLAH NILAI UNIK PER KOLOM ===")
for col_name in ["location", "job_type", "education_req", "keyword_category"]:
    unique_count = df_clean.select(F.countDistinct(col_name)).collect()[0][0]
    print(f"  {col_name:20s}: {unique_count} nilai unik")

# Transparansi gaji per kota
print("\n=== KOTA VS TRANSPARANSI GAJI ===")
df_clean.groupBy("location") \
    .agg(
        F.count("*").alias("total"),
        F.sum(
            F.when(F.col("salary_range") != "Tidak disebutkan", 1).otherwise(0)
        ).alias("ada_gaji")
    ) \
    .withColumn(
        "pct_ada_gaji",
        F.round(F.col("ada_gaji") * 100 / F.col("total"), 1)
    ) \
    .orderBy("total", ascending=False) \
    .show()

import os
os.makedirs("output", exist_ok=True)

df_clean.toPandas().to_csv(
    "output/glints_cleaned.csv",
    index=False,
    encoding="utf-8-sig"
)

print("\nDataset berhasil disimpan ke:")
print("  - output/glints_cleaned.csv")

spark.stop()
print("\nSparkSession ditutup. Analisis selesai.")