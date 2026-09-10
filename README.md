# Rodinný finanční kompas – online verze

Tato verze je připravená pro skutečné nasazení: přihlášení přes server, jeden společný účet domácnosti, až 20 členů, sdílená data, označení autora výdaje, serverová historie a automatická bodová záloha před každým uložením.

## Co už je zapojené
- účet domácnosti: e-mail zakladatele + název domácnosti + rodinné uživatelské jméno + společné heslo,
- každý člen má vlastní jméno a při přihlášení se vybere,
- maximálně 20 členů,
- data se ukládají na PostgreSQL server, ne do localStorage,
- změny se posílají na server po každé úpravě,
- před každým uložením se uloží předchozí stav do tabulky záloh,
- historie změn a obnovení staršího stavu,
- oprávnění jsou vázaná na konkrétní domácnost,
- hesla se ukládají pouze jako bcrypt hash,
- ochranné hlavičky a omezení pokusů o přihlášení,
- HTTPS je očekávané v produkci.

## Co je ještě potřeba před veřejným spuštěním
1. Nasadit aplikaci na hosting a připojit PostgreSQL. Pro Render je připravený `render.yaml` a `DEPLOY_RENDER.md`.
2. HTTPS na hostingu.
3. Skutečná pravidelná záloha PostgreSQL mimo hlavní server / managed backup.
4. E-mailová obnova hesla – tato verze ji zatím záměrně nepředstírá.
5. Nastavit `DATABASE_SSL` podle konkrétního poskytovatele databáze.
6. Po nasazení udělat test přihlášení, synchronizace, smazání, vrácení a obnovy historie.

## Lokální spuštění
```bash
npm install
npm start
```

Nebo:
```bash
docker compose up --build
```

Po spuštění otevřete web serveru. Bez PostgreSQL a proměnných prostředí se server nespustí.
