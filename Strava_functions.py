import json
import psycopg2
from psycopg2.extras import execute_values
import requests
import time
from datetime import datetime
import pandas as pd


class ConnectToDB:
    """ This Class creates a connection object to the postGRE Strava database and allows
        to perform queries on this database"""

    # Initialize an object of the class
    def __init__(self):
        self.status = "Not Connected"
        self.conn = None
        self.cur = None
        self.query_result = None

    def initialize_connection(self):

        """ Method to connect the object to the postGRE Strava Database"""

        with open('strava_DB_config.json', 'r') as configfile:
            db_config_params = json.load(configfile)

        try:
            # Read in the configuration parameters to connect to the strava database
            strava_config_params = db_config_params

            # Connect to the PostGRE SQL - Strava database
            self.conn = psycopg2.connect(**strava_config_params)

            # Create a cursor to execute SQL commands
            self.cur = self.conn.cursor()

            # Set the status to Connected
            self.status = "Connected"

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def query_data(self, query, parameter):

        """ Method to let the object query to the postGRE Strava database """

        try:
            # Execute the query
            self.cur.execute(query, parameter)

            # Get the Result
            self.query_result = self.cur.fetchall()

            # Close the cursor
            self.cur.close()

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def insert_data(self, query, parameters):

        """Method to let the object insert data in the postGRE Strava database"""

        try:
            # Execute the query
            execute_values(self.cur, query, parameters)

            # Commit the changes to the database
            self.conn.commit()

            # Close the cursor
            self.cur.close()

            # Check if something went wrong - print the error
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def update_data(self, query, parameter):

        """Method to let the object update data in the postGRE Strava database"""

        try:
            # Execute the query
            self.cur.execute(query, parameter)

            # Commit the changes to the database
            self.conn.commit()

            # Close the cursor
            self.cur.close()

        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def delete_data(self, query, parameter):

        """Method to delete data from the postGRE Strava database"""

        try:
            # Execute the query
            self.cur.executemany(query, parameter)

            # Commit the changes to the database
            self.conn.commit()

            # Close the cursor
            self.cur.close()

            # Check if something went wrong - print the error
        except (Exception, psycopg2.DatabaseError) as error:
            print(error)

    def close_connection(self):

        """Method to close the object's connection to the database """

        self.conn.close()
        self.status = "Not Connected"


def read_api_secrets():

    """ Function to read the config parameters of the API"""

    with open('strava_API_config.json', 'r') as configfile:
        api_config_params = json.load(configfile)

    return api_config_params


def get_current_auth_info(user_id):

    """ Function to retrieve the current authentication information from the postGRE Strava database"""

    auth_info = {}

    # Build the query to get the auth information
    query = """SELECT auth_key, recovery_key, expiration_date FROM auth_info WHERE user_id = %s """

    # Make an object from the ConnectToDB class
    conn_obj = ConnectToDB()

    # Initialize the connection to the database
    conn_obj.initialize_connection()

    # Perform the query
    conn_obj.query_data(query, (user_id,))

    # Get the result
    auth_info['auth_key'], auth_info['recovery_key'], auth_info['expiration_date'] = conn_obj.query_result[0]

    # Close the connection
    conn_obj.close_connection()

    return auth_info


def update_auth_key(user_id, response):

    """ Function to update the authentication key and recovery key in the postGRE Strava database"""

    # Build the query to update the authentication information
    query = """ UPDATE auth_info 
                SET auth_key = %s,
                    recovery_key = %s,
                    expiration_date = %s
                WHERE user_id = %s """
    # Make tuple of parameters to perform the update
    params = (response['access_token'], response['refresh_token'], response['expires_at'], user_id)

    # Make an object from the ConnectToDB class
    conn_obj = ConnectToDB()

    # Initialize the connection to the database
    conn_obj.initialize_connection()

    # Perform the update in the database
    conn_obj.update_data(query, params)

    # Close the connection
    conn_obj.close_connection()


def get_new_recovery_key(user_id):

    """Function to get a new recovery token when the authentication token has expired """

    token_url = "https://www.strava.com/api/v3/oauth/token"
    auth_params = read_api_secrets()
    auth_params['refresh_token'] = get_current_auth_info(user_id)['recovery_key']
    auth_params['grant_type'] = 'refresh_token'

    try:
        # Perform a post request to request new a new authentication token and recovery token
        response = requests.post(url=token_url, params=auth_params)
        print(response.url)

        # Check if an HTTP error has occurred - invalid request
        response.raise_for_status()

        # Update the new received authentication key and recovery token in the postGRE Strava database
        update_auth_key(user_id=user_id, response=response.json())

    except requests.exceptions.HTTPError as err:
        print(err)


