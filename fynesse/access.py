from .config import *

from .assess import *

import csv
import osmnx as ox
import pymysql
import requests
import urllib.request
import zipfile

# This file accesses the data

def create_connection(user, password, host, database, port=3306):
    """ Create a database connection to the MariaDB database
        specified by the host url and database name.
    :param user: username
    :param password: password
    :param host: host url
    :param database: database
    :param port: port number
    :return: Connection object or None
    """
    conn = None
    try:
        conn = pymysql.connect(user=user,
                               passwd=password,
                               host=host,
                               port=port,
                               local_infile=1,
                               db=database
                               )
    except Exception as e:
        print(f"Error connecting to the MariaDB Server: {e}")
    return conn

def download_price_data(start, end):
    """
    Downloads property price data from <start> to <end> year, inclusive.
    Downloads both part 1 and 2 and saves to disk.
    :param start: Start year
    :param end: End year
    """

    for i in range(start, end + 1):
        url = f"http://prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com/pp-{i}-part1.csv"
        response = requests.get(url)

        with open(f'pp-{i}-1.csv', 'w') as f:
            writer = csv.writer(f)
            for line in response.iter_lines():
                writer.writerow(line.decode('utf-8').split(','))
        
        print("Downloaded:", i, "part 1")
        
        url = f"http://prod.publicdata.landregistry.gov.uk.s3-website-eu-west-1.amazonaws.com/pp-{i}-part2.csv"
        response = requests.get(url)

        with open(f'pp-{i}-2.csv', 'w') as f:
            writer = csv.writer(f)
            for line in response.iter_lines():
                writer.writerow(line.decode('utf-8').split(','))
        
        print("Downloaded:", i, "part 1")

def create_db_price_schema(conn):
    """
    Sets up the database schema for the `pp_data` table.
    """

    cur = conn.cursor()
    cur.execute("""
    DROP TABLE IF EXISTS `pp_data`;
    CREATE TABLE IF NOT EXISTS `pp_data` (
        `transaction_unique_identifier` tinytext COLLATE utf8_bin NOT NULL,
        `price` int(10) unsigned NOT NULL,
        `date_of_transfer` date NOT NULL,
        `postcode` varchar(8) COLLATE utf8_bin NOT NULL,
        `property_type` varchar(1) COLLATE utf8_bin NOT NULL,
        `new_build_flag` varchar(1) COLLATE utf8_bin NOT NULL,
        `tenure_type` varchar(1) COLLATE utf8_bin NOT NULL,
        `primary_addressable_object_name` tinytext COLLATE utf8_bin NOT NULL,
        `secondary_addressable_object_name` tinytext COLLATE utf8_bin NOT NULL,
        `street` tinytext COLLATE utf8_bin NOT NULL,
        `locality` tinytext COLLATE utf8_bin NOT NULL,
        `town_city` tinytext COLLATE utf8_bin NOT NULL,
        `district` tinytext COLLATE utf8_bin NOT NULL,
        `county` tinytext COLLATE utf8_bin NOT NULL,
        `ppd_category_type` varchar(2) COLLATE utf8_bin NOT NULL,
        `record_status` varchar(2) COLLATE utf8_bin NOT NULL,
        `db_id` bigint(20) unsigned NOT NULL
    ) DEFAULT CHARSET=utf8 COLLATE=utf8_bin AUTO_INCREMENT=1 ;
                """)

    return

def set_index_pp_data(conn):
    """
    Creates additional indices for the `pp_data` table.
    """

    cur = conn.cursor()
    cur.execute("""
    ALTER TABLE `pp_data`
    ADD PRIMARY KEY (`db_id`);
    ALTER TABLE `pp_data`
    MODIFY `db_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=1;
    CREATE INDEX `pp.postcode` USING HASH
        ON `pp_data`
            (postcode);
    CREATE INDEX `pp.date` USING HASH
        ON `pp_data`
            (date_of_transfer);
                """)
    
    return

def upload_price_data(conn, start, end):
    """
    Uploads both parts of price data from years <start> to <end> inclusive.
    """

    cur = conn.cursor()
    for i in range(start, end + 1):
        cur.execute(f"""
        LOAD DATA LOCAL INFILE 'pp-{i}-1.csv' INTO TABLE pp_data
        FIELDS TERMINATED BY ','
        OPTIONALLY ENCLOSED BY '""'
        LINES STARTING BY '' TERMINATED BY '\n';
        """)

        cur.execute(f"""
        LOAD DATA LOCAL INFILE 'pp-{i}-2.csv' INTO TABLE pp_data
        FIELDS TERMINATED BY ','
        OPTIONALLY ENCLOSED BY '""'
        LINES STARTING BY '' TERMINATED BY '\n';
        """)
    
    return

def download_postcode_data():
    """
    Downloads the ONS postcode information to disk and unzips it.
    """

    urllib.request.urlretrieve("https://www.getthedata.com/downloads/open_postcode_geo.csv.zip", "postcode_data.zip")

    with zipfile.ZipFile("postcode_data.zip", 'r') as zip_ref:
        zip_ref.extractall()
    
    return

