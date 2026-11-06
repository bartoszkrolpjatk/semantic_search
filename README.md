# Wyszukiwarka semantyczna produktów

Prosty prototyp wyszukiwania produktów po znaczeniu, a nie po dokładnym dopasowaniu tekstu. Model embeddingowy działa lokalnie w Dockerze, a produkty są trzymane w pamięci programu.

## Wymagania

- Docker z Docker Compose
- Python 3.10 lub nowszy

## Uruchomienie

```bash
docker compose up -d
pip install -r requirements.txt
python search.py
```

Przy pierwszym uruchomieniu Docker pobiera obraz i model, więc start może potrwać kilka minut. Model zostaje w wolumenie Dockera i kolejne starty nie pobierają go ponownie.

## Obsługa

Po wyświetleniu `Szukaj:` wpisz frazę i naciśnij Enter:

```text
Szukaj: pierogi z serem
  0.868  Pierogi z serem (Virtu, Mrożonki i dania gotowe)
  0.786  Serek wiejski (Piątnica, Nabiał)
  ...
```

Program pokazuje 5 najbliższych produktów. Liczba po lewej to podobieństwo cosinusowe: im wyższe, tym bliżej produkt leży frazy w przestrzeni wektorowej.

Pusta linia kończy program. Kontener zatrzymasz poleceniem:

```bash
docker compose down
```

## Działanie

1. `search.py` czeka, aż serwer modelu będzie gotowy.
2. Wczytuje produkty z `products.json`.
3. Łączy nazwę, firmę i kategorię każdego produktu w jeden tekst i zamienia go na embedding.
4. Zamienia wpisaną frazę na embedding.
5. Porównuje go z embeddingami wszystkich produktów i wybiera 5 najbliższych.

Embeddingi są liczone od nowa przy każdym starcie programu.

## Pliki

| Plik | Opis |
|---|---|
| `search.py` | Główny program |
| `products.json` | Przykładowe produkty |
| `docker-compose.yml` | Serwer modelu |
| `requirements.txt` | Zależności Pythona |

## Ograniczenia

- Program zawsze zwraca 5 wyników, nawet gdy żaden produkt nie pasuje do frazy.
- Wyszukiwanie semantyczne słabo radzi sobie z literówkami i dokładnymi oznaczeniami.
- Dane są tylko w pamięci, a zmiany w `products.json` wymagają ponownego uruchomienia programu.
