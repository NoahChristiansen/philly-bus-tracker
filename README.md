## Philadelphia Bus Tracking App

This repo is a work-in-progress attempt to make a realtime bus tracking application for Philadelphia, PA.

GTFS-realtime data comes from [SEPTA](https://www3.septa.org/#/).
GTFS-static data also comes from [SEPTA via Github](https://github.com/septadev/GTFS).

Python functions for downloading, processing, and storing data are located in `bus_map.py`.

The `create_gtfs_db.sql` file is used to create a Postgresql database for storing the static GTFS data.

The `application.py` file creates a Dash app with a bus map that can be filtered to select routes (all routes are shown by default), and displays bus locations updated in 30 second intervals.