# ROADMAP.md — Development Roadmap

Open work only; completed items are removed as they land (see git history).

---

## Salary data

- [ ] Take each new guide as it comes out: 2026 is the spring list and the fall
  one replaces it.
- [ ] Both releases a year, not one: a player signed in the summer window is in
  the fall guide only, one sold in it is in the spring guide only.
- [ ] MLS 1997–2003: find and transcribe whatever was published.
- [ ] MLS 1996 is 46 players with no clubs and no recorded source. Find the
  source; add the clubs.
- [ ] Clubs for 2004–2006. The press lists were by club and the transcription
  dropped them; failing the originals, infer a club from the player's stat line
  that season.
- [ ] Spelling variants split one player into two (Amado Guevera, Dilaver Duka,
  Benjamin and Benji Kikanović). About one salary name in six matches no MLS
  stat line that season; some never played, the rest need aliases in `metadata`.
- [ ] Take positions from MLSsoccer.com's season stats, which will override the
  union's. The salary guides' positions (letter codes through 2023, named roles
  from 2024, grouped in the build's normalize stage) are a stopgap, and
  1996 and 2004–2006 have none.
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

## Transfers

- [ ] Load `money_data/transfers/`: a parser in `parse`, the mongo build, a
  `Transfer` model, and pages by season, club and player. The data is a first
  pass of 181 reported fees and is not on the site.
- [ ] Widen the first pass. It only holds deals whose fee is stated in the
  `oneonta` news archive, which is thin before 2025: Davies to Bayern, Almirón
  to Newcastle and most of 2015–2021 are missing.
- [ ] Deals passed over because the article did not name the other club:
  Jonathan Pérez to Nashville, Nicolás Dubersarsky, Djé D'Avilla, Sanabria.
- [ ] Sell-on clauses and the money they later paid (Aaronson, Pepi, Reynolds).

## Beyond salaries

- [ ] Transaction rules: the salary budget, designated players, allocation
  money, the U22 initiative. Define them in prose first, then model them.
- [ ] Team valuations and expansion fees.
- [ ] Owners and their net worth.
- [ ] Other leagues: Liga MX, NASL, ASL, ALPF, then the big European five.
