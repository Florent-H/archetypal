import datetime as dt
import json
import logging as lg
import os
import sys
import unicodedata
from datetime import datetime, timedelta

import numpy as np
import pandas as pd
from pandas.io.json import json_normalize

import archetypal as ar
from . import load_umi_template
from . import settings


def config(data_folder=settings.data_folder,
           logs_folder=settings.logs_folder,
           imgs_folder=settings.imgs_folder,
           cache_folder=settings.cache_folder,
           use_cache=settings.use_cache,
           log_file=settings.log_file,
           log_console=settings.log_console,
           log_level=settings.log_level,
           log_name=settings.log_name,
           log_filename=settings.log_filename,
           useful_idf_objects=settings.useful_idf_objects,
           umitemplate=settings.umitemplate):
    """
    Configurations

    Args:
        data_folder (str): where to save and load data files
        logs_folder (str): where to write the log files
        imgs_folder (str): where to save figures
        cache_folder (str): where to save the simluation results
        use_cache (bool): if True, use a local cache to save/retrieve
            EnergyPlus simulation results instead of calling the API
            repetitively for the same requests. This can save a lot of time
            when simulations are long
        log_file (bool): if true, save log output to a log file in logs_folder
        log_console (bool): if true, print log output to the console
        log_level (int): one of the logger.level constants
        log_name (str): name of the logger
        log_filename (str): name of the log file
        useful_idf_objects (list): a list of useful idf objects
        umitemplate (str): where the umitemplate is located

    Returns:
        None

    """
    # set each global variable to the passed-in parameter value
    settings.use_cache = use_cache
    settings.cache_folder = cache_folder
    settings.data_folder = data_folder
    settings.imgs_folder = imgs_folder
    settings.logs_folder = logs_folder
    settings.log_console = log_console
    settings.log_file = log_file
    settings.log_level = log_level
    settings.log_name = log_name
    settings.log_filename = log_filename
    settings.useful_idf_objects = useful_idf_objects
    settings.umitemplate = umitemplate
    settings.common_umi_objects = get_list_of_common_umi_objects(
        settings.umitemplate)

    # if logging is turned on, log that we are configured
    if settings.log_file or settings.log_console:
        log('Configured archetypal')


def log(message, level=None, name=None, filename=None):
    """
    Write a message to the log file and/or print to the the console.

    Args:
        message (str): the content of the message to log
        level (int): one of the logger.level constants
        name (str): name of the logger
        filename (str): name of the log file

    Returns:
        None

    """
    if level is None:
        level = settings.log_level
    if name is None:
        name = settings.log_name
    if filename is None:
        filename = settings.log_filename

    # if logging to file is turned on
    if settings.log_file:
        # get the current logger (or create a new one, if none), then log
        # message at requested level
        logger = get_logger(level=level, name=name, filename=filename)
        if level == lg.DEBUG:
            logger.debug(message)
        elif level == lg.INFO:
            logger.info(message)
        elif level == lg.WARNING:
            logger.warning(message)
        elif level == lg.ERROR:
            logger.error(message)

    # if logging to console is turned on, convert message to ascii and print to
    # the console
    if settings.log_console:
        # capture current stdout, then switch it to the console, print the
        # message, then switch back to what had been the stdout. this prevents
        # logging to notebook - instead, it goes to console
        standard_out = sys.stdout
        sys.stdout = sys.__stdout__

        # convert message to ascii for console display so it doesn't break
        # windows terminals
        message = unicodedata.normalize('NFKD', make_str(message)).encode(
            'ascii', errors='replace').decode()
        print(message)
        sys.stdout = standard_out


def get_logger(level=None, name=None, filename=None):
    """
    Create a logger or return the current one if already instantiated.

    Args:
        level (int): one of the logger.level constants
        name (str): name of the logger
        filename (str): name of the log file

    Returns:
        logging.Logger: a Logger

    """

    if level is None:
        level = settings.log_level
    if name is None:
        name = settings.log_name
    if filename is None:
        filename = settings.log_filename

    logger = lg.getLogger(name)

    # if a logger with this name is not already set up
    if not getattr(logger, 'handler_set', None):

        # get today's date and construct a log filename
        todays_date = dt.datetime.today().strftime('%Y_%m_%d')
        log_filename = os.path.join(settings.logs_folder,
                                    '{}_{}.log'.format(filename, todays_date))

        # if the logs folder does not already exist, create it
        if not os.path.exists(settings.logs_folder):
            os.makedirs(settings.logs_folder)

        # create file handler and log formatter and set them up
        handler = lg.FileHandler(log_filename, encoding='utf-8')
        formatter = lg.Formatter(
            '%(asctime)s %(levelname)s %(name)s %(message)s')
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(level)
        logger.handler_set = True

    return logger


