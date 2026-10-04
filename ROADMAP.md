# ROADMAP.md — Development Roadmap

Open work only; completed items are removed as they land (see git history).

---

## Salary data

- [ ] MLS 2007–2014 from the union's own guides. It publishes a fall guide for
  each of those years; the files on hand are older transcriptions (2014 is the
  April list) with no recorded source for 2007–2013. Retranscribing gives every
  season the same release, a source, and positions throughout.
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
- [ ] Positions are letter codes through 2023 and spelled out from 2024. Pick
  one vocabulary.
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
