# ROADMAP.md — Development Roadmap

Open work only; completed items are removed as they land (see git history).

---

## Salary data

- [ ] MLS 2015–2026: transcribe the MLS Players Association salary guides into
  `money_data/salaries/mls/`. The site is ten years behind without them.
- [ ] MLS 1997–2003: find and transcribe whatever was published.
- [ ] MLS 1996 is 46 players with no clubs and no recorded source. Find the
  source; add the clubs.
- [ ] Clubs for 2004–2006. The press lists were by club and the transcription
  dropped them; failing the originals, infer a club from the player's stat line
  that season.
- [ ] Positions for 2011–2013, which the union lists carry.
- [ ] Spelling variants split one player into two (Amado Guevera, Dilaver Duka,
  Harrison Shipp). 156 salary names match no MLS stat line; alias the ones that
  are variants in `metadata`.
- [ ] `metadata.alias` maps "Aminu Abdallah" to "Aminu Abdallah*".
- [ ] The 1925 wage sits in season "1925"; ASL seasons straddle two years.
- [ ] Salaries before MLS: ASL, NASL and the rest, as sources turn up.

## Site

- [ ] Deploy to bert: gunicorn unit, nginx vhost, `upload.sh`, as s2 does it.
- [ ] Sortable tables.
- [ ] Player and team indexes, and search.
- [ ] A player's age each season; dollars per minute and per goal once season
  stats are loaded.
- [ ] Adjust for inflation, and show each salary against that season's cap.

## Beyond salaries

- [ ] Transaction rules: the salary budget, designated players, allocation
  money, the U22 initiative. Define them in prose first, then model them.
- [ ] Team valuations and expansion fees.
- [ ] Owners and their net worth.
- [ ] Other leagues: Liga MX, NASL, ASL, ALPF, then the big European five.
