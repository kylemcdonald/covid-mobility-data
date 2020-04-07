import numpy as np

import re
import os
import subprocess
from datetime import date, timedelta
from itertools import cycle

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('input_fn', type=str)
parser.add_argument('--days_per_plot', type=int, default=43)
args = parser.parse_args()

start_date = date(2020, 2, 16)
days_per_plot = args.days_per_plot

def points_inside(plot, box):
    t,b,l,r = box
    return (plot[:,0] >= l) & (plot[:,0] <= r) & \
         (plot[:,1] >= t) & (plot[:,1] <= b)

def chunks(lst, n):
    for i in range(0, len(lst), n):
        yield lst[i:i + n]
        
def get_region(pdf_fn):
    txt_fn = '.pdftotext.txt'
    err = subprocess.call(['pdftotext', '-f', '1', '-l', '1', pdf_fn, txt_fn])
    if err:
        return
    with open(txt_fn) as f:
        text = f.read()
    os.remove(txt_fn)
        
    region = text.splitlines()[2]
    region = region.split(' ')[:-3] # remove date
    region = ' '.join(region)
    return region

def list_subregions(pdf_fn):
    txt_fn = '.pdftotext.tmp'
    err = subprocess.call(['pdftotext', '-f', '3', pdf_fn, txt_fn])
    if err:
        return
    with open(txt_fn) as f:
        text = f.read()
    os.remove(txt_fn)

    ignore = [
        'Retail & recreation',
        'Grocery & pharmacy',
        'Parks',
        'Transit stations',
        'Workplace',
        'Residential',
        'Not enough data for this date',
        'needs a significant volume of data to generate an aggregated and anonymous view of trends.',
    ]
    
    for line in text.splitlines():
        line = line.strip()

        if len(line) == 0:
            continue
        if line.startswith('Sun '):
            continue
        if line.endswith('%'):
            continue
        if line.startswith('*'):
            continue
        if line.endswith('aseline'):
            continue
        if line in ignore:
            continue

        if line == 'About this data':
            break

        yield line

def build_tracking_areas(xs, ys):
    tracking_areas = []
    for top,bottom in zip(ys,ys[1:]):
        for left,right in zip(xs,xs[1:]):
            tracking_areas.append((top,bottom,left,right))
    return tracking_areas

polyline_re = re.compile(r'((?:[-\d.]+[\n ]+[-\d.]+[\n ]+[lm][\n ]+)+)S Q', re.DOTALL)
def extract_plots_and_ticks(page):
    ticks = []
    plots = []
    matches = polyline_re.findall(page)
    for j, match in enumerate(matches):
        parts = match.split(' ')
        n = (len(parts)//3)*3
        parts = np.array(parts)[:n].reshape(-1,3)
        parts = parts[:,:2].astype(np.float)
        vline = parts[0,0] == parts[1,0]
        hline = parts[0,1] == parts[1,1]
        if vline:
            ticks.append(parts)
        elif not hline:
            plots.append(parts)
    ticks = np.array(ticks).reshape(-1,2)
    return plots, ticks

def bbox(group):
    t = np.min(group[:,1])
    b = np.max(group[:,1])
    l = np.min(group[:,0])
    r = np.max(group[:,0])
    return t,b,l,r

def get_top(ticks, tblr):
    valid = points_inside(ticks, tblr)
    points = ticks[valid]
    if len(points) == 0:
        return None
    top = np.min(points[:,1])
    return top

def get_left(ticks, tblr):
    valid = points_inside(ticks, tblr)
    points = ticks[valid]
    if len(points) == 0:
        return None
    top = np.min(points[:,0])
    return top

def select_plot(plots, tblr):
    for plot in plots:
        inside = points_inside(plot, tblr)
        if np.mean(inside) > 0.5:
            return plot
    return None

def extract_from_tracking_areas(page, categories, tracking_areas, baseline_offset):
    days_per_plot = 43
    plot_scale = 80
    plot_width = 114.316
    
    plots, ticks = extract_plots_and_ticks(page)
    
    results = []    
    for category, tracking_area in zip(categories, tracking_areas):
        cur = [None] * days_per_plot
        plot = select_plot(plots, tracking_area)
        top = get_top(ticks, tracking_area)
        if plot is None or top is None:
            results.append((category, cur))
            continue
        baseline = top - baseline_offset
        ys = (plot[:,1] - baseline) * (-plot_scale / baseline_offset)
        if len(ys) == days_per_plot:
            cur = ys
        else:
            xs = plot[:,0]
            spacing = plot_width / (days_per_plot - 1)
            left = get_left(ticks, tracking_area)
            indices = np.round((plot[:,0] - left) / spacing)
            for i, y in zip(indices, ys):
                cur[int(i)] = y
        results.append((category, cur))
    return results

def process_pdf(fn):
    ps_fn = '.pdftocairo.ps'
    err = subprocess.call(['pdftocairo', '-ps', fn, ps_fn])
    if err:
        return
    with open(ps_fn) as f:
        ps = f.read()
    os.remove(ps_fn)

    pages = ps.split('%%Page:')[1:]
    
    categories = ['Retail & recreation', 'Grocery & pharmacy', 'Parks', 'Transit stations', 'Workplace', 'Residential']

    region = get_region(fn)
    
    # region plots are taller
    baseline_offset = 34.297

    xs = [100,500]
    ys = [340,450,570,690]
    tracking_areas = build_tracking_areas(xs, ys)
    results = extract_from_tracking_areas(pages[0], categories[:3], tracking_areas, baseline_offset)
    for result in results:
        yield ('region', region, *result)
    
    xs = [100,500]
    ys = [10,150,260,400]
    tracking_areas = build_tracking_areas(xs, ys)
    results = extract_from_tracking_areas(pages[1], categories[3:], tracking_areas, baseline_offset)
    for result in results:
        yield ('region', region, *result)

    # subregion plots are shorter
    baseline_offset *= 5/6

    all_subregions = []
    for subregion in list_subregions(fn):
        all_subregions.extend([subregion] * 6)
    all_subregions = iter(all_subregions)

    results = []
    for page in pages[2:-1]:
        xs = [40,220,390,555]
        ys = [100,230,400,550,700]
        tracking_areas = build_tracking_areas(xs, ys)
        results = extract_from_tracking_areas(page, cycle(categories), tracking_areas, baseline_offset)
        for result in results:
            try:
                subregion = next(all_subregions)
            except StopIteration:
                return
            yield ('subregion', subregion, *result)

def none_safe_str(f):
    return '' if f is None else str(round(f,2))

def print_header():
    parts = [(start_date + timedelta(i)).isoformat() for i in range(days_per_plot)]
    parts = ['Kind', 'Name', 'Category'] + parts
    print('\t'.join(parts))

def print_tsv(kind, region, category, data):
    print(f'{kind}\t{region}\t{category}\t' + '\t'.join(map(none_safe_str, data)))

if __name__ == '__main__':
    print_header()
    for result in process_pdf(args.input_fn):
        print_tsv(*result)