import json
import time
from pathlib import Path

import numpy as np
import requests

TEI_URL = "http://localhost:8080"
PRODUCTS_FILE = Path(__file__).parent / "products.json"
QUERY_PREFIX = "Instruct: Given a web search query, retrieve relevant passages that answer the query.\nQuery: "
TOP_K = 5
BATCH_SIZE = 32
STARTUP_TIMEOUT_SECONDS = 1200


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


def main():
    wait_for_model()

    print("Liczę embeddingi produktów...", flush=True)
    products = load_products()
    print(f"Gotowe: {len(products)} produktów. Pusta linia kończy program.\n")

    while True:
        try:
            phrase = input("Szukaj: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break

        if not phrase:
            break

        for score, product in search(products, phrase):
            print(
                f"  {score:.3f}  {product['name']} "
                f"({product['company']}, {product['category']})"
            )
        print()

main()
