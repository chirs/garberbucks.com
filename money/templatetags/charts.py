"""
Inline-SVG charts, drawn the way soccerstats.us draws them
(../s2/competitions/templatetags/charts.py). The Python here does the geometry;
the template emits the markup. Every chart is followed by a table carrying the
same numbers, so nothing is only readable from the picture.
"""

import math

from django import template
from django.urls import reverse

register = template.Library()

WIDTH = 960
LEFT, RIGHT = 64, 64   # gutters: the league scale on the left, the club scale on the right
TOP = 40               # the legend sits above the plot
PLOT_H = 300
LABEL_H = 30           # season labels under the plot
INTERVALS = 4          # both scales are cut into the same intervals, so they share gridlines


def compact(value):
    """A dollar figure short enough for an axis: $631M, $2.5M, $500K."""
    if value >= 1e6:
        return '$%sM' % ('%.1f' % (value / 1e6)).rstrip('0').rstrip('.')
    if value >= 1e3:
        return '$%dK' % round(value / 1e3)
    return '$%d' % value


def nice_step(maximum, intervals=INTERVALS):
    """The smallest clean step that reaches maximum in the given number of intervals."""
    raw = maximum / intervals
    magnitude = 10 ** math.floor(math.log10(raw))
    for m in (1, 1.5, 2, 2.5, 3, 4, 5, 6, 8, 10):
        if m * magnitude >= raw:
            return m * magnitude


def latest_run(seasons):
    """
    The latest unbroken run of annual, year-named seasons, oldest first. A line
    drawn across a missing season would claim to know what happened in it.
    """
    rows = sorted((s for s in seasons if s['period'] == 'year' and s['season'].isdigit()),
                  key=lambda s: int(s['season']))
    run = []
    for row in rows:
        if run and int(row['season']) != int(run[-1]['season']) + 1:
            run = []
        run.append(row)
    return run


def series(name, css, rows, key, xs, base, step):
    """One measure over the run: a line broken where a season has no value, a point per season."""
    scale = PLOT_H / (step * INTERVALS)
    path, points, drawing = [], [], False
    for row, x in zip(rows, xs):
        if row[key] is None:
            drawing = False
            continue
        value = float(row[key])
        y = base - value * scale
        path.append('%s%.1f,%.1f' % ('L' if drawing else 'M', x, y))
        drawing = True
        points.append({
            'x': x, 'y': y,
            'url': reverse('season_detail', args=[row['competition__slug'], row['season']]),
            'title': '%s %s: $%s' % (row['season'], name.lower(), format(round(value), ',')),
        })
    return {'name': name, 'css': css, 'path': ''.join(path), 'points': points}


@register.inclusion_tag("money/_payroll_chart.html")
def payroll_chart(seasons):
    """
    League payroll against the left scale; average and median team payroll
    against the right. At thirty clubs a club's payroll is a thirtieth of the
    league's and would lie flat along the baseline of a shared scale, so each
    side has its own, and the legend says which line reads against which.
    """
    rows = latest_run(seasons)
    if len(rows) < 3:
        return {}

    base = TOP + PLOT_H
    right_edge = WIDTH - RIGHT
    slot = (right_edge - LEFT) / (len(rows) - 1)
    xs = [LEFT + i * slot for i in range(len(rows))]

    league_step = nice_step(max(float(r['total']) for r in rows))
    lines = [series('League payroll', 'league', rows, 'total', xs, base, league_step)]
    lines[0]['scale'] = 'left scale'

    with_teams = [r for r in rows if r['team_average'] is not None]
    team_step = None
    if len(with_teams) >= 3:
        team_step = nice_step(max(float(max(r['team_average'], r['team_median']))
                                  for r in with_teams))
        for name, css, key in (('Average team payroll', 'average', 'team_average'),
                               ('Median team payroll', 'median', 'team_median')):
            line = series(name, css, rows, key, xs, base, team_step)
            line['scale'] = 'right scale'
            lines.append(line)

    ticks = []
    for i in range(INTERVALS + 1):
        ticks.append({
            'y': base - i * PLOT_H / INTERVALS,
            'left': compact(i * league_step),
            'right': compact(i * team_step) if team_step else '',
        })

    # The legend runs along the top: a sample of each line, its name, its scale.
    x = LEFT
    for line in lines:
        line['legend'] = {'x1': x, 'x2': x + 28, 'dot': x + 14, 'text_x': x + 36,
                          'text': '%s, %s' % (line['name'], line['scale'])}
        x += 36 + len(line['legend']['text']) * 6.3 + 28

    every = max(1, math.ceil(44 / slot))  # label spacing so four-digit years never touch
    # Count back from the latest season, so the year the eye lands on is always named.
    labels = [{'x': x, 'text': r['season']}
              for i, (r, x) in enumerate(zip(rows, xs)) if (len(rows) - 1 - i) % every == 0]

    first, last = rows[0]['season'], rows[-1]['season']
    caption = ('League payroll, read against the left scale, is the pay of every '
               'player on record that season.')
    if team_step:
        caption += (' Team payroll, read against the right scale, is the pay of the players '
                    'listed with a club: the average splits it evenly across the clubs that '
                    'have a squad on record, and the median is the club in the middle. Where '
                    'the lines cross means nothing; the two scales are unrelated.')
        if with_teams[0] is not rows[0]:
            caption += (' The record names no clubs before %s, so team payroll starts there.'
                        % with_teams[0]['season'])
    if len(rows) < len(seasons):
        caption += (' Seasons outside the unbroken run of %s–%s are in the table only.'
                    % (first, last))
    caption += ' Hover or focus a point for its figure.'

    return {
        'lines': lines,
        'ticks': ticks,
        'labels': labels,
        'legend_y': 14,
        'label_y': base + LABEL_H - 10,
        'width': WIDTH,
        'height': base + LABEL_H,
        'left': LEFT,
        'right_edge': right_edge,
        'base': base,
        'label': 'League payroll and team payroll by season, %s to %s' % (first, last),
        'caption': caption,
    }