def make_str(value):
    """
    Convert a passed-in value to unicode if Python 2, or string if Python 3.

    Args:
        value (any): the value to convert to unicode/string

    Returns:
        unicode or string

    """
    try:
        # for python 2.x compatibility, use unicode
        return unicode(value)
    except NameError:
        # python 3.x has no unicode type, so if error, use str type
        return str(value)


def load_umi_template_objects(filename):
    """
    Reads

    Args:
        filename (str): path of template file

    Returns:
        dict: Dict of umi_objects

    """
    with open(filename) as f:
        umi_objects = json.load(f)
    return umi_objects


def umi_template_object_to_dataframe(umi_dict, umi_object):
    """
    Returns flattened DataFrame of umi_objects

    Args:
        umi_dict (dict): dict of umi objects
        umi_object (str): umi_object name

    Returns:
        pandas.DataFrame: flattened DataFrame of umi_objects

    """
    return json_normalize(umi_dict[umi_object])


def get_list_of_common_umi_objects(filename):
    """
    Returns list of common umi objects

    Args:
        filename (str): path to umi template file

    Returns:
        dict: Dict of common umi objects
    """
    umi_objects = load_umi_template(filename)
    components = {}
    for umi_dict in umi_objects:
        for x in umi_dict:
            #         print(umi_dict[x].columns.tolist())
            components[x] = umi_dict[x].columns.tolist()
    return components


def newrange(previous, following):
    """
    Takes the previous DataFrame and calculates a new Index range.
    Returns a DataFrame with a new index

    Args:
        previous (pandas.DataFrame): previous DataFrame
        following (pandas.DataFrame): follwoing DataFrame

    Returns:
        pandas.DataFrame: DataFrame with an incremented new index

    """
    if not previous.empty:
        from_index = previous.iloc[[-1]].index.values + 1
        to_index = from_index + len(following)

        following.index = np.arange(from_index, to_index)
        return following.rename_axis('$id')
    else:
        # If privious dataframe is empty, return the orginal DataFrame
        return following


def type_surface(row):
    """
    Takes a boundary and returns its corresponding umi-type

    Args:
        row:

    Returns:
        str: The umi-type of boundary
    """

    # Floors
    if row['Surface_Type'] == 'Floor':
        if row['Outside_Boundary_Condition'] == 'Surface':
            return 3
        if row['Outside_Boundary_Condition'] == 'Ground':
            return 2
        if row['Outside_Boundary_Condition'] == 'Outdoors':
            return 4
        else:
            return np.NaN

    # Roofs & Ceilings
    if row['Surface_Type'] == 'Roof':
        return 1
    if row['Surface_Type'] == 'Ceiling':
        return 3
    # Walls
    if row['Surface_Type'] == 'Wall':
        if row['Outside_Boundary_Condition'] == 'Surface':
            return 5
        if row['Outside_Boundary_Condition'] == 'Outdoors':
            return 0
    return np.NaN


def label_surface(row):
    """
    Takes a boundary and returns its corresponding umi-Category

    Args:
        row:

    Returns:

    """
    # Floors
    if row['Surface_Type'] == 'Floor':
        if row['Outside_Boundary_Condition'] == 'Surface':
            return 'Interior Floor'
        if row['Outside_Boundary_Condition'] == 'Ground':
            return 'Ground Floor'
        if row['Outside_Boundary_Condition'] == 'Outdoors':
            return 'Exterior Floor'
        else:
            return 'Other'

    # Roofs & Ceilings
    if row['Surface_Type'] == 'Roof':
        return 'Roof'
    if row['Surface_Type'] == 'Ceiling':
        return 'Interior Floor'
    # Walls
    if row['Surface_Type'] == 'Wall':
        if row['Outside_Boundary_Condition'] == 'Surface':
            return 'Partition'
        if row['Outside_Boundary_Condition'] == 'Outdoors':
            return 'Facade'
    return 'Other'


def layer_composition(row):
    """
    Takes in a series with $id and thickness values and return an array of
    dict of the form
    {'Material': {'$ref': ref, 'thickness': thickness}}
    If thickness is 'nan', it returns None.

    Args:
        row (pandas.Series): a row

    Returns (list): List of dicts

    """
    array = []
    ref = row['$id', 'Outside_Layer']
    thickness = row['Thickness', 'Outside_Layer']
    if np.isnan(ref):
        pass
    else:
        array.append({'Material': {'$ref': ref, 'thickness': thickness}})
        for i in range(2, len(row['$id']) + 1):
            ref = row['$id', 'Layer_{}'.format(i)]
            if np.isnan(ref):
                pass
            else:
                thickness = row['Thickness', 'Layer_{}'.format(i)]
                array.append(
                    {'Material': {'$ref': ref, 'thickness': thickness}})
        return array


