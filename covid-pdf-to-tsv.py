import numpy as np
from scipy.ndimage import convolve
from pdf2image import convert_from_bytes
from pytesseract import image_to_string

from itertools import cycle
from datetime import date, timedelta

import argparse
parser = argparse.ArgumentParser()
parser.add_argument('input_fn', type=str)
parser.add_argument('--days_per_plot', type=int, default=43)
args = parser.parse_args()

start_date = date(2020, 2, 16)
days_per_plot = args.days_per_plot

def get_country_name(arr):
    sub = arr[200:280,80:1300].astype(np.float)
    sub = sub.mean(axis=-1)
    sub = np.minimum(sub, 110)
    sub -= sub.min()
    sub /= sub.max()
    return image_to_string(sub)

def get_subregion_names(arr):
    regions = [
        (90,170,80,1000),
        (1000,1080,80,1000)
    ]
    names = [image_to_string(arr[t:b,l:r]) for t,b,l,r in regions]
    return names

def extract_mask(img, color):
    return np.all(img == color, axis=-1)

def extract_plot_mask(img):
    return extract_mask(img, [66,133,244])

def extract_line_mask(img):
    return extract_mask(img, [218,220,224])

def extract_tick_mask(img):
    mask = extract_line_mask(img) * 1
    kernel = np.array([[0,1],[0,1]]) # vertical line detector
    ticks_left = convolve(mask, kernel)
    ticks_left = ticks_left == ticks_left.max()
    ticks_right = convolve(mask, 1-kernel)
    ticks_right = ticks_right == ticks_right.max()
    ticks = ticks_left | ticks_right
    return ticks

def nonzero_bbox(img, tblr):
    t,b,l,r = tblr
    sub = img[t:b,l:r]
    xsum = sub.sum(0)
    xpeaks = xsum > (xsum.max() / 2)
    left = np.argmax(xpeaks)
    right = len(xpeaks) - np.argmax(xpeaks[::-1]) - 1
    ysum = sub.sum(1)
    ypeaks = ysum > (ysum.max() / 2)
    top = np.argmax(ypeaks)
    bottom = len(ypeaks) - np.argmax(ypeaks[::-1]) - 1
    return top+t, bottom+t, left+l, right+l

def extract_data(plot_mask, tick_mask, region):  
    plot_height = 160 # fixed height
    plot_range = 80 # from y axis labels
    padding = 40
    
    zero_offset = int(plot_height / 2)
    t,b,l,r = region
    plot_top = t - plot_height
    plot = plot_mask[plot_top-padding:t+padding,l:r].copy()
    datapoints = []
    for x in np.linspace(2, plot.shape[1]-2, days_per_plot):
        x = int(x)
        segment = plot[:, x]
        valid = np.argwhere(segment == 1)
        if len(valid):
            y = np.mean(valid)
        else:
            y = np.nan
        datapoints.append(y)
    datapoints = np.array(datapoints)
    datapoints = ((zero_offset + padding) - datapoints) * (plot_range / (plot_height / 2))
    return datapoints

def build_tracking_areas(xs, ys):
    tracking_areas = []
    for top,bottom in zip(ys,ys[1:]):
        for left,right in zip(xs,xs[1:]):
            tracking_areas.append((top,bottom,left,right))
    return tracking_areas

def extract_from_tracking_areas(arr, categories, tracking_areas):
    plot_mask = extract_plot_mask(arr)
    tick_mask = extract_tick_mask(arr)
    results = []
    for category, tracking_area in zip(categories, tracking_areas):
        region = nonzero_bbox(tick_mask, tracking_area)
        datapoints = extract_data(plot_mask, tick_mask, region)
        results.append((category, datapoints))
    return results

def nan_safe_str(f):
    return str(f) if f == f else ''

def print_header():
    parts = [(start_date + timedelta(i)).isoformat() for i in range(days_per_plot)]
    parts = ['Region', 'Category'] + parts
    print('\t'.join(parts))

def print_tsv(region, category, data):
    print(f'{region}\t{category}\t' + '\t'.join(map(nan_safe_str, data)))

def process_pdf(fn):
    with open(fn, 'rb') as f:
        images = convert_from_bytes(f.read())

    categories = ['Retail & recreation', 'Grocery & pharmacy', 'Parks', 'Transit stations', 'Workplace', 'Residential']

    xs = [300,1300]
    ys = [1024,1350,1680,2000]
    arr = np.array(images[0])
    region = get_country_name(arr)
    tracking_areas = build_tracking_areas(xs, ys)
    results = extract_from_tracking_areas(arr, categories[:3], tracking_areas)
    for category, datapoints in results:
        yield (region, category, datapoints)

    xs = [300,1300]
    ys = [250,480,820,1100]
    arr = np.array(images[1])
    tracking_areas = build_tracking_areas(xs, ys)
    results = extract_from_tracking_areas(arr, categories[3:], tracking_areas)
    for category, datapoints in results:
        yield (region, category, datapoints)
                
    for ppm in images[2:-1]:    
        arr = np.array(ppm)
        subregions = get_subregion_names(arr)
        
        xs = [125,600,1080,1580]
        ys = [440,730,1180]
        tracking_areas = build_tracking_areas(xs, ys)
        results = extract_from_tracking_areas(arr, cycle(categories), tracking_areas)
        for category, datapoints in results:
            yield (subregions[0], category, datapoints)
        
        if len(subregions[1]) == 0:
            continue
        
        xs = [125,600,1080,1580]
        ys = [1180,1640,2000]
        tracking_areas = build_tracking_areas(xs, ys)
        results = extract_from_tracking_areas(arr, cycle(categories), tracking_areas)
        for category, datapoints in results:
            yield (subregions[1], category, datapoints)

if __name__ == '__main__':
    print_header()
    for result in process_pdf(args.input_fn):
        print_tsv(*result)