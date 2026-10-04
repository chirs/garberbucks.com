def season_ranges(seasons):
    """
    Collapse season names into runs: 1996, 2004, 2005, 2006 -> "1996, 2004–2006".
    Seasons that are not a plain year stand alone.
    """
    runs = []
    for season in sorted(set(seasons)):
        if runs and season.isdigit() and runs[-1][1].isdigit() and int(season) == int(runs[-1][1]) + 1:
            runs[-1][1] = season
        else:
            runs.append([season, season])

    return ', '.join(a if a == b else '%s–%s' % (a, b) for a, b in runs)