def insert_activities(activities):

    """Function to upload a pandas dataframe containing activities into the postGRE Strava database"""

    # Prepare query for loading the data table in the postGRE Strava database
    columns = ','.join(list(activities.columns))
    tuples = [tuple(x) for x in activities.to_numpy()]

    query = "INSERT INTO activities({}) VALUES %s".format(columns)

    # Make an object from the ConnectToDB class
    conn_obj = ConnectToDB()

    # Initialize the connection to the database
    conn_obj.initialize_connection()

    # Perform the insert in the database
    conn_obj.insert_data(query, tuples)

    # Close the connection
    conn_obj.close_connection()


def initialize_activities(user_id):

    """ Function to get all activities for a new user and upload them in the postGRE Strava database"""
    activities = []
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    page = 1
    user_auth_info = get_current_auth_info(user_id)

    # Check if the current authentication key is still valid - get an updated one if necessary
    if user_auth_info['expiration_date'] < time.time():
        get_new_recovery_key(user_id)
        user_auth_info = get_current_auth_info(user_id)

    # Write a loop to get all the activities of an athlete - retrieve 50 activities per page
    while True:
        # Create the parameters to build the API request query
        auth_params = {"access_token": user_auth_info['auth_key'],
                       "page": page,
                       "per_page": 50}

        try:
            # Build the query to get the activities
            response = requests.get(url=activities_url, params=auth_params)
            # Check to be sure no wrong request was send
            response.raise_for_status()

            # Check if the response still has data - if so continue loop
            if len(response.json()) > 0:
                # Append the results to the activities list
                activities.append(response.json())

                # Increase the page for a new query and continue the loop
                page += 1
                continue

            # Break the loop if no results are found anymore
            else:
                print("The number of pages is {}".format(page))
                break

        except requests.exceptions.HTTPError as err:
            print(err)
            break

    # Create a dataframe from the activities out of Strava - create / transform necessary columns
    data = pd.DataFrame([dct for lst in activities for dct in lst])
    data['user_id'] = user_id
    data['start_epoch'] = [datetime.strptime(d['start_date_local'], "%Y-%m-%dT%H:%M:%SZ").timestamp()
                           for lst in activities for d in lst]
    data['year_month'] = pd.to_datetime(data.start_epoch.astype(int), unit='s').dt.to_period("M").dt.to_timestamp()
    data['distance_in_km'] = data['distance'].div(1000)

    # Keep only relevant columns
    data = data[['id', 'user_id', 'name', 'distance', 'moving_time', 'total_elevation_gain', 'type', 'start_date_local',
                 'location_city', 'location_state', 'location_country', 'achievement_count', 'kudos_count',
                 'comment_count',
                 'athlete_count', 'trainer', 'commute', 'manual', 'private', 'gear_id', 'average_speed', 'max_speed',
                 'has_heartrate', 'average_heartrate', 'max_heartrate', 'elev_high', 'elev_low', 'pr_count',
                 'total_photo_count', 'average_watts', 'kilojoules', 'start_epoch', 'year_month', 'distance_in_km']]

    # Update the activities in the postGRE strava database
    insert_activities(data)


