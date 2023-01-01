# Campsite Availability Scraping

This script scrapes the https://recreation.gov website for info regarding campgrounds and permits, as well as checking their availabilities.



## Campgrounds

**Get campground info**

Info on campground, including

- Overall campground info, including any recreation.gov alerts
- Ratings on quality of cell service for major providers
- Info on each of the individual campsites within the the campground, with link to recreation.gov page

Get information on Cottonwood Campground in Joshua Tree.

```
❯ ./scripts/camping.py campground info 272299
COTTONWOOD CAMPGROUND (CA)
                                    Alerts
 ─────────────────────────────────────────────────────────────────────────────
  ⚠️   <p>Odd-numbered campsites may not accommodate driver side slideouts</p>
 ─────────────────────────────────────────────────────────────────────────────
                             Campground fields

  Field             Value
 ─────────────────────────────────────────────────────────────────────────
  URL               https://www.recreation.gov/camping/campgrounds/272299
  email
  id                272299
  latitude          33.75
  longitude         -115.825
  map_url
  name              COTTONWOOD CAMPGROUND (CA)
  phone             760-367-5554
  campground_type   CampgroundType.standard
  parent_asset_id   2782
  Sprint            0.3
  AT&T              0.3
  Verizon           0.2
  T-Mobile          0.2

                                       Campsites

  Name   ID       Status                      Site type               Reservation type
 ──────────────────────────────────────────────────────────────────────────────────────
  B02    103758   Open                        STANDARD NONELECTRIC    Site-Specific
  B27    103759   Open                        STANDARD NONELECTRIC    Site-Specific
  B21    103760   Not Reservable Management   MANAGEMENT              Site-Specific
  A30    103761   Open                        STANDARD NONELECTRIC    Site-Specific
  B30    103762   Open                        STANDARD NONELECTRIC    Site-Specific
  A05    103763   Open                        STANDARD NONELECTRIC    Site-Specific
  B06    103764   Open                        STANDARD NONELECTRIC    Site-Specific
  ...
```

**Get campground availability**

Search campsite availability within the campground, including ability to:

- Filter by date window
- Filter by availability status (available, reserved, etc…)
- Filter by length of window 
- Filter by campsite IDs

Search for sites in Cottonwood Campground in January that are available for at least 7 consecutive.

```
❯ ./scripts/camping.py campground avail 272299 -s 2023-01-01 -e 2023-01-31 -l 7 --status available
                                    Alerts
 ─────────────────────────────────────────────────────────────────────────────
  ⚠️   <p>Odd-numbered campsites may not accommodate driver side slideouts</p>
 ─────────────────────────────────────────────────────────────────────────────
                             Available campsites

  Campsite name   Campsite ID   Start date   End date     Length   Status
 ────────────────────────────────────────────────────────────────────────────
  B02             103758        2023-01-22   2023-02-01   10       Available
  A30             103761        2023-01-02   2023-01-13   11       Available
  A30             103761        2023-01-22   2023-02-01   10       Available
  B30             103762        2023-01-02   2023-01-13   11       Available
  B30             103762        2023-01-22   2023-02-01   10       Available
  B06             103764        2023-01-22   2023-02-01   10       Available
  B01             103767        2023-01-22   2023-02-01   10       Available
  B09             103773        2023-01-22   2023-02-01   10       Available
  A21             103775        2023-01-22   2023-02-01   10       Available
  A23             103776        2023-01-22   2023-01-29   7        Available
  ...
```

Campground availability options

```
❯ ./scripts/camping.py campground avail --help

 Usage: camping.py campground avail [OPTIONS] CAMP_ID

 get detailed availability for a campground

Arguments 
*    camp_id      TEXT  [default: None] [required]

Options
--start-date  -s      TEXT     Start date [default: 2022-12-31]
--end-date    -e      TEXT     End date [default: None]
--site-ids    -i      TEXT     Site IDs [default: None]
--length      -l      INTEGER  Booking window length [default: None]
--status              TEXT     Campsite status [default: None]
```

## Permits

**Get permit info**

Info on permit, including

