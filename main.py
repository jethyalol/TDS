from fastapi import FastAPI, Query, HTTPException
from pydantic import BaseModel
import subprocess
import httpx
import json
import os
import shutil
import sqlite3
import duckdb
import markdown
import pandas as pd
from bs4 import BeautifulSoup
from PIL import Image
import pytesseract
from typing import List
from dotenv import load_dotenv
# Constants
load_dotenv()
DATA_DIR = "/data"
AI_PROXY_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {os.getenv('AIPROXY_TOKEN')}", "Content-Type": "application/json"}

# Initialize FastAPI app
app = FastAPI()

# Security policies (B1 & B2)
def enforce_security(path):
    if not path.startswith(DATA_DIR):
        raise HTTPException(status_code=403, detail="Access to directories outside /data is forbidden.")
    if os.path.exists(path) and os.path.isfile(path) and not os.access(path, os.W_OK):
        raise HTTPException(status_code=403, detail="Insufficient permissions.")
    return path

# LLM for task parsing
def parse_task_with_llm(task_description: str):
    payload = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "Parse the task description and return a JSON object with task type and parameters."},
            {"role": "user", "content": task_description}
        ]
    }
    response = httpx.post(AI_PROXY_URL, json=payload, headers=HEADERS)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]

# Run a command securely
def run_command(cmd):
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=True)
        return result.stdout.strip()
    except subprocess.CalledProcessError as e:
        raise HTTPException(status_code=500, detail=f"Command failed: {e.stderr.strip()}")

# Task Handlers
def install_uv_and_run_datagen(email: str):
    run_command("pip install uv || true")
    run_command(f"python3 -m uv {DATA_DIR}/datagen.py {email}")

def format_markdown():
    run_command(f"npx prettier --write {DATA_DIR}/format.md")

def count_wednesdays():
    with open(enforce_security(f"{DATA_DIR}/dates.txt"), "r") as f:
        dates = f.readlines()
    wednesday_count = sum(1 for date in dates if pd.to_datetime(date, errors='coerce').day_name() == "Wednesday")
    with open(enforce_security(f"{DATA_DIR}/dates-wednesdays.txt"), "w") as f:
        f.write(str(wednesday_count))

def sort_contacts():
    contacts_path = enforce_security(f"{DATA_DIR}/contacts.json")
    with open(contacts_path, "r") as f:
        contacts = json.load(f)
    contacts.sort(key=lambda x: (x["last_name"], x["first_name"]))
    with open(enforce_security(f"{DATA_DIR}/contacts-sorted.json"), "w") as f:
        json.dump(contacts, f, indent=4)

def process_logs():
    logs_dir = enforce_security(f"{DATA_DIR}/logs")
    log_files = sorted([f for f in os.listdir(logs_dir) if f.endswith(".log")], key=lambda f: os.path.getmtime(os.path.join(logs_dir, f)), reverse=True)[:10]
    with open(enforce_security(f"{DATA_DIR}/logs-recent.txt"), "w") as f:
        for log_file in log_files:
            with open(os.path.join(logs_dir, log_file)) as lf:
                f.write(lf.readline())

def create_docs_index():
    docs_dir = enforce_security(f"{DATA_DIR}/docs")
    index = {}
    for file in os.listdir(docs_dir):
        if file.endswith(".md"):
            with open(os.path.join(docs_dir, file), "r") as f:
                for line in f:
                    if line.startswith("# "):
                        index[file] = line.strip("# ").strip()
                        break
    with open(enforce_security(f"{DATA_DIR}/docs/index.json"), "w") as f:
        json.dump(index, f, indent=4)

def extract_email():
    with open(enforce_security(f"{DATA_DIR}/email.txt"), "r") as f:
        email_content = f.read()
    email_address = parse_task_with_llm(f"Extract email address from: {email_content}")
    with open(enforce_security(f"{DATA_DIR}/email-sender.txt"), "w") as f:
        f.write(email_address)

def extract_credit_card():
    image_path = enforce_security(f"{DATA_DIR}/credit-card.png")
    image = Image.open(image_path)
    card_number = pytesseract.image_to_string(image).replace(" ", "").strip()
    with open(enforce_security(f"{DATA_DIR}/credit-card.txt"), "w") as f:
        f.write(card_number)

def compute_ticket_sales():
    db_path = enforce_security(f"{DATA_DIR}/ticket-sales.db")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT SUM(units * price) FROM tickets WHERE type='Gold'")
    total_sales = cursor.fetchone()[0] or 0
    conn.close()
    with open(enforce_security(f"{DATA_DIR}/ticket-sales-gold.txt"), "w") as f:
        f.write(str(total_sales))

# Business Tasks (B3–B10)
def fetch_api_data(url: str, output_path: str):
    response = httpx.get(url)
    response.raise_for_status()
    with open(enforce_security(output_path), "w") as f:
        f.write(response.text)

def clone_git_repo(repo_url: str):
    run_command(f"git clone {repo_url} {DATA_DIR}/repo")

def run_sql_query(db_path: str, query: str):
    conn = duckdb.connect(enforce_security(db_path))
    result = conn.execute(query).fetchall()
    conn.close()
    return result

def scrape_website(url: str):
    response = httpx.get(url)
    response.raise_for_status()
    return BeautifulSoup(response.text, "html.parser").prettify()

def resize_image(image_path: str, output_path: str, size=(128, 128)):
    img = Image.open(enforce_security(image_path))
    img.thumbnail(size)
    img.save(enforce_security(output_path))

def transcribe_audio(audio_path: str, output_path: str):
    run_command(f"whisper {audio_path} --output {output_path}")

def convert_md_to_html(md_path: str, html_path: str):
    with open(enforce_security(md_path), "r") as f:
        md_content = f.read()
    html_content = markdown.markdown(md_content)
    with open(enforce_security(html_path), "w") as f:
        f.write(html_content)

# API Endpoints
@app.post("/run")
def run_task(task: str = Query(...)):
    try:
        task_data = parse_task_with_llm(task)
        eval(task_data)  # Executes corresponding function
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/read")
def read_file(path: str):
    try:
        with open(enforce_security(path), "r") as f:
            return f.read()
    except FileNotFoundError:
        raise HTTPException(status_code=404, detail="File not found")