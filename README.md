# Nord Express dla Home Assistant

Wersja 0.2.0. Nieoficjalna integracja rozkładów i prognoz odjazdów Nord Express
z `nordexpress.kiedyprzyjedzie.pl`. Konfiguracja z interfejsu HA, bez YAML i konta.

## Instalacja

1. Skopiuj katalog `custom_components/nordexpress` do
   `/config/custom_components/nordexpress` w Home Assistant.
2. Uruchom ponownie HA.
3. Otwórz **Ustawienia → Urządzenia i usługi → Dodaj integrację → Nord Express**.
4. Wybierz przystanek, linię i zaznacz jeden lub kilka kierunków.
   Przykład: 105 ze Słupska — **Główczyce + Cecenowo**. Kursy obu wariantów
   trafiają wspólnie do sensora i kalendarza, chronologicznie.
   Dla innego przystanku lub linii dodaj kolejny wpis integracji.

Archiwum instalacyjne zawiera katalog `custom_components` gotowy do wypakowania
w katalogu konfiguracji HA. Nie usuwa ani nie zastępuje starego pakietu YAML.
Po porównaniu nowych encji przełącz karty i automatyzacje, a następnie wyłącz stare
sensory Nord Express. Nowe encje mają własne identyfikatory.

## Aktualizacja z 0.1.0

Zastąp katalog komponentu wersją 0.2.0 i uruchom ponownie HA. Następnie otwórz
**Ustawienia → Urządzenia i usługi → Nord Express → Opcje** przy swoim wpisie
(na niektórych wersjach HA przycisk nazywa się „Konfiguruj”). Zaznacz np.
**Główczyce** i **Cecenowo**, po czym zapisz. Nie musisz usuwać wpisu ani ponownie
ustawiać kart: identyfikatory encji pozostają te same. Stare wpisy z pojedynczym
kierunkiem nadal działają. Zaznaczenie kilku kierunków nie dodaje nowych sensorów.

## Prezentacja zgodna z hass-zim-slupsk

Główny sensor ma nazwę `Linia 105 - Główczyce → Słupsk, Dworzec Autobusowy
(Nord Express)` i klasę `timestamp`. Stan oznacza najbliższy odjazd, a atrybuty
pasują do konwencji lokalnej integracji `hass-zim-slupsk`:

| Atrybut | Znaczenie |
|---|---|
| `BusHour` | Najbliższy odjazd, `HH:MM` |
| `Direction` | Rzeczywisty kierunek najbliższego odjazdu |
| `NextBusHour` | Następny odjazd, `HH:MM` |
| `NextBusTime` | Następny odjazd, `YYYY-MM-DD HH:MM` |
| `NextBusDirection` | Rzeczywisty kierunek następnego odjazdu |
| `line`, `stop_name`, `stop_code` | Linia i przystanek |
| `latitude`, `longitude` | Współrzędne przystanku |

W istniejącej karcie ZIM wystarczy wskazać nowy sensor. Zachowana jest wielkość
liter w nazwach atrybutów. Nie zmieniamy nazw własnych kierunków przez `capitalize()`.
Daty i skrócone godziny są w strefie przewoźnika `Europe/Warsaw`.

Dodatkowo dostępne są osobne sensory kolejnego odjazdu i minut do odjazdu.
Ich zegar odświeża się lokalnie co 15 sekund. `unknown` oznacza brak kursu
w skonfigurowanym horyzoncie; `unavailable` oznacza błąd pobierania rozkładu.

Kalendarz ma takie samo nazewnictwo jak sensor, tytuły `Linia 105 → Słupsk,
Dworzec Autobusowy` i zdarzenia trwające minutę, zgodnie z ZIM. Pokazuje **godziny
planowe**; sensory pokazują prognozy, jeśli API je udostępnia. Odwołane odjazdy
są pomijane. Kalendarze ZIM i Nord Express można umieścić na tej samej standardowej
karcie kalendarza HA.

W opcjach integracji ustaw **Liczba dni w kalendarzu**: 1–14, domyślnie 7.
Dni liczone są od dzisiaj włącznie. Aplikacja kiedyPrzyjedzie pozwala wybrać
dzisiaj + 13 dni; dlatego Nord Express ma mniejszy zakres niż 60 dni w ZIM.
Zapytania kalendarza są przycinane do tego okna i korzystają z pamięci, bez
dodatkowych odczytów HTTP. Opcje przeładowują wpis automatycznie.

Przykład karty (zastąp `sensor.twoja_encja_nord_express` rzeczywistym ID):