def create_db_postcode_schema(conn):
    """
    Sets up the database schema for the `postcode_data` table.
    """

    cur = conn.cursor()
    cur.execute("""
    USE `property_prices`;
    DROP TABLE IF EXISTS `postcode_data`;
    CREATE TABLE IF NOT EXISTS `postcode_data` (
        `postcode` varchar(8) COLLATE utf8_bin NOT NULL,
        `status` enum('live','terminated') NOT NULL,
        `usertype` enum('small', 'large') NOT NULL,
        `easting` int unsigned,
        `northing` int unsigned,
        `positional_quality_indicator` int NOT NULL,
        `country` enum('England', 'Wales', 'Scotland', 'Northern Ireland', 'Channel Islands', 'Isle of Man') NOT NULL,
        `latitude` decimal(11,8) NOT NULL,
        `longitude` decimal(10,8) NOT NULL,
        `postcode_no_space` tinytext COLLATE utf8_bin NOT NULL,
        `postcode_fixed_width_seven` varchar(7) COLLATE utf8_bin NOT NULL,
        `postcode_fixed_width_eight` varchar(8) COLLATE utf8_bin NOT NULL,
        `postcode_area` varchar(2) COLLATE utf8_bin NOT NULL,
        `postcode_district` varchar(4) COLLATE utf8_bin NOT NULL,
        `postcode_sector` varchar(6) COLLATE utf8_bin NOT NULL,
        `outcode` varchar(4) COLLATE utf8_bin NOT NULL,
        `incode` varchar(3)  COLLATE utf8_bin NOT NULL,
        `db_id` bigint(20) unsigned NOT NULL
    ) DEFAULT CHARSET=utf8 COLLATE=utf8_bin;
    """)

    return

def set_index_postcode_data(conn):
    """
    Creates additional index for the `postcode_data` table.
    """

    cur = conn.cursor()
    cur.execute("""
    ALTER TABLE `postcode_data`
    ADD PRIMARY KEY (`db_id`);
    ALTER TABLE `postcode_data`
    MODIFY `db_id` bigint(20) unsigned NOT NULL AUTO_INCREMENT,AUTO_INCREMENT=1;
    CREATE INDEX `po.postcode` USING HASH
        ON `postcode_data`
            (postcode);
    """)
    
    return

def upload_postcode_data(conn):
    """
    Uploads postcode data.
    """

    cur = conn.cursor()
    cur.execute(f"""
    LOAD DATA LOCAL INFILE 'open_postcode_geo.csv' INTO TABLE postcode_data
    FIELDS TERMINATED BY ','
    LINES STARTING BY '' TERMINATED BY '\n';
    """)
    
    return

def create_db_joined_schema(conn):
    """
    Sets up the database schema for the `prices_coordinates_data` table.
    """

    cur = conn.cursor()
    cur.execute("""
    DROP TABLE IF EXISTS `prices_coordinates_data`;
    CREATE TABLE IF NOT EXISTS `prices_coordinates_data` (
        `price` int(10) unsigned NOT NULL,
        `date_of_transfer` date NOT NULL,
        `postcode` varchar(8) COLLATE utf8_bin NOT NULL,
        `property_type` varchar(1) COLLATE utf8_bin NOT NULL,
        `new_build_flag` varchar(1) COLLATE utf8_bin NOT NULL,
        `tenure_type` varchar(1) COLLATE utf8_bin NOT NULL,
        `locality` tinytext COLLATE utf8_bin NOT NULL,
        `town_city` tinytext COLLATE utf8_bin NOT NULL,
        `district` tinytext COLLATE utf8_bin NOT NULL,
        `county` tinytext COLLATE utf8_bin NOT NULL,
        `country` enum('England', 'Wales', 'Scotland', 'Northern Ireland', 'Channel Islands', 'Isle of Man') NOT NULL,
        `latitude` decimal(11,8) NOT NULL,
        `longitude` decimal(10,8) NOT NULL,
        `db_id` bigint(20) unsigned NOT NULL
    ) DEFAULT CHARSET=utf8 COLLATE=utf8_bin AUTO_INCREMENT=1 ;
    """)

    return

def get_bounds(latitude, longitude, box_width, box_height):
    """
    Get the bounding coordinates for a given latitude and longitude.
    """
    north = latitude + box_height/2
    south = latitude - box_height/2
    west = longitude - box_width/2
    east = longitude + box_width/2

    return (north, south, east, west)

def get_pois(latitude, longitude, box_width, box_height, tags):
    """
    Get points of interest at <latitude>,<longitude>
    with a bounding box of size <box_width> by <box_height>.
    The points matching the <tags> are fetched.
    """

    north, south, east, west = get_bounds(latitude, longitude, box_width, box_height)
    pois = ox.geometries_from_bbox(north, south, east, west, tags)
    return pois

def get_streets(latitude, longitude, box_width, box_height):
    """
    Returns the edges representing streets, as fetched from OpenStreetMap,
    within the bounding box
    """

    north, south, east, west = get_bounds(latitude, longitude, box_width, box_height)
    graph = ox.graph_from_bbox(north, south, east, west)
    nodes, edges = ox.graph_to_gdfs(graph)
    return edges

