"""
Inline-SVG charts, one series in the site's accent, as soccerstats.us draws
them (../s2/competitions/templatetags/charts.py). The Python here does the
geometry; the template emits the markup. Every chart is followed by a table
carrying the same numbers, so nothing is only readable from the picture.
"""

import math

from django import template
from django.urls import reverse

register = template.Library()

WIDTH = 960
LEFT, RIGHT = 64, 70   # gutters: tick labels on the left, the end value on the right
PANEL_H = 170
TITLE_H = 26           # room above each panel for its name
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


def panel(name, rows, key, xs, top):
    """One measure over the run: gridlines, a line broken where a season has no value, a point per season."""
    values = [float(r[key]) if r[key] is not None else None for r in rows]
    ceiling = max(v for v in values if v is not None)
    step = nice_step(ceiling)
    y_max = step * math.ceil(ceiling / step)
    plot_top = top + TITLE_H
    base = plot_top + PANEL_H
    scale = PANEL_H / y_max

    path, points, drawing = [], [], False
    for row, x, value in zip(rows, xs, values):
        if value is None:
            drawing = False
            continue
        y = base - value * scale
        path.append('%s%.1f,%.1f' % ('L' if drawing else 'M', x, y))
        drawing = True
        points.append({
            'x': x, 'y': y,
            'url': reverse('season_detail', args=[row['competition__slug'], row['season']]),
            'title': '%s: $%s' % (row['season'], format(round(value), ',')),
        })

    return {
        'name': name,
        'title_y': top + 14,
        'base': base,
        'ticks': [{'y': base - i * step * scale, 'text': compact(i * step)}
                  for i in range(round(y_max / step) + 1)],
        'path': ''.join(path),
        'points': points,
        # Only the latest value is written on the chart; the rest are a hover or the table away.
        'end': {'x': points[-1]['x'] + 10, 'y': points[-1]['y'],
                'text': compact([v for v in values if v is not None][-1])},
    }


@register.inclusion_tag("money/_payroll_chart.html")
def payroll_chart(seasons):
    """
    League payroll and average team payroll by season, as two panels on one
    season axis. They share no y-axis: at thirty clubs the average is a
    thirtieth of the total and would lie flat along the baseline.
    """
    rows = latest_run(seasons)
    if len(rows) < 3:
        return {}

    slot = (WIDTH - LEFT - RIGHT) / (len(rows) - 1)
    xs = [LEFT + i * slot for i in range(len(rows))]

    panels = [panel('League payroll', rows, 'total', xs, 0)]
    with_teams = [r for r in rows if r['team_average'] is not None]
    if len(with_teams) >= 3:
        panels.append(panel('Average team payroll', rows, 'team_average', xs,
                            TITLE_H + PANEL_H + GAP))
    height = panels[-1]['base'] + LABEL_H

    every = max(1, math.ceil(44 / slot))  # label spacing so four-digit years never touch
    # Count back from the latest season, so the year the eye lands on is always named.
    labels = [{'x': x, 'text': r['season']}
              for i, (r, x) in enumerate(zip(rows, xs)) if (len(rows) - 1 - i) % every == 0]

    first, last = rows[0]['season'], rows[-1]['season']
    caption = ('League payroll is the pay of every player on record that season. '
               'Average team payroll is the pay of the players listed with a club, '
               'split evenly across the clubs that have a squad on record.')
    if len(panels) > 1 and with_teams[0] is not rows[0]:
        caption += (' The record names no clubs before %s, so the average starts there.'
                    % with_teams[0]['season'])
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
        'label': 'League payroll and average team payroll by season, %s to %s' % (first, last),
        'caption': caption,
    }
