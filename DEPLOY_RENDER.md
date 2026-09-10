# Nasazení Rodinného finančního kompasu na Render

Tento návod je pro poslední hotovou online verzi. Funkce aplikace se kvůli nasazení nemění.

## Co je připravené

- `render.yaml` vytvoří webovou službu a PostgreSQL databázi.
- `DATABASE_URL` se propojí automaticky.
- `SESSION_SECRET` se vygeneruje automaticky.
- zdravotní kontrola je `/api/health`.
- aplikace používá serverovou databázi, historii a bodové zálohy.

## Postup

1. Nahrajte celý obsah tohoto projektu do soukromého GitHub repozitáře.
2. Na Renderu zvolte **New → Blueprint** a připojte tento repozitář.
3. Render načte `render.yaml`.
4. Zkontrolujte, že region je Frankfurt.
5. Vytvořte služby.
6. Po nasazení otevřete adresu webové služby a vytvořte první rodinný účet.

## Před prvním skutečným používáním

Proveďte tento test:

1. Vytvořit domácnost.
2. Přidat dalšího člena.
3. Přihlásit se jako první člen.
4. Přidat výdaj.
5. Otevřít Kompas z jiného zařízení/prohlížeče.
6. Přihlásit se do stejné domácnosti.
7. Ověřit, že výdaj vidí i druhé zařízení.
8. Výdaj upravit.
9. Výdaj smazat.
10. Použít „Vrátit zpět“.
11. Ověřit Historii změn.
12. Obnovit starší stav.

## Důležité

Aplikace už má vlastní historii a bodové zálohy. Pro skutečná produkční data je ale vhodné používat placenou PostgreSQL službu s podporovanou obnovou databáze a pravidelně kontrolovat, že záloha jde skutečně obnovit.

Před veřejným spuštěním je ještě potřeba doplnit obnovu zapomenutého hesla přes e-mail. Tato funkce není v této verzi předstíraná ani nahrazena nebezpečným posíláním hesla e-mailem.
