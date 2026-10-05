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

- [ ] Sortable tables.
- [ ] Player and team indexes, and search.
- [ ] A player's age each season; dollars per minute and per goal once season
  stats are loaded.
- [ ] A favicon. The header silhouette is a blob at 16px, so it needs its own
  mark.

## Transfers

- [ ] Widen the first pass. It only holds deals whose fee is stated in the
  `oneonta` news archive, which holds MLSsoccer.com only from 2024: most of
  2015–2021 is missing. Backfilling MLSsoccer.com further (2013 on) would fill it.
- [ ] Deals passed over because the article did not name the other club:
  Jonathan Pérez to Nashville, Nicolás Dubersarsky, Djé D'Avilla, Sanabria.
- [ ] Sell-on clauses and the money they later paid (Aaronson, Pepi, Reynolds).

## Sponsorships

- [ ] Fill the gaps: naming-rights and shirt deals before about 2015, the
  undisclosed current deals (Q2, Subaru, Carvana, Target, Yeti, Nationwide),
  sleeve patches, training grounds.

## TV rights

- [ ] Local TV deals for clubs other than the two LA clubs, 1996–2022 (Seattle's
  JOEtv and KCPQ, Toronto and Montreal, the Red Bulls on MSG, Chicago on WGN).
- [ ] Figures for MLS 1999–2006, the 2023 Fox, TelevisaUnivision and TSN deals,
  and the Canadian deals from 2007; the NASL's TVS, ESPN and USA Network deals.
- [ ] Split the 2007–2022 deals between MLS and U.S. Soccer where a report does.
- [ ] Other leagues: the NPSL's 1967 CBS deal, USL, NWSL.

## Beyond salaries

- [ ] Salary budgets for 1997–2005 and 2009, and allocation money before 2015.
  The league's rules page is archived only from 2011, the Fraser testimony
  covers 1996, and media guides of the era print the rules without figures;
  archived mlsnet.com releases or newspapers are what is left.
- [ ] Owners' net worths before 2017: a Forbes profile's wealth history shows its
  last ten lists, so older archived captures of each profile would reach back
  further. Clark Hunt's profile has no history; only 2024 is on record.
- [ ] Rules not yet on record: the U22 Initiative slots, the third-DP fee, the
  homegrown subsidy, and the 2025 cash-for-GAM conversion. Define them in prose
  first, then model what can be.
- [ ] A club's own budget position: payroll against the salary budget, its DPs,
  and the allocation money it traded for, season by season.
- [ ] Ownership: more sales with figures (Seattle's 2019 group and its 2026
  raise, Portland, Minnesota's partners, LAFC's earlier stake sales, Nashville's
  minority investors), exact dates rather than years, and stakes for the
  operators file.
- [ ] NASL ownership: the first pass is in; fill operator years and owners for
  the clubs with none (Kansas City Spurs, Washington Darts, Denver Dynamos,
  Tulsa Roughnecks, Toronto Blizzard before 1979) and more sale prices.
- [ ] ASL ownership, 1921–1933.
- [ ] Owners' net worth.
- [ ] Forbes's MLS valuations before 2008 and for 2014, if any were published;
  Sportico's 2023, if it exists. Forbes 2008 and 2019 come from write-ups of the
  lists, not Forbes's own pages; replace them if the tables turn up.
- [ ] Other leagues: Liga MX, NASL, ASL, ALPF, then the big European five.

## Staff

- [ ] U.S. Soccer's and the union's 990s before 2014: the IRS has only the
  e-filed years; earlier ones are scanned PDFs on Nonprofit Explorer (Gulati's,
  Bradley's and Arena's first terms, the union's first decade).
- [ ] MLS executives beyond Garber's one reported contract, from the press.
- [ ] Referees: per-match fees and retainers from the PSRA agreements with PRO.
- [ ] MLS coaches and general managers, as reported, like the NASL salaries.

## Stadiums

- [ ] Public money for the 21 stadiums without it on record: land, bonds,
  infrastructure and tax breaks (Commerce City's $65M bond, Kansas's STAR
  bonds, Orange County's tourist tax, Harrison's land for Red Bull Arena).
- [ ] The big renovations: BMO Field 2016, Providence Park 2019, Stade Saputo
  2012, BC Place 2011.
- [ ] Nu Stadium (2026) and Etihad Park (2027, $780M) when their costs are
  reported as built.

## Deferred

- Inflation adjustment: ruled out; every figure stays in dollars of the day.
