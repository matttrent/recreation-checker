# Campsite Availability Scraping

This script scrapes the https://recreation.gov website for campsite availabilities.

It has 3 modes:

- `check` to see if campsites are available for the entire range of `start_date` to `end_date`.
- `search` for campsites with available blocks of at least `stay_length` anytime between `start_date` and `end_date`.
- `nextopen` to see the first date campsites are available.  Useful for very hard-to-get ones like fire lookouts.

where the results are broken donw by the type of campsite available (tent only, RV, etc...).

## Example Usage

Here is the output of `check` for campsites on 3 specific nights:

```shell
$ python camping.py search --start-date 2020-07-01 --end-date 2020-07-31 232448 232450 232447 232770
❌ TUOLUMNE MEADOWS https://www.recreation.gov/camping/campgrounds/232448
    GROUP TENT ONLY AREA NONELECTRIC: 0 / 7 available
    MANAGEMENT: 0 / 4 available
    TENT ONLY NONELECTRIC: 0 / 2 available
    STANDARD NONELECTRIC: 0 / 8 available
❌ LOWER PINES https://www.recreation.gov/camping/campgrounds/232450
    STANDARD NONELECTRIC: 0 / 66 available
    MANAGEMENT: 0 / 2 available
    RV NONELECTRIC: 0 / 7 available
❌ UPPER PINES https://www.recreation.gov/camping/campgrounds/232447
    STANDARD NONELECTRIC: 0 / 205 available
    RV NONELECTRIC: 0 / 28 available
    TENT ONLY NONELECTRIC: 0 / 4 available
    MANAGEMENT: 0 / 3 available
🏕 BASIN MONTANA CAMPGROUND https://www.recreation.gov/camping/campgrounds/232770
    STANDARD NONELECTRIC: 20 / 29 available
    MANAGEMENT: 0 / 1 available
```

Here is the output of `search` for any 2-night periods:

```shell
± python camping.py search --start-date 2020-07-01 --end-date 2020-07-31 -l 3 232448 232450 232447 232770
❌ TUOLUMNE MEADOWS https://www.recreation.gov/camping/campgrounds/232448
❌ LOWER PINES https://www.recreation.gov/camping/campgrounds/232450
❌ UPPER PINES https://www.recreation.gov/camping/campgrounds/232447
🏕 BASIN MONTANA CAMPGROUND https://www.recreation.gov/camping/campgrounds/232770
    STANDARD NONELECTRIC:
        Starting 2020-07-05 (Sun) for 5 days
        Starting 2020-07-12 (Sun) for 5 days
        Starting 2020-07-19 (Sun) for 5 days
        Starting 2020-07-26 (Sun) for 5 days
```

You can also read from stdin. Define a file (e.g. `parks.txt`) with IDs like this:

```text
232447
232449
232450
232448
```

and then use it with this slightly funky syntax to be compatible with `click`:

```shell
$ cat parks.txt | tr "\n" " " | xargs python camping.py check --start-date 2018-07-20 --end-date 2018-07-23
❌ TUOLUMNE MEADOWS https://www.recreation.gov/camping/campgrounds/232448
    GROUP TENT ONLY AREA NONELECTRIC: 0 / 7 available
    ...
```

## Getting park IDs

What you'll want to do is go to [recreation.gov](https://recreation.gov) and search for the campground you want. Click on it in the search sidebar. This should take you to a page for that campground, the URL will look like `https://www.recreation.gov/camping/campgrounds/<number>`. That number is the park ID.

## Installation

```shell
conda create -n campsite-checker python=3.8 pip
python3 -m venv myvenv
source activate campsite-checker
pip install -r requirements.txt
# You're good to go!
```

## Development

This code is formatted using black and isort:

```shell
black -l 80 -t py38 camping.py
isort camping.py
```

## Limitations / Todo

[recreation.gov](https://recreation.gov) changed their API to only return results for a single month at a time.  Searches still work correctly within a month, but I have yet to update the code to handle search queries that span months.
