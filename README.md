# Strava Dashboard 

Project to build a dashboard visualizing my personal Strava Data. The data is queried
from the Strava website using their API and then stored on a local postGRE SQL
database. This data is thereafter used in the dashboard build using the Python
Dash package.

## files
* Strava_functions.py : general functions to query data from the Strava API and 
keep the postGRE SQL database up to date
* main.py: file containing the code for rendering the Dash app
* Yaml: Anaconda environment used to script this

    