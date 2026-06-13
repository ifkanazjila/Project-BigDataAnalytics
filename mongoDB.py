import pandas as pd
from pymongo import MongoClient
from datetime import datetime
import os

MONGO_URI  = "mongodb://localhost:27017/"
DB_NAME    = "bigdata_glints"
INPUT_FILE = "output/glints_clustered.csv"

df = pd.read_csv(INPUT_FILE, encoding="utf-8-sig")
print(f"Data dimuat: {len(df)} baris")
print(f"Kolom: {df.columns.tolist()}")

print(f"\nMenghubungkan ke MongoDB: {MONGO_URI}")
client = MongoClient(MONGO_URI, serverSelectionTimeoutMS=5000)

mongo_ok = False

try:
    client.admin.command("ping")
    print("Koneksi MongoDB berhasil!")
    mongo_ok = True

except Exception as e:
    print(f"Gagal terhubung ke MongoDB: {e}")
    print("MongoDB tidak aktif, lanjut ke backup file...")

if not mongo_ok:
    os.makedirs("output", exist_ok=True)

    df.to_csv("output/mongo_backup.csv", index=False, encoding="utf-8-sig")
    df.to_json("output/mongo_backup.json", orient="records", force_ascii=False)

    print("\n✔ Backup berhasil dibuat:")
    print("  - output/mongo_backup.csv")
    print("  - output/mongo_backup.json")

else:
    db = client[DB_NAME]

    collection_raw = db["raw_jobs"]
    collection_raw.drop()

    records = df.to_dict(orient="records")

    for rec in records:
        rec["scraped_at"] = datetime.now().isoformat()
        rec["source"] = "Glints.com"

    collection_raw.insert_many(records)
    print(f"\n[raw_jobs] {len(records)} dokumen berhasil disimpan.")

    collection_summary = db["cluster_summary"]
    collection_summary.drop()

    summaries = []

    for cluster_id in sorted(df["cluster"].unique()):
        df_c = df[df["cluster"] == cluster_id]

        top_category = df_c["keyword_category"].value_counts().idxmax()
        top_location = df_c["location"].value_counts().idxmax()
        top_education = df_c["education_req"].value_counts().idxmax()
        pct_salary = round(df_c["has_salary"].mean() * 100, 1)

        summary = {
            "cluster_id": int(cluster_id),
            "total_lowongan": int(len(df_c)),
            "kategori_dominan": top_category,
            "lokasi_dominan": top_location,
            "pendidikan_dominan": top_education,
            "pct_gaji_dicantumkan": pct_salary,
            "distribusi_kategori": df_c["keyword_category"].value_counts().to_dict(),
            "distribusi_lokasi": df_c["location"].value_counts().head(5).to_dict(),
            "generated_at": datetime.now().isoformat()
        }

        summaries.append(summary)

        print(f"  Cluster {cluster_id}: {len(df_c)} lowongan | "
              f"Dominan: {top_category} | {top_location}")

    collection_summary.insert_many(summaries)
    print(f"\n[cluster_summary] {len(summaries)} dokumen berhasil disimpan.")

    collection_companies = db["top_companies"]
    collection_companies.drop()

    company_docs = []

    for cluster_id in sorted(df["cluster"].unique()):
        df_c = df[df["cluster"] == cluster_id]
        top_companies = df_c["company_name"].value_counts().head(5).to_dict()

        company_docs.append({
            "cluster_id": int(cluster_id),
            "top_companies": top_companies,
            "generated_at": datetime.now().isoformat()
        })

    collection_companies.insert_many(company_docs)
    print(f"\n[top_companies] {len(company_docs)} dokumen berhasil disimpan.")

    print("\n=== VERIFIKASI DATA DI MONGODB ===")
    print(f"Database: {DB_NAME}")

    for col_name in db.list_collection_names():
        count = db[col_name].count_documents({})
        print(f"  - {col_name:25s}: {count} dokumen")

    print("\n=== CONTOH DATA cluster_summary ===")

    for doc in db["cluster_summary"].find({}, {"_id": 0}):
        print(f"\nCluster {doc['cluster_id']}:")
        print(f"  Total     : {doc['total_lowongan']}")
        print(f"  Kategori  : {doc['kategori_dominan']}")
        print(f"  Lokasi    : {doc['lokasi_dominan']}")
        print(f"  Pendidikan: {doc['pendidikan_dominan']}")
        print(f"  % Gaji    : {doc['pct_gaji_dicantumkan']}%")

    client.close()
    print("\nKoneksi MongoDB ditutup.")
    print("Pipeline Big Data selesai!")