def get_row_prop(self, other, on, property):
    """

    Todo:
        * Not used
        * This function may raise an error (it has to). Maybe we can do
        things better.

    Args:
        self:
        other:
        on:
        property:

    Returns:
        same type as caller

    """
    try:
        value_series = pd.DataFrame(self).T[on].join(
            other.reset_index().set_index([on[0], 'Name']), on=on,
            rsuffix='_viz')[property]
    except:
        raise ValueError()
    else:
        if len(value_series) > 1:
            log(
                'Found more than one possible values for property {} for item '
                '{}'.format(
                    property, self[on]),
                lg.WARNING)
            log('Taking the first occurrence...')

            index = value_series.index.values.astype(int)[0]
            value_series = value_series.values.astype(float)[0]
        elif value_series.isna().all():
            raise ValueError('No corresponding property was found')
        else:
            index = value_series.index.values.astype(int)[0]
            value_series = value_series.values.astype(float)[0]
        return index, value_series


def schedule_composition(row):
    """
    Takes in a series with $id and \*_ScheduleDay_Name values and return an
    array of dict of the form
    {'$ref': ref}

    Args:
        row (pandas.Series): a row

    Returns:
        list: list of dicts

    """
    # Assumes 7 days
    day_schedules = []
    days = ['Monday_ScheduleDay_Name',
            'Tuesday_ScheduleDay_Name',
            'Wednesday_ScheduleDay_Name',
            'Thursday_ScheduleDay_Name',
            'Friday_ScheduleDay_Name',
            'Saturday_ScheduleDay_Name',
            'Sunday_ScheduleDay_Name']  # With weekends last (as defined in
    # umi-template)
    # Let's start with the `Outside_Layer`
    for day in days:
        try:
            ref = row['$id', day]
        except:
            pass
        else:
            day_schedules.append({'$ref': ref})
    return day_schedules


def year_composition(row):
    """
    Takes in a series with $id and ScheduleWeek_Name_{} values and return an
    array of dict of the form
    {'FromDay': fromday, 'FromMonth': frommonth, 'Schedule': {'$ref': int(
    ref)}, 'ToDay': today, 'ToMonth': tomonth}

    Args:
        row (pandas.Series): a row

    Returns:
        list: list of dicts

    """
    parts = []
    for i in range(1, 26 + 1):
        try:
            ref = row['$id', 'ScheduleWeek_Name_{}'.format(i)]
        except:
            pass
        else:
            if ~np.isnan(ref):
                fromday = row['Schedules', 'Start_Day_{}'.format(i)]
                frommonth = row['Schedules', 'Start_Month_{}'.format(i)]
                today = row['Schedules', 'End_Day_{}'.format(i)]
                tomonth = row['Schedules', 'End_Month_{}'.format(i)]

                parts.append({'FromDay': fromday,
                              'FromMonth': frommonth,
                              'Schedule': {'$ref': int(ref)},
                              'ToDay': today,
                              'ToMonth': tomonth})
    return parts


def date_transform(date_str):
    """
    Simple function transforming one-based hours (1->24) into zero-based
    hours (0->23)

    Args:
        date_str (str): a date string of the form 'HH:MM'

    Returns:
        datetime.datetime: datetime object

    """
    if date_str[0:2] != '24':
        return datetime.strptime(date_str, '%H:%M') - timedelta(hours=1)
    return datetime.strptime('23:00', '%H:%M')


def time2time(row):
    """
    Constructs an array of 24 hour schedule points from a
    Shedule:Day:Interval object.

    Args:
        row (pandas.Series): a row

    Returns:
        numpy.ndarray: a numpy array of length 24

    """
    time_seg = []
    for i in range(1, 25):
        try:
            time = row['Time_{}'.format(i)]  # Time_i
            value = row['Value_Until_Time_{}'.format(i)]  # Value_Until_Time_i
        except:
            pass
        else:
            if str(time) != 'nan' and str(value) != 'nan':
                time = date_transform(time).hour
                times = np.ones(time + 1) * float(value)
                time_seg.append(times)
    arrays = time_seg
    array = time_seg[0]
    length = len(arrays[0])
    for i, a in enumerate(arrays):
        if i != 0:
            array = np.append(array, a[length - 1:-1])
            length = len(a)
    return array[0:24]


