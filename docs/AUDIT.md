# Audyt Nord Express — 2026-11-02

Zakres: odczyt dostarczonego `nordexpress.yaml`, publicznej strony Nord Express,
aplikacji kiedyPrzyjedzie, jej kodu frontendowego i wybranych odpowiedzi JSON.
Nie wykonywano audytu bezpieczeństwa ani testów ingerujących w usługę.

Źródła:

- https://nordexpress.pl/rozklad-jazdy/
- https://nordexpress.pl/rozklad-jazdy/rozklady-jazdy-105/
- https://nordexpress.pl/rozkladynew/start-105_20261012-1.html
- https://nordexpress.kiedyprzyjedzie.pl/
- https://contributors.home-assistant.io/core/integrations/fetching-data/
- https://contributors.home-assistant.io/core/integrations/config-flow/

Strona WordPress osadza wersjonowane tabele HTML. kiedyPrzyjedzie udostępnia
czytelniejsze źródło JSON bez logowania. Potwierdzone odczyty:

| Endpoint | Wynik |
|---|---|
| `/stops` i `/stops?rev=1124` | HTTP 200, 399 pozycji |
| `/api/directions/{place_id}?date=YYYY-MM-DD` | Linie, kierunki, pełne ID |
| `/api/timetable/{place_id}/{base64url(line)}?date=YYYY-MM-DD` | Rozkład, warianty, indeks kursu |
| `/api/departures/{place_id}` | Tablica bieżąca z timestamp, prognozami i odwołaniami |
| `/api/departures?places=ID,ID` | Odczyt zbiorczy, bez timestamp w sprawdzonej odpowiedzi |

Pełny identyfikator zawiera dwie części, np. `1301499:1360809`. Pierwsza część
samodzielnie nie wystarcza do odczytu tablicy. Przykładowe błędy przy niepełnych
ID nie oznaczają braku funkcji w usłudze.

Przystanki z YAML: `1301499:1360809` — Słupsk, Wiejska 03 (105),
`1915047:1360822` — Słupsk, Kaszubska - Cmentarz 01 (101),
`1301410:1360673` — Główczyce (101 i 105).

Problemy YAML: odczyt co 12 godzin bez zmiany bufora o północy, stałe `OK`, brak
rozróżnienia awarii i braku kursów, pomijanie symboli wariantów kierunku, brak
prognoz i odwołań, powielona logika, brak przejścia do kolejnego dnia z kursami.
Przykład potwierdzony odpowiedzią z 2026-11-02: 105 z Główczyc o 08:46 ma symbol
`A` (Cecenowo), chociaż `main_direction` wskazuje Słupsk.

Frontend odświeża tablicę co 15 sekund, a wybór dnia ogranicza do wczoraj oraz
dzisiaj + 13 dni. Integracja używa interwału 30 sekund i maksymalnie 14 dni
kalendarza. Nie znaleziono publicznej gwarancji dostępności ani stabilności API.

Spójność prezentacji ustalono na podstawie lokalnych `sensor.py`, `calendar.py`,
`const.py` i README repo `hass-zim-slupsk` (odczyt 2026-11-02). Zachowano nazwy
atrybutów głównego sensora i format wydarzeń kalendarza. Kod Nord Express jest
osobnym komponentem, bez zmian w ZIM.
