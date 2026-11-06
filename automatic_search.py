import json
import time
from pathlib import Path

import numpy as np
import requests
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font

TEI_URL = "http://localhost:8080"
PROJECT_DIR = Path(__file__).parent
PRODUCTS_FILE = PROJECT_DIR / "products.json"
QUERIES_FILE = PROJECT_DIR / "queries.json"
RESULTS_FILE = PROJECT_DIR / "results.xlsx"
QUERY_PREFIX = "Instruct: Given a web search query, retrieve relevant passages that answer the query.\nQuery: "
TOP_K = 3
BATCH_SIZE = 32
STARTUP_TIMEOUT_SECONDS = 1200
MAX_SHEET_NAME_LENGTH = 31


def wait_for_model():
    print("Czekam na model...", flush=True)
    deadline = time.monotonic() + STARTUP_TIMEOUT_SECONDS

    while time.monotonic() < deadline:
        try:
            if requests.get(f"{TEI_URL}/health", timeout=2).ok:
                return
        except requests.RequestException:
            pass
        time.sleep(2)

    raise SystemExit(
        f"Model nie odpowiada pod {TEI_URL}. "
        "Sprawdź `docker compose ps` i `docker compose logs embeddings`."
    )


def get_model_name():
    response = requests.get(f"{TEI_URL}/info", timeout=5)
    response.raise_for_status()
    return response.json()["model_id"].split("/")[-1]


def embed(texts):
    response = requests.post(
        f"{TEI_URL}/embed",
        json={"inputs": texts, "normalize": True},
        timeout=120,
    )
    response.raise_for_status()
    return response.json()


def product_text(product):
    return (
        f"{product['name']}. "
        f"Firma: {product['company']}. "
        f"Kategoria: {product['category']}"
    )


def load_products():
    products = json.loads(PRODUCTS_FILE.read_text(encoding="utf-8"))
    texts = [product_text(product) for product in products]

    embeddings = []
    for start in range(0, len(texts), BATCH_SIZE):
        embeddings.extend(embed(texts[start : start + BATCH_SIZE]))

    for product, embedding in zip(products, embeddings):
        product["embedding"] = np.array(embedding)

    return products


def search(products, phrase):
    query = np.array(embed([QUERY_PREFIX + phrase])[0])
    # Oba wektory mają długość 1, więc iloczyn skalarny to podobieństwo cosinusowe.
    scored = [(float(query @ product["embedding"]), product) for product in products]
    scored.sort(key=lambda item: item[0], reverse=True)
    return scored[:TOP_K]


def format_answer(results):
    return "\n".join(
        f"{score:.3f}  {product['name']} "
        f"({product['company']}, {product['category']})"
        for score, product in results
    )


def create_sheet(model_name):
    if RESULTS_FILE.exists():
        workbook = load_workbook(RESULTS_FILE)
    else:
        workbook = Workbook()
        workbook.remove(workbook.active)

    sheet_name = model_name[:MAX_SHEET_NAME_LENGTH]
    if sheet_name in workbook.sheetnames:
        workbook.remove(workbook[sheet_name])

    sheet = workbook.create_sheet(sheet_name)
    sheet.append(["Zapytanie", "Odpowiedź"])
    sheet["A1"].font = Font(bold=True)
    sheet["B1"].font = Font(bold=True)
    sheet.column_dimensions["A"].width = 30
    sheet.column_dimensions["B"].width = 80
    return workbook, sheet


def save_results(model_name, rows):
    workbook, sheet = create_sheet(model_name)

    for phrase, answer in rows:
        sheet.append([phrase, answer])
        for cell in sheet[sheet.max_row]:
            cell.alignment = Alignment(wrap_text=True, vertical="top")

    try:
        workbook.save(RESULTS_FILE)
    except PermissionError:
        raise SystemExit(
            f"Nie mogę zapisać {RESULTS_FILE.name}. "
            "Zamknij plik w Excelu i uruchom program ponownie."
        )


def main():
    wait_for_model()
    model_name = get_model_name()
    print(f"Model: {model_name}", flush=True)

    print("Liczę embeddingi produktów...", flush=True)
    products = load_products()
    phrases = json.loads(QUERIES_FILE.read_text(encoding="utf-8"))

    rows = []
    for phrase in phrases:
        print(f"Szukam: {phrase}", flush=True)
        rows.append((phrase, format_answer(search(products, phrase))))

    save_results(model_name, rows)
    print(f"Zapisano arkusz {model_name[:MAX_SHEET_NAME_LENGTH]} w {RESULTS_FILE.name}")


main()
