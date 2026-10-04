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
LEFT, RIGHT = 64, 70   # gutters: tick labels on the left, the latest value on the right
PANEL_H = 170
HEAD_H = 28            # room above each panel for its name and legend
GAP = 26               # between panels
LABEL_H = 30           # season labels under the last panel


def compact(value):
    """A dollar figure short enough for an axis: $631M, $2.5M, $500K."""
    if value >= 1e6:
        return '$%sM' % ('%.1f' % (value / 1e6)).rstrip('0').rstrip('.')
    if value >= 1e3:
        return '$%dK' % round(value / 1e3)
    return '$%d' % value


def nice_step(maximum, target_ticks=4):
    """A clean tick step (1, 2, 2.5, 5 x 10^k) giving about target_ticks lines."""
    raw = maximum / target_ticks
    magnitude = 10 ** math.floor(math.log10(raw))
    for m in (1, 2, 2.5, 5, 10):
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


def series(name, css, rows, key, xs, base, scale):
    """One measure over the run: a line broken where a season has no value, a point per season."""
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
            'x': x, 'y': y, 'value': value,
            'url': reverse('season_detail', args=[row['competition__slug'], row['season']]),
            'title': '%s %s: $%s' % (row['season'], name.lower(), format(round(value), ',')),
        })
    return {'name': name, 'css': css, 'path': ''.join(path), 'points': points}


def panel(name, rows, measures, xs, top):
    """
    A panel of one or more measures on one scale. Measures sharing a panel
    share its scale, so they can be read against each other.
    """
    ceiling = max(float(r[key]) for r in rows for _, _, key in measures if r[key] is not None)
    step = nice_step(ceiling)
    y_max = step * math.ceil(ceiling / step)
    base = top + HEAD_H + PANEL_H
    scale = PANEL_H / y_max

    lines = [series(label, css, rows, key, xs, base, scale) for label, css, key in measures]

    # A panel of one measure is named by its title; more than one gets a legend.
    if len(lines) > 1:
        x = LEFT + len(name) * 7.5 + 28
        for line in lines:
            line['legend'] = {'x1': x, 'x2': x + 28, 'dot': x + 14, 'text_x': x + 36}
            x += 36 + len(line['name']) * 6.3 + 24

    # The latest value of each line is written at its end; the rest are a hover
    # or the table away. Where two ends would collide, the lower one gives way.
    ends = sorted(({'x': line['points'][-1]['x'] + 10, 'y': line['points'][-1]['y'],
                    'text': compact(line['points'][-1]['value'])} for line in lines),
                  key=lambda e: e['y'])
    for upper, lower in zip(ends, ends[1:]):
        lower['y'] = max(lower['y'], upper['y'] + 14)

    return {
        'name': name,
        'title_y': top + 16,
        'base': base,
        'ticks': [{'y': base - i * step * scale, 'text': compact(i * step)}
                  for i in range(round(y_max / step) + 1)],
        'lines': lines,
        'ends': ends,
    }


@register.inclusion_tag("money/_payroll_chart.html")
def payroll_chart(seasons):
    """
    League payroll, then average and median team payroll, then average and
    median player pay, each panel on a scale of its own. A club's payroll is a thirtieth of the league's, so a shared
    scale would flatten it against the baseline, and two scales on one plot
    would set the lines beside each other as if they could be compared.
    """
    rows = latest_run(seasons)
    if len(rows) < 3:
        return {}

    slot = (WIDTH - LEFT - RIGHT) / (len(rows) - 1)
    xs = [LEFT + i * slot for i in range(len(rows))]

    panels = [panel('League payroll', rows, [('League payroll', 'league', 'total')], xs, 0)]
    with_teams = [r for r in rows if r['team_average'] is not None]
    if len(with_teams) >= 3:
        panels.append(panel('Team payroll', rows,
                            [('Average club', 'average', 'team_average'),
                             ('Median club', 'median', 'team_median')],
                            xs, panels[-1]['base'] + GAP))
    panels.append(panel('Player pay', rows,
                        [('Average player', 'average', 'player_average'),
                         ('Median player', 'median', 'player_median')],
                        xs, panels[-1]['base'] + GAP))
    height = panels[-1]['base'] + LABEL_H

    every = max(1, math.ceil(44 / slot))  # label spacing so four-digit years never touch
    # Count back from the latest season, so the year the eye lands on is always named.
    labels = [{'x': x, 'text': r['season']}
              for i, (r, x) in enumerate(zip(rows, xs)) if (len(rows) - 1 - i) % every == 0]

    first, last = rows[0]['season'], rows[-1]['season']
    caption = 'League payroll is the pay of every player on record that season.'
    if len(with_teams) >= 3:
        caption += (' Team payroll is the pay of the players listed with a club: the average '
                    'splits it evenly across the clubs that have a squad on record, and the '
                    'median is the club in the middle.')
        if with_teams[0] is not rows[0]:
            caption += (' The record names no clubs before %s, so team payroll starts there.'
                        % with_teams[0]['season'])
    caption += (' Player pay is over every player on record; the median is the player in '
                'the middle, and the gap below the average is how far a few large salaries '
                'pull it up. Each panel has its own scale.')
    if len(rows) < len(seasons):
        caption += (' Seasons outside the unbroken run of %s–%s are in the table only.'
                    % (first, last))
    caption += ' Hover or focus a point for its figure.'

    return {
        'panels': panels,
        'labels': labels,
        'label_y': height - 10,
        'width': WIDTH,
        'height': height,
        'left': LEFT,
        'right_edge': WIDTH - RIGHT,
        'label': 'League payroll and team payroll by season, %s to %s' % (first, last),
        'caption': caption,
    }
