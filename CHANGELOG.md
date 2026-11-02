# Zmiany

## 0.3.0 — 2026-11-02

- Wybór kilku linii po wskazaniu przystanku.
- Kierunki wybierane oddzielnie dla każdej zaznaczonej linii.
- Możliwość ponownego dodania tego samego przystanku i linii dla kierunku przeciwnego.
- Jeden sensor i kalendarz na wybraną linię, kolejne kursy w atrybutach jak w ZIM.
- Opcje pozwalające zmienić linie i kierunki z zachowaniem ID istniejących linii.
- Automatyczne usunięcie zbędnych sensorów pomocniczych i encji odznaczonych linii.

## 0.2.1 — 2026-11-02

- Jeden sensor na wpis, zgodnie z prezentacją ZIM Słupsk.
- Kolejny kurs w NextBusHour, NextBusTime i NextBusDirection.
- Krótsze nazwy sensora i kalendarza: Linia 105 - Główczyce.
- Automatyczne usunięcie wycofanych sensorów pomocniczych z rejestru HA.
- Zachowanie identyfikatora głównej encji oraz obsługi wielu kierunków.

## 0.2.0 — 2026-11-02

- Wybór kilku kierunków w jednej konfiguracji, np. Główczyce + Cecenowo dla 105.
- Wspólny, chronologiczny sensor i kalendarz z kierunkiem każdego kursu.
- Edycja kierunków przez opcje bez zmiany identyfikatorów encji.
- Zgodność ze starymi wpisami z pojedynczym kierunkiem.
- Walidacja pustego wyboru i duplikatów zestawów kierunków.

## 0.1.0 — 2026-11-02

- Konfiguracja przystanku, linii i kierunku z GUI Home Assistant.
- Rozkład i prognozy z kiedyPrzyjedzie, wspólna pamięć podręczna.
- Główny sensor z atrybutami zgodnymi z hass-zim-slupsk.
- Sensory kolejnego odjazdu i minut do odjazdu.
- Kalendarz planowych odjazdów, opcja 1–14 dni.
- Obsługa wariantów tras, odwołań, zmiany daty i awarii źródła.
- Polskie i angielskie tłumaczenia, testy i dokumentacja.
