# COVID-19 Mobility .pdf to .tsv

### [Download the .tsv data](https://github.com/kylemcdonald/covid-mobility-data/releases/download/2020-03-29/2020-03-29-covid-mobility-data.zip).

This script attempts to digitize the [COVID-19 Mobility Reports](https://www.google.com/covid19/mobility/) produced by Google.

The start date is currently hardcoded to 2020-02-16, and the total number of days defaults to 43.

If the PDFs are re-downloaded and re-processed after they are updated, there's a good chance this script won't work, or (at least) the dates in the header will be incorrect.

To download the .pdf files, run the following command:

```
$ mkdir pdf && cd pdf && xargs -n 1 curl -O < ../urls.txt
```

To convert all the .pdf files to .tsv files, first make sure your python environment is ready:

* Python 3
* Python packages: numpy, scipy, pdf2image, pytesseract
* Note that the Tesseract binaries need to be installed separately: `sudo apt install tesseract-ocr`. On Debian you may also need to install `poppler-utils`.

Then run the following commands to create an output folder and pipe all the data to the folder.

```
$ mkdir tsv
$ for f in pdf/*; do echo $f; python covid-pdf-to-tsv.py $f > tsv/`basename $f`.tsv; done
```

## Operating principle

This script identifies the light-gray x-axis ticks in each plot using a vertical-line-edge kernel. Then the bounding box of these ticks are selected within a few known regions: 3 locations on the first page, 3 on the second page, and in up to 12 locations on the remaining pages, with the exception of the last page.

Then we select a subregion of the .pdf immediately above the tick marks. We assume the plots are all -80% to +80% range, and have a 2:1 aspect ratio and a specific size given the DPI. Finally, we select pixels that match the blue line color from the plot, and find the mean y-position along a set of 43 vertical bars.

## Accuracy

Please visually confirm that this works for you. Because digitization happens at a relatively low DPI and using a naive algorithm, it's likely that the accuracy is low for data points that are very different from their neighbors. When there are missing datapoints in the original plots, it's possible that nearby datapoints will also be missing. In practice there is probably a fixed +/-1% bias to a lot of the output, and +/-5% error for plots with a lot of variation.
