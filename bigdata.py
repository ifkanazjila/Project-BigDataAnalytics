from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import re
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

BASE_URL = "https://glints.com/id/opportunities/jobs/explore"

KEYWORDS = ["data", "software", "engineer", "analyst", "IT"]
MAX_PAGE = 5
TARGET_DATA = 160
OUTPUT_FILE = "Dataset_AnalitikBigData.csv"

def setup_driver():
    options = Options()
    options.add_argument("--start-maximized")
    options.add_argument("--disable-blink-features=AutomationControlled")

    driver = webdriver.Chrome(
        service=Service(ChromeDriverManager().install()),
        options=options
    )

    driver.execute_script(
        "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
    )

    return driver


def clean_text(text):
    return re.sub(r"\s+", " ", text.strip()) if text else ""


def format_rupiah(text):
    angka = re.sub(r"[^\d]", "", text)

    if not angka:
        return text

    return "Rp. " + "{:,}".format(int(angka)).replace(",", ".")


def extract_salary(text):

    salaries = re.findall(
        r'Rp\s*[\d.]+(?:,\d+)?',
        text,
        flags=re.IGNORECASE
    )

    if not salaries:
        return "Tidak disebutkan"

    cleaned = []

    for salary in salaries:

        angka = re.sub(r"[^\d]", "", salary)

        if len(angka) < 6:
            continue

        formatted = (
            "Rp. "
            + "{:,}".format(int(angka)).replace(",", ".")
        )

        cleaned.append(formatted)

    if not cleaned:
        return "Tidak disebutkan"

    cleaned = sorted(
        list(set(cleaned)),
        key=lambda x: int(re.sub(r"[^\d]", "", x))
    )

    if len(cleaned) >= 2:
        return f"{cleaned[0]} - {cleaned[-1]}"

    return cleaned[0]

def scrape_detail(driver, url):

    driver.get(url)
    time.sleep(random.uniform(2, 4))

    soup = BeautifulSoup(driver.page_source, "html.parser")
    page_text = soup.get_text(" ", strip=True)

    title_tag = soup.find("h1")
    job_title = clean_text(title_tag.text) if title_tag else "Tidak ditemukan"

    company_tag = soup.find("a", href=lambda x: x and "/companies/" in x)
    company_name = clean_text(company_tag.text) if company_tag else "Tidak ditemukan"

    location = "Tidak ditemukan"

    cities = [
        "jakarta",
        "bandung",
        "surabaya",
        "remote",
        "medan",
        "semarang",
        "yogyakarta",
        "malang",
        "bali"
    ]

    for city in cities:
        if city in page_text.lower():
            location = city.title()
            break

    job_type = (
        "Full-time"
        if "full time" in page_text.lower()
        else "Tidak ditemukan"
    )

    exp = re.search(r"\d+\+?\s*tahun", page_text.lower())
    experience_level = exp.group() if exp else "Tidak ditemukan"

    edu = re.search(
        r"S[123]|D[1234]|SMA|SMK|Bachelor",
        page_text
    )

    education_req = edu.group() if edu else "Tidak ditemukan"

    salary_range = extract_salary(page_text)

    # SKILL / REQUIREMENTS

    skill_keywords = [
        "Python",
        "SQL",
        "Excel",
        "Java",
        "JavaScript",
        "HTML",
        "CSS",
        "React",
        "Vue",
        "Angular",
        "Laravel",
        "PHP",
        "Node.js",
        "Spring Boot",
        "Machine Learning",
        "Deep Learning",
        "TensorFlow",
        "PyTorch",
        "Power BI",
        "Tableau",
        "Data Analysis",
        "Data Visualization",
        "Git",
        "Docker",
        "AWS",
        "Azure",
        "Linux",
        "MySQL",
        "PostgreSQL",
        "MongoDB"
    ]

    found_skills = []

    for skill in skill_keywords:
        if skill.lower() in page_text.lower():
            found_skills.append(skill)

    job_requirements = (
        ", ".join(found_skills[:5])
        if found_skills
        else "Tidak ditemukan"
    )

    # RESPONSIBILITIES
    responsibilities_map = {
        "frontend": "Mengembangkan tampilan frontend",
        "backend": "Mengembangkan sistem backend",
        "full stack": "Mengembangkan aplikasi full stack",
        "machine learning": "Membangun model machine learning",
        "data analyst": "Menganalisis data perusahaan",
        "data scientist": "Mengembangkan solusi berbasis data",
        "dashboard": "Membuat dashboard dan visualisasi data",
        "report": "Menyusun laporan dan insight data",
        "testing": "Melakukan pengujian sistem",
        "quality assurance": "Menjamin kualitas perangkat lunak",
        "api": "Mengembangkan dan mengelola API",
        "database": "Mengelola database perusahaan",
        "security": "Menjaga keamanan sistem informasi"
    }

    job_responsibilities = "Tidak ditemukan"

    for keyword, desc in responsibilities_map.items():
        if keyword in page_text.lower():
            job_responsibilities = desc
            break

    posted_date = datetime.now().strftime("%Y-%m-%d")

    source_platform = "Glints"

    return {
        "job_title": job_title,
        "company_name": company_name,
        "location": location,
        "job_type": job_type,
        "experience_level": experience_level,
        "education_req": education_req,
        "salary_range": salary_range,
        "job_requirements": job_requirements,
        "job_responsibilities": job_responsibilities,
        "posted_date": posted_date,
        "source_platform": source_platform
    }


def main():

    driver = setup_driver()
    job_links = set()
    all_jobs = []

    try:

        for keyword in KEYWORDS:

            print(f"\nKeyword: {keyword}")

            for page in range(1, MAX_PAGE + 1):

                search_url = f"{BASE_URL}?keyword={keyword}&page={page}"

                print(f"Halaman: {page}")

                driver.get(search_url)
                time.sleep(3)

                soup = BeautifulSoup(
                    driver.page_source,
                    "html.parser"
                )

                links = soup.find_all("a", href=True)

                for link in links:

                    href = link["href"]

                    if "/opportunities/jobs/" in href:
                        full_link = "https://glints.com" + href
                        job_links.add(full_link)

                print(
                    "Total link sementara:",
                    len(job_links)
                )

                if len(job_links) >= TARGET_DATA:
                    break

        print("\nTotal link terkumpul:", len(job_links))

        for link in list(job_links)[:TARGET_DATA]:

            try:
                job_data = scrape_detail(driver, link)

                all_jobs.append(job_data)

                print("✓", job_data["job_title"])

            except Exception as e:
                print("Gagal:", e)

        print("\nTotal data berhasil:", len(all_jobs))

    finally:
        driver.quit()

    df = pd.DataFrame(all_jobs)

    df = df[[
        "job_title",
        "company_name",
        "location",
        "job_type",
        "experience_level",
        "education_req",
        "salary_range",
        "job_requirements",
        "job_responsibilities",
        "posted_date",
        "source_platform"    
]]

    df.to_csv(
        OUTPUT_FILE,
        index=False,
        encoding="utf-8-sig"
    )

    print("\nDataset berhasil disimpan:", OUTPUT_FILE)


if __name__ == "__main__":
    main()