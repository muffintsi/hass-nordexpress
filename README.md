# Nord Express — Home Assistant

[![Dodaj integrację do Home Assistant](https://my.home-assistant.io/badges/config_flow_start.svg)](https://my.home-assistant.io/redirect/config_flow_start/?domain=nordexpress)
[![Otwórz w HACS](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=muffintsi&repository=hass-nordexpress&category=integration)

Integracja rozkładów jazdy i prognoz odjazdów autobusów Nord Express dla Home Assistant.
Dane pochodzą z [kiedyPrzyjedzie](https://nordexpress.kiedyprzyjedzie.pl/).

- Obsługa wielu przystanków oraz wybranych linii i kierunków.
- Jeden sensor i osobny kalendarz odjazdów dla każdej wybranej linii.
- Najbliższy i kolejny kurs w atrybutach `BusHour`, `NextBusHour`, `NextBusTime`, `Direction` i `NextBusDirection`.
- Automatyczne odświeżanie oraz konfiguracja przez GUI Home Assistant.

## Instalacja przez HACS

1. W HACS otwórz **Własne repozytoria / Custom repositories**.
2. Dodaj `https://github.com/muffintsi/hass-nordexpress` jako **Integracja**.
3. Pobierz **Nord Express** i uruchom ponownie Home Assistant.
4. W **Ustawienia → Urządzenia i usługi → Dodaj integrację** wybierz **Nord Express**.

Instalacja ręczna: skopiuj katalog `custom_components/nordexpress` do katalogu `custom_components` w konfiguracji HA i uruchom ponownie Home Assistant.

## Konfiguracja

Wybierz przystanek, zaznacz linie i ustaw kierunki osobno dla każdej z nich.
Ten sam przystanek i linię można dodać ponownie z innym kierunkiem.

W opcjach integracji możesz zmienić linie, kierunki i liczbę dni w kalendarzu:
**1–14 dni**, domyślnie **7**. Kalendarz pokazuje rozkład planowy, a sensor uwzględnia dostępne prognozy.

## English

Home Assistant integration for Nord Express bus timetables and departure predictions.
Supports multiple stops, selected lines and destinations, with one sensor and a separate
calendar per line. Install through HACS as a custom **Integration** repository, restart
Home Assistant, then add **Nord Express** under **Settings → Devices & services**.
