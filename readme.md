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
* Python packages: numpy
* pdftocairo and pdftotext: `sudo apt install poppler-utils`

Then run the following commands to create an output folder and pipe all the data to the folder.

```
$ mkdir tsv
$ for f in pdf/*; do echo $f; python covid-pdf-to-tsv.py $f > tsv/`basename $f`.tsv; done
```

## Operating principle

This script uses pdftocairo to convert to Postscript, and a regular expression to identify polylines. Polylines and ticks in different regions are categorized appropriately.

We use pdftotext to extract all the place names. The place names in the Postscript output are too obfuscated by layout and style commands for the extraction to work correctly.

## Accuracy

Please visually confirm that this works for you. From examining a few hundred datapoints manually, there is less than a 0.5% error compared to the printed numbers. But there may be some edge cases where the extraction failed.