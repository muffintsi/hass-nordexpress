# Walidacja 0.3.0 — 2026-11-02

- 49 testów klienta/modelu/prezentacji: OK.
- Test z rzeczywistymi klasami HA 2026.10.4: OK — wybór 101 i 105 na przystanku,
  kierunki osobno dla każdej linii, po jednym sensorze i kalendarzu na linię,
  wspólne odjazdy Główczyce/Cecenowo oraz ponowne dodanie tego samego przystanku
  i 105 z osobnym kierunkiem Słupsk. Identyczny zestaw jest blokowany jako duplikat.
- Opcje: zmiana listy linii i kierunków oraz walidacja pustego wyboru — OK.
- Rejestr HA: usuwanie dawnych sensorów pomocniczych i nieaktywnej linii, zachowanie
  aktywnych sensorów, wpisu niestandardowego i encji obcej platformy — OK.
- Zgodność dawnych wpisów z jedną linią i zachowanie ich identyfikatorów — OK.
- Ruff, kompilacja i składnia JSON — OK.
- Pełnego cyklu życia z oficjalnym harness nie uruchomiono na Windows (brak fcntl).
  Workflow CI jest skonfigurowany do uruchamiania go na Ubuntu.
- Nie zmieniano konfiguracji docelowego HA.

# Walidacja 0.2.1 — 2026-11-02

- 44 testy klienta/modelu/prezentacji: OK.
- Test z rzeczywistymi klasami HA 2026.10.4: OK. Platforma tworzy dokładnie jeden
  sensor, o dotychczasowym unique_id i krótkiej nazwie; kolejne odjazdy są
  dostępne w atrybutach. Kalendarz zachowuje oba wybrane kierunki.
- Test rzeczywistego rejestru encji: dwa dawne sensory pomocnicze są usuwane;
  główny sensor, niestandardowy wpis i encja innej platformy pozostają. Powtórne
  czyszczenie działa poprawnie.
- Pełny cykl życia HA pozostaje testowany przez workflow na Linuksie; lokalny
  test na Windows nie uruchamia docelowej instalacji HA.

# Walidacja 0.2.0 — 2026-11-02

- 44 testy: OK, w tym wspólne sortowanie kierunków, zachowanie nazw kierunków
  w atrybutach ZIM i kalendarzu, zgodność starej konfiguracji i nadpisanie
  kierunków w opcjach, pusty wybór i normalizacja kolejności.
- Test z klasami Home Assistant 2026.10.4: OK — formularz wielokrotnego wyboru,
  koordynator, 3 sensory, wspólny kalendarz i opcje istniejącego wpisu.
- Ruff, formatowanie, kompilacja modułów i składnia JSON: OK.
- Testy pełnego cyklu życia HA w `tests/ha/test_homeassistant.py` pozostają
  przeznaczone dla CI na Linuksie; nie uruchomiono ich na docelowym HA.
- Nie zmieniano konfiguracji działającej instalacji HA.

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