def update_strava_activity(user_id):

    """ Function to perform an update of the most recent activities of user in the postGRE Strava database
        In order to do this easy - a request of the last 50 activities is made from the strava API.
        To keep it simple - corresponding activities in the postGRE Strava database are removed and
        re-uploaded."""

    select_query = """SELECT DISTINCT id FROM activities WHERE user_id = %s
                       ORDER BY id DESC LIMIT 50"""

    delete_query = """DELETE FROM activities where id IN (%s)"""
    activities = []
    activities_url = "https://www.strava.com/api/v3/athlete/activities"
    user_auth_info = get_current_auth_info(user_id)

    # Make an object from the ConnectToDB class
    conn_obj = ConnectToDB()

    # Initialize the connection to the database
    conn_obj.initialize_connection()

    # Perform the query
    conn_obj.query_data(select_query, (user_id,))

    # Close the connection
    conn_obj.close_connection()

    # Make a list of activities we already know
    known_activity_ids = [t[0] for t in conn_obj.query_result]

    # Check if the current authentication key is still valid - get an updated one if necessary
    if user_auth_info['expiration_date'] < time.time():
        get_new_recovery_key(user_id)
        user_auth_info = get_current_auth_info(user_id)

    # Create the parameters to build the API request query - just request the last 50 activities
    auth_params = {"access_token": user_auth_info['auth_key'],
                   "page": 1,
                   "per_page": 50}
    try:
        # Build the query to get the activities
        response = requests.get(url=activities_url, params=auth_params)
        # Check to be sure no wrong request was send
        response.raise_for_status()

        # Get the result from the query
        activities.append(response.json())

    except requests.exceptions.HTTPError as err:
        print(err)

    # Create a dataframe from the activities out of Strava - create / transform necessary columns
    data = pd.DataFrame([dct for lst in activities for dct in lst])
    data['user_id'] = user_id
    data['start_epoch'] = [datetime.strptime(d['start_date_local'], "%Y-%m-%dT%H:%M:%SZ").timestamp()
                           for lst in activities for d in lst]
    data['year_month'] = pd.to_datetime(data.start_epoch.astype(int), unit='s').dt.to_period("M").dt.to_timestamp()
    data['distance_in_km'] = data['distance'].div(1000)

    # Keep only relevant columns
    data = data[['id', 'user_id', 'name', 'distance', 'moving_time', 'total_elevation_gain', 'type', 'start_date_local',
                 'location_city', 'location_state', 'location_country', 'achievement_count', 'kudos_count',
                 'comment_count',
                 'athlete_count', 'trainer', 'commute', 'manual', 'private', 'gear_id', 'average_speed', 'max_speed',
                 'has_heartrate', 'average_heartrate', 'max_heartrate', 'elev_high', 'elev_low', 'pr_count',
                 'total_photo_count', 'average_watts', 'kilojoules', 'start_epoch', 'year_month', 'distance_in_km']]

    # Get the intersection of the last 50 activities on Strava vs last 50 activities in the postGRE Strava database
    intersect = [(x, ) for x in list(data.loc[data.id.isin(known_activity_ids), "id"])]

    # Delete the activities which are in the intersect tuple out of the activities table for the user in the postGRE
    # Strava database
    if len(intersect) > 0:
        # Initialize the connection to the database
        conn_obj.initialize_connection()

        # Perform the deletion of the rows
        conn_obj.delete_data(delete_query, intersect)

        # Close the connection
        conn_obj.close_connection()

    # If data contains actual data - do the upload
    if len(data) > 0:
        insert_activities(data)


def get_strava_activities(user_id):

    """ Function to get the strava activities of a user in a pandas dataframe used for making the graphs
        in the Dash app"""

    select_query = "SELECT * FROM activities WHERE user_id = %s"

    # Make an object from the ConnectToDB class
    conn_obj = ConnectToDB()

    # Initialize the connection to the database
    conn_obj.initialize_connection()

    # Perform the query
    conn_obj.query_data(select_query, (user_id,))

    # Close the connection
    conn_obj.close_connection()

    # Get the column names and the actual data in a pandas data frame
    columnames = [t[0] for t in conn_obj.cur.description]
    query_result = conn_obj.query_result

    data = pd.DataFrame.from_records(columns=columnames, data=query_result)

    # Group the data by type and year_month so we have aggregated data on this level

    data_grouped = data.groupby(['year_month', 'type'], as_index=False).agg({'distance': 'sum', 'distance_in_km': 'sum'})

    # In order to generate the Bar Chart we need data for each time point for each sport type a data point
    # Get the start and the end point

    dt_min = data_grouped.year_month.min()
    dt_max = data_grouped.year_month.max()

    # Generate all the time points on month basis between the start and end point and provide a key
    months = pd.DataFrame(pd.to_datetime(pd.date_range(dt_min, dt_max, freq="MS")))
    months['key'] = 0
    months.set_index('key')
    months.key.astype('datetime64[ns]')

    # Generate all possible sport types
    types = pd.DataFrame(data_grouped.type.unique())
    types['key'] = 0
    types.set_index('key')
    types.key.astype('datetime64[ns]')

    # Get the year_month variable in the correct date type
    data_grouped['year_month'] = data_grouped.year_month.astype('datetime64[ns]')

    # Create the Cartesian product so that we have a data point for all the combinations of sport types and monthly
    # time points - and impute the missing points with a 0.
    cart = months.merge(types, on='key').rename(columns={"0_x": "year_month", "0_y": "type"}) \
        .merge(data_grouped, how="left", on=['year_month', 'type'])
    cart = cart.fillna({"distance": 0, "distance_in_km": 0})

    return cart



