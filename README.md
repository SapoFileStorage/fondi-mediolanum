# Monitor fondi Mediolanum

Dashboard statica (GitHub Pages) per seguire l'andamento giornaliero dei 5 fondi
Challenge, con aggiornamento automatico dei NAV via GitHub Actions.

## Struttura

| File | Cosa fa |
|---|---|
| `fetch_nav.py` | Scarica lo storico NAV dei 5 fondi da Morningstar → `data/nav_history.csv` |
| `.github/workflows/update-nav.yml` | Esegue lo script ogni mattina (lun–sab, ~9:30) e committa il CSV |
| `data/versamenti.csv` | **Lo compili tu**: una riga per ogni versamento (`data,isin,importo`) |
| `data/nav_history.csv` | Storico NAV, generato automaticamente — non toccarlo |
| `index.html` | La dashboard |

## Installazione (una volta sola)

1. Crea un nuovo repository su GitHub (es. `fondi-mediolanum`) e carica questi file
   (stessa procedura usata per `dashboard-saluggia`).
2. **Correggi le date in `data/versamenti.csv`**: ho messo `2026-06-02` come
   segnaposto — sostituiscila con le date reali dei tuoi versamenti da 420 €.
3. Tab **Settings → Pages** → Source: `main`, cartella `/ (root)` → Save.
4. Tab **Actions** → abilita i workflow se richiesto → apri "Aggiorna NAV fondi"
   → **Run workflow** per il primo popolamento dello storico.
5. Dopo 1–2 minuti apri `https://<tuo-utente>.github.io/fondi-mediolanum/`.

Test in locale (facoltativo): `python fetch_nav.py` e poi
`python -m http.server` nella cartella → http://localhost:8000
(la pagina va servita via http, aprendo il file direttamente il fetch dei CSV fallisce).

## Uso quotidiano

- **Non devi fare nulla**: il NAV si aggiorna da solo nei giorni feriali.
- **Quando fai un versamento**: apri `data/versamenti.csv` su GitHub (anche da
  telefono), tasto ✏️ Edit, aggiungi una riga per ogni fondo, Commit. Esempio:

  ```
  2026-08-01,IE0004460683,420.00
  2026-08-01,IE0004488262,420.00
  ...
  ```

## Note importanti

- I fondi hanno **NAV giornaliero**, pubblicato di norma il giorno lavorativo
  successivo: non esiste quotazione intraday, quindi la dashboard è
  "in tempo reale" nei limiti di ciò che il prodotto consente.
- Le quote sono **stimate** (importo ÷ NAV del primo giorno utile dopo il
  versamento) e non includono eventuali commissioni di sottoscrizione: per il
  controvalore ufficiale fa fede l'app Mediolanum. Se noti uno scarto sistematico,
  puoi ridurre gli importi in `versamenti.csv` al netto delle commissioni.
- Se Morningstar cambiasse i propri endpoint, lo script smetterebbe di trovare
  dati (il workflow fallisce, GitHub ti manda una mail): in quel caso va adattata
  la funzione di download a un'altra fonte (es. Borsa Italiana).