- Overall permit info, including any recreation.gov alerts
- Ratings on quality of cell service for major providers
- Info on each of the individual permit divisions (aka trailheads) within the area

Get info on Inyo National Forest permits.

```
❯ ./scripts/camping.py permit info inyo
Inyo National Forest - Wilderness Permits

                     Permit fields

  Field      Value
 ──────────────────────────────────────────────────────
  URL        https://www.recreation.gov/permits/233262
  id         233262
  name       Inyo National Forest - Wilderness Permits
  Verizon    0.7
  T-Mobile   0.3
  AT&T       0.7
  Sprint     0.5

                                      Divisions

  Name                                       ID     Code      District
 ────────────────────────────────────────────────────────────────────────────────────
  Baker and Green Lakes                      460    JM22      John Muir
  Baxter Pass                                464    JM29      John Muir
  Beck Lake                                  437    AA12      Ansel Adams
  Big Pine Creek North Fork                  495    JM23      John Muir
  Big Pine Creek North Fork (Outfitter)      4952   JM23-O
  Big Pine Creek North Fork (Pack Outfit)    4951   JM23-PO
  Big Pine Creek South Fork                  461    JM24      John Muir
  Birch Lake                                 462    JM25      John Muir
  Bishop Pass -South Lake                    459    JM21      John Muir
  Blackrock (Non Quota)                      473    GT66      Golden Trout
  Bloody Canyon                              517    AA03      Ansel Adams
  ...
```

**Get permit availability**

Search permit availability by division/trailhead, with ability to:

- Filter by date window
- Filter by number of spots remaining
- Filter by division ID and code

Search for permits in Inyo NF in June 2023 that have at least 5 remaining.

```
❯ ./scripts/camping.py permit avail inyo -r 5 -s 2023-06-01

                                     Available permits

  Division name                    Division ID   Date         Remain   Total    Is walkup
 ─────────────────────────────────────────────────────────────────────────────────────────
  Glacier Canyon                   424           2023-06-01   5        5        False
  Parker Lake                      425           2023-06-01   6        6        False
  Rush Creek                       430           2023-06-01   10       18       False
  Yost / Fern Lakes                434           2023-06-01   5        5        False
  Golden Trout Lakes               442           2023-06-01   6        6        False
  Duck Pass                        444           2023-06-01   18       18       False
  Valentine Lake                   445           2023-06-01   5        5        False
  Laurel Lakes                     446           2023-06-01   5        5        False
  Convict Creek                    447           2023-06-01   6        6        False
  McGee Pass                       448           2023-06-01   9        9        False
  ...
```

Campground availability options

```
❯ ./scripts/camping.py permit avail --help

 Usage: camping.py permit avail [OPTIONS] PERMIT_ID

 get detailed availability for a permit

Arguments*    permit_id      TEXT  [default: None] [required]

Options
--start-date  -s                    TEXT     Start date [default: 2022-12-31]
--end-date    -e                    TEXT     End date [default: None]
--div-ids     -i                    TEXT     Division IDs [default: None]
--div-codes   -c                    TEXT     Division codes [default: None]
--remain      -r                    INTEGER  Remaining spots [default: None]
--is-walkup       --no-is-walkup             Is walkup permit [default: no-is-walkup]
```

**Extra**

There are aliases for the common California permits, so you don’t have to look up the ID:

```
PERMIT_IDS = {
    "desolation": "233261",
    "humboldt": "445856",
    "yosemite": "445859",
    "inyo": "233262",
    "sierra": "445858",
    "seki": "445857",
    "whitney": "233260",
}
```

## Getting campground and permit IDs

What you'll want to do is go to [recreation.gov](https://recreation.gov) and search for the campground (or permit) you want. Click on it in the search sidebar. This should 
take you to a page for that campground, the URL will look like `https://www.recreation.gov/camping/campgrounds/<number>`. That number is the campground ID.  Similarly, the URL will look like `https://www.recreation.gov/permits/<number>` for permits.

## Status

The API and core models are complete, reasonably well-polished, and have tests.  The `campinp.py` script is a hodge-podge of things that could be much better.

## Todo

- Filter campground availability by site type
- `¯\_(ツ)_/¯`
