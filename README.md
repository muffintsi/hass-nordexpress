# Nord Express dla Home Assistant

Wersja 0.3.0. Nieoficjalna integracja rozkładów i prognoz Nord Express z
`nordexpress.kiedyprzyjedzie.pl`. Konfiguracja przez interfejs HA, bez YAML i konta.

## Instalacja

1. Skopiuj `custom_components/nordexpress` do `/config/custom_components/nordexpress`.
2. Uruchom ponownie Home Assistant.
3. Wybierz **Ustawienia → Urządzenia i usługi → Dodaj integrację → Nord Express**.
4. Wybierz przystanek.
5. Zaznacz jedną lub kilka linii, które chcesz dodać.
6. Dla każdej zaznaczonej linii osobno wybierz kierunki, które mają być pokazywane razem.

Każda wybrana linia daje **jeden sensor i jeden kalendarz**. Nie powstają osobne
sensory kolejnego odjazdu ani minut do odjazdu. Niezaznaczone linie nie są dodawane.

## Osobne kierunki na tym samym przystanku

Każdy wpis jest niezależną grupą. Możesz ponownie wybrać **ten sam przystanek
oraz tę samą linię** i wskazać inny kierunek. Przykład dla przystanku obsługującego
obie strony trasy:

- Pierwszy wpis: przystanek → 105 → **Główczyce + Cecenowo**.
- Drugi wpis: ten sam przystanek → 105 → **Słupsk**.

Powstaną niezależne sensory i kalendarze. Kierunek przeciwny nie jest dopisywany
automatycznie. Łączone są wyłącznie kierunki świadomie zaznaczone w danym wpisie.
Identyczny zestaw linii i kierunków na tym samym przystanku jest wykrywany jako
duplikat. Dostępne kierunki zależą od danych rzeczywistego przystanku.

Jeżeli dwa sensory mają tę samą krótką nazwę, ich grupę rozpoznasz po tytule wpisu,
nazwie urządzenia i atrybutach `directions`. Nazwę sensora możesz też ustawić w HA.

## Aktualizacja istniejącej instalacji

Zastąp pliki komponentu wersją 0.3.0 i uruchom ponownie HA. Dotychczasowe wpisy
z jedną linią nadal działają, a główny sensor oraz kalendarz zachowują swoje ID.
Dwa dawne sensory pomocnicze są automatycznie usuwane z rejestru HA.

W **Nord Express → Opcje / Konfiguruj** możesz zmienić zaznaczone linie, liczbę dni
oraz kierunki osobno dla każdej linii. Dodanie kolejnej linii tworzy dodatkową parę
sensor/kalendarz. Odznaczenie linii usuwa jej encje z rejestru. Zachowane linie
utrzymują identyfikatory. Stare osobne wpisy nie są automatycznie łączone.

Pakiet YAML i istniejące dashboardy nie są modyfikowane przez integrację.

## Prezentacja zgodna z hass-zim-slupsk

Sensor ma krótką nazwę, np. **Linia 105 - Główczyce**, ikonę `mdi:bus` i klasę
`timestamp`. Stan to najbliższy odjazd. Następny kurs znajduje się w atrybutach:

| Atrybut | Znaczenie |
|---|---|
| `BusHour` | Najbliższy odjazd, `HH:MM` |
| `Direction` | Kierunek najbliższego odjazdu |
| `NextBusHour` | Kolejny odjazd, `HH:MM` |
| `NextBusTime` | Kolejny odjazd, `YYYY-MM-DD HH:MM` |
| `NextBusDirection` | Kierunek kolejnego odjazdu |
| `line`, `stop_name`, `stop_code` | Linia i przystanek |
| `latitude`, `longitude` | Współrzędne przystanku |

W karcie ZIM wystarczy wskazać nowy sensor. Atrybuty zachowują wielkość liter.
Godziny są prezentowane w strefie przewoźnika `Europe/Warsaw`.

