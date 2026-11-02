# Walidacja 0.1.0 — 2026-11-02

- 38 testów klienta API, modelu, kalendarza i kontraktu prezentacji ZIM: OK.
  Uruchomione z Pythonem 3.10 oraz 3.14.10.
- Ruff: OK. Kompilacja wszystkich modułów komponentu: OK.
- Wszystkie pliki JSON, w tym tłumaczenia PL/EN: poprawne składniowo.
- Test `tests/ha/runtime_smoke.py` z rzeczywistymi klasami Home Assistant
  2026.10.4: OK — formularze przystanku/linii/kierunku, koordynator, wartości
  i atrybuty trzech sensorów, wydarzenia kalendarza i przycięcie zakresu.
  Test korzysta z atrap odpowiedzi API, bez uruchamiania serwera HA.
- Gotowy klient aiohttp odczytał 399 przystanków oraz wszystkie cztery relacje
  z oryginalnego YAML. Sprawdzono dzisiaj, jutro oraz dzisiaj + 13 dni, a także
  powiązanie tablicy bieżącej z rozkładem.
- Potwierdzono potrzebę jawnego nagłówka User-Agent: domyślny klient
  Python/aiohttp otrzymywał HTTP 400; HomeAssistant/NordExpress-0.1.0 HTTP 200.
- Pełne testy cyklu życia HA: przygotowane w `tests/ha`, ale nie uruchomione do końca
  lokalnie. Oficjalny harness z Home Assistant 2026.10.4 wymaga modułu Unix
  `fcntl`, niedostępnego na Windows. Nie zastępowano go atrapą. Workflow CI
  uruchamia te testy na Ubuntu/Pythonie 3.14 po opublikowaniu repozytorium.

Integracja nie została jeszcze uruchomiona w docelowym Home Assistant
użytkownika. Nie zmieniono pakietu YAML ani dashboardów. Zalecany pierwszy
odbiór: dodać jedną relację, porównać sensor i kalendarz z tablicą przewoźnika,
a następnie przełączyć istniejącą kartę ZIM na nową encję.
