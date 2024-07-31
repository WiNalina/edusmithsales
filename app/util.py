import pytz
import numpy as np


def datetimefilter(value, return_string=True, format="%d-%b-%Y %H:%M:%S"):
    """Transform the datetime from UTC timezone to local timezone

    Args:
        value (datetime.datetime): Input datetime with the UTC timezone
        return_string (bool, optional): A flag, which is True if the filter returns a string and false if the filter returns the datetime object. Defaults to True.
        format (str, optional): string of the output datetime format. Defaults to "%d/%m/%Y %H:%M:%S".

    Returns:
        str/datetime.datetime: the output datetime or datetime string for the local timezone
    """
    tz = pytz.timezone('Asia/Bangkok') # timezone you want to convert to from UTC
    utc = pytz.timezone('UTC')
    value = utc.localize(value, is_dst=None).astimezone(pytz.utc)
    local_dt = value.astimezone(tz)
    if return_string:
        return local_dt.strftime(format)
    else:
        return local_dt

def shortdatefilter(value):
    """Change the input datetime object to a short string form

    Args:
        value (datetime.datetime object): input datetime object to be shortened

    Returns:
        str: datetime object in a string form
    """
    return value.strftime('%d/%m/%Y')

def booleanfilter(value):
    """Change the input value from True or False to the words Yes or No

    Args:
        value (boolean/None): Given input to be transformed

    Returns:
        same type or str: the boolean value changed to 'Yes' or 'No' or just the value itself
    """
    if value is None or value in {'nan', 'NaN'} or np.isnan(value):
        return value
    else:
        assert value in {True, False}
        if value == True:
            return 'Yes'
        else:
            return 'No'

def missingfilter(value):
    """ Handle the missing data case from None/NaN to '-'

    Args:
        value (str/None): Input string or None value 

    Returns:
        (same type as the input/str): '-' or the same value as the input
    """
    if value in {'nan', 'NaN'} or value is None:
        return '-'
    else:
        return value

def mockfilter(value):
    """ Handle the mock exam case - if True, change to Mock. If False, change to blank space.

    Args:
        value (boolean): a flag indicating whether the exam is mock

    Returns:
        (str): string indicating if the exam is actual or mock
    """
    assert value in {True, False}
    if value == True:
        return 'Mock'
    else:
        return ''