Kalendarz ma tę samą krótką nazwę, tytuły **Linia 105 → kierunek** i minutowe
wydarzenia, tak jak w ZIM. Każdy kurs zachowuje właściwy kierunek. Kalendarz
pokazuje godziny planowe; sensor używa prognozy, jeśli jest dostępna. Odwołane
kursy są pomijane. Można użyć wspólnej standardowej karty kalendarza dla ZIM i Nord Express.

Liczba dni: **1–14**, domyślnie 7, od dzisiaj włącznie. Zakres odpowiada wyborowi
daty w kiedyPrzyjedzie. Zapytania kalendarza są przycinane do tego okna i nie
powodują dodatkowego pobierania HTTP. `unknown` oznacza brak kursu w tym oknie;
`unavailable` oznacza nieudane pobranie rozkładu.

Przykład karty; zastąp identyfikator rzeczywistą encją:

```yaml
type: markdown
content: >-
  {% set e = 'sensor.twoja_encja_nord_express' %}
  **{{ state_attr(e, 'line') }} → {{ state_attr(e, 'Direction') or '—' }}**

  Najbliższy: **{{ state_attr(e, 'BusHour') or '—' }}**

  Kolejny: {{ state_attr(e, 'NextBusTime') or '—' }}
```

## Dane i pobieranie

`directions` opisuje wybraną grupę kierunków. `departures` zawiera do 10 kolejnych
kursów, a `canceled_departures` kursy odwołane. Każdy odjazd ma m.in. `scheduled`,
`expected`, `estimated`, `canceled`, `at_stop`, `platform`, `direction`, `trip_id`
i `stop_index`. Dodatkowe atrybuty: `realtime_available`, `realtime_timestamp`,
`horizon_end`.

`realtime_available` oznacza dostępność bieżącej tablicy; `estimated` mówi, czy
konkretny odjazd ma prognozę. Przy awarii tablicy używany jest rozkład i
`realtime_available: false`. Awaria rozkładu powoduje niedostępność encji.

API podaje prognozy jako `N min`, `< 1 min` i `HH:MM`. Dokładność to minuty;
`< 1 min` oznacza kurs nadjeżdżający teraz. Podstawą obliczeń jest timestamp
serwera, a odpowiedzi starsze niż 120 sekund są odrzucane. Nieznany format
pozostawia godzinę planową. Kursy dopasowywane są po linii, trip_id, indeksie
przystanku i najbliższej dacie, ponieważ identyfikatory powtarzają się między dniami.

Tablica odczytywana jest co 30 sekund, z pamięcią podręczną współdzieloną przez
linie i wpisy. Rozkład jest buforowany na godzinę osobno dla daty/przystanku/linii;
przystanki na dobę. Pobierany jest też poprzedni dzień dla godzin po 24:00.
Pierwsza konfiguracja kilku linii może potrwać chwilę. Czasowy limit zapytania
wynosi 15 sekund. Stan sensora jest też odświeżany lokalnie co 15 sekund.

Uwzględniane są symbole wariantów kierunku, odwołania, sortowanie i zmiana daty.
Planowe nieistniejące godziny wiosenne są pomijane, a przy podwójnej godzinie
jesiennej wybierane jest pierwsze wystąpienie, bo API nie udostępnia rozstrzygnięcia.
Prognozy względne liczone są w UTC.

To API aplikacji pasażerskiej bez publicznego wersjonowanego kontraktu. Zmiana
formatu u dostawcy może wymagać aktualizacji komponentu. Nie znaleziono
potwierdzonego oficjalnego GTFS Nord Express.

## Walidacja i rozwój

```sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python -m compileall -q custom_components
```

Dodatkowy test z rzeczywistymi bibliotekami Home Assistant 2026.10.4:
`python tests/ha/runtime_smoke.py`. Test obejmuje wybór wielu linii, powtórne
dodanie przystanku i linii z kierunkiem przeciwnym, encje, opcje i czyszczenie
rejestru. Nie uruchamia serwera ani nie pobiera publicznych danych.

Pełny cykl życia HA jest opisany testami w `tests/ha/test_homeassistant.py`,
przeznaczonymi dla CI na Linuksie. Test lokalny nie zastępuje odbioru w docelowym HA.
Szczegóły: `docs/VALIDATION.md`, audyt: `docs/AUDIT.md`.