def iscore(row):
    """
    Helps to group by core and perimeter zones. If any of "has `core` in
    name" and "ExtGrossWallArea == 0" is true,
    will consider zone_loads as core, else as perimeter.

    Todo:
        * assumes a basement zone_loads will be considered as a core
        zone_loads since no ext wall area for basements.

    Args:
        row (pandas.Series): a row

    Returns:
        str: 'Core' or 'Perimeter'

    """
    if any(['core' in row[('Zones', 'Zone Name')].lower(),
            float(row[('Zones', 'Exterior Gross Wall Area {m2}')]) == 0]):
        # We look for the string `core` in the Zone_Name
        return 'Core'
    elif row[('Zones', 'Part of Total Building Area')] == 'No':
        return np.NaN
    elif 'plenum' in row[('Zones', 'Zone Name')].lower():
        return np.NaN
    else:
        return 'Perimeter'


def weighted_mean(series, df, weighting_variable):
    """
    Compute the weighted average while ignoring NaNs. Implements
    :func:`numpy.average`.

    Args:
        series (pandas.Series):
        df (pandas.DataFrame):
        weighting_variable (str or list or tuple): Weight name to use in
        *df*. If multiple values given, the values are
            multiplied together.

    Returns:
        numpy.ndarray: the weighted average
    """
    # get non-nan values
    index = ~np.isnan(series.values.astype('float'))

    # Returns weights. If multiple `weighting_variable`, df.prod will take care
    # of multipling them together.
    if not isinstance(weighting_variable, list):
        weighting_variable = [weighting_variable]
    try:
        weights = df.loc[series.index, weighting_variable].astype('float').prod(
            axis=1)
    except Exception:
        raise

    # Try to average
    try:
        wa = np.average(series[index].astype('float'), weights=weights[index])
    except ZeroDivisionError:
        log('Cannot aggregate empty series {}'.format(series.name), lg.WARNING)
        return np.NaN
    except Exception:
        raise
    else:
        return wa


def top(series, df, weighting_variable):
    """
    Compute the highest ranked value weighted by some other variable. Implements
        :func:`pandas.DataFrame.nlargest`.

    Args:
        series (pandas.Series): the *series* on which to compute the ranking.
        df (pandas.DataFrame): the *df* containing weighting variables.
        weighting_variable (str or list or tuple): Name of weights to use in
            *df*. If multiple values given, the values are multiplied together.

    Returns:
        numpy.ndarray: the weighted top ranked variable
    """
    # Returns weights. If multiple `weighting_variable`, df.prod will take care
    # of multipling them together.
    if not isinstance(series, pd.Series):
        raise TypeError('"top()" only works on Series, '
                        'not DataFrames\n{}'.format(series))

    if not isinstance(weighting_variable, list):
        weighting_variable = [weighting_variable]

    try:
        idx_ = df.loc[series.index].groupby(series.name).apply(
            lambda x: safe_prod(x, df, weighting_variable)
        )
        if not idx_.empty:
            idx = idx_.nlargest(1).index
        else:
            log('No such names "{}"'.format(series.name))
            return np.NaN
    except KeyError:
        log('Cannot aggregate empty series {}'.format(series.name), lg.WARNING)
        return np.NaN
    except Exception:
        raise
    else:
        if idx.isnull().any():
            return np.NaN
        else:
            return pd.to_numeric(idx, errors='ignore').values[0]


def safe_prod(x, df, weighting_variable):
    df_ = df.loc[x.index, weighting_variable]
    if not df_.empty:
        return df_.astype('float').prod(axis=1).sum()
    else:
        return 0


def copy_file(files):
    """Handles a copy of test idf files"""
    import shutil, os
    if isinstance(files, str):
        files = [files]
    files = {os.path.basename(k): k for k in files}
    for file in files:
        dst = os.path.join(ar.settings.cache_folder, file)
        output_folder = ar.settings.cache_folder
        if not os.path.isdir(output_folder):
            os.makedirs(output_folder)
        shutil.copyfile(files[file], dst)
        files[file] = dst

    return list(files.values())

    # scratch_then_cache is not necessary if we want to see the results
    # for file in files:
    #     dirname = os.path.dirname(files[file])
    #     if os.path.isdir(dirname):
    #         shutil.rmtree(dirname)



class Error(Exception):
    """Base class for exceptions in this module."""
    pass


class EnergyPlusProcessError(Error):
    """EnergyPlus Process call error"""

    def __init__(self, cmd, stderr, idf=None):
        self.cmd = cmd
        self.idf = idf
        self.stderr = stderr

    def __str__(self):
        """Override that only returns the stderr"""
        msg = ':\n'.join([self.idf, self.stderr])
        return msg