```yaml
type: markdown
content: >-
  {% set e = 'sensor.twoja_encja_nord_express' %}
  **{{ state_attr(e, 'line') }} → {{ state_attr(e, 'Direction') or '—' }}**

  Najbliższy: **{{ state_attr(e, 'BusHour') or '—' }}**

  Kolejny: {{ state_attr(e, 'NextBusTime') or '—' }}
```

## Dodatkowe dane i wiarygodność

Wybrane kierunki są w atrybucie `directions`. Każdy odjazd oraz tytuł wydarzenia
kalendarza zachowuje swój rzeczywisty kierunek, np. Główczyce lub Cecenowo.

Główny sensor udostępnia do 10 następnych kursów w `departures`, odwołane kursy
w `canceled_departures`, `realtime_available`, `realtime_timestamp` i `horizon_end`.
Każdy kurs opisują `scheduled`, `expected`, `estimated`, `canceled`, `at_stop`,
`platform`, `symbols`, `direction`, `trip_id`, `stop_index` i `display_time`.

`realtime_available` oznacza poprawną odpowiedź bieżącej tablicy przystankowej,
a nie obecność prognozy dla każdego kursu. To pole `estimated` określa pochodzenie
godziny konkretnego odjazdu. Przy awarii tablicy sensory przechodzą na poprawnie
pobrany rozkład i ustawiają `realtime_available: false`. Utrata dostępu do
rozkładu oznacza niedostępność encji, a nie pustą listę autobusów.

API publikuje prognozy jako `N min`, `< 1 min` lub `HH:MM`. Ich dokładność to
minuty. Integracja używa znacznika czasu serwera; nie obiecuje dokładności co do
sekundy. `< 1 min` oznacza kurs nadjeżdżający teraz. Nieznany format pozostawia
godzinę planową. Odpowiedzi starsze niż 120 sekund są odrzucane. Prognozy
powiązane są po kursie, indeksie przystanku, linii i najbliższej dacie, ponieważ
identyfikatory kursów powtarzają się między dniami.

Rozkład uwzględnia symbole wariantów (np. Cecenowo zamiast Słupska), sortowanie,
zmianę daty, dni bez kursów i godziny po 24:00 z poprzedniej daty kursowania.
API nie rozstrzyga powtórzonej godziny jesiennej zmiany czasu dla rozkładu
planowego: wybierane jest pierwsze wystąpienie. Nieistniejące godziny wiosenne
są pomijane. Prognozy względne liczone są w UTC.

## Pobieranie danych

Tablica odjazdów jest odczytywana co 30 sekund; wspólna pamięć podręczna
ogranicza wielokrotne zapytania dla tej samej relacji/przystanku. Jeden odczyt
przystanku obsługuje wszystkie skonfigurowane na nim linie. Używamy endpointu
pojedynczego przystanku, bo udostępnia znacznik czasu odpowiedzi.
Rozkłady są buforowane na godzinę osobno dla daty, przystanku i linii, a lista
przystanków na dobę. Zapytania są wykonywane sekwencyjnie, z limitem 15 sekund.
Pobierany jest też poprzedni dzień. Pierwsze dodanie relacji może potrwać chwilę.
Klient wysyła jawny identyfikator `HomeAssistant/NordExpress-0.1.0`; w teście
domyślny identyfikator Python/aiohttp zwracał HTTP 400, a ten nagłówek HTTP 200.

To API aplikacji pasażerskiej, bez publicznego wersjonowanego kontraktu.
Zmiana formatu po stronie dostawcy może wymagać aktualizacji integracji.
Nie znaleziono potwierdzonego oficjalnego GTFS Nord Express.

## Walidacja i rozwój

Testy klienta, modelu, prezentacji ZIM i kalendarza, bez uruchamiania HA:

```sh
python -m pip install -r requirements-test.txt
python -m unittest discover -s tests -v
python -m compileall -q custom_components
```

Testy kontraktu HA znajdują się w `tests/ha` i są przeznaczone dla Linux/Pythona
obsługiwanego przez aktualny Home Assistant. CI instaluje
`pytest-homeassistant-custom-component` i uruchamia je osobno. Lokalna walidacja
na Windows nie zastępuje uruchomienia integracji w prawdziwym HA.
Z rzeczywistymi bibliotekami HA 2026.10.4 przeszedł dodatkowo test
`python tests/ha/runtime_smoke.py` obejmujący formularze, koordynator, sensory
i kalendarz bez uruchamiania serwera. Szczegóły: `docs/VALIDATION.md`.

Publiczne próbki API z 2026-11-02 są w `tests/fixtures`. Testy nie korzystają
z sieci. Opis źródeł i audytu: `docs/AUDIT.md`.
