import datetime
import phonenumbers
import re

ZONE_ZIP_DICT = {
    'North Central (City)': [60614, 60625, 60640, 60618, 60202, 60613, 60201, 60657, 60615],
    'North West (City)': [60647, 60076, 60641, 60646, 60077, 60661, 60464],
    'Southside (City)': [60609, 60653, 60637, 60617, 60619, 60621, 60649],
    'Far North (Suburbs)': [60203, 60093, 60035, 60015, 60031, 60044, 60048, 60043, 60025, 60091, 60062],
    'Central East (City)': [60610, 60611, 60654, 60642],
    'Near West (Suburbs)': [60104, 60301, 60115, 60130, 60707, 60305, 60513, 60526, 60304, 60126, 60634, 60163, 60402],
    'Westside (City)': [60302],
    'North West (Suburb)': [60074, 60546, 60193, 60008, 60123, 60056, 60068, 60010, 60630, 60005, 60631, 60067, 60007, 60714, 60016],
    'South Loop (City)': [60608, 60605, 60607, 60616, 60602],
    'Central West (City)': [60651, 60639, 60624, 60623],
    'South West (Suburbs)': [60514, 60487, 60525, 60459, 60439, 60440, 60453, 60148, 60540, 60559, 60188, 60515],
    'South (Suburbs)': [60655, 60422, 60629, 60805, 60643, 60465, 60441, 60803, 60429],
    'North East (City)': [60626, 60660],
    'Central (City)': [60612, 60601, 60622],
    'Far West (Suburbs)': [60656, 60154, 60565, 60558, 60564, 60181, 60189, 60187, 60174, 60143, 60137]
}


def str_list_to_int_list(strlist):
    zips = strlist.strip("[]").split(",")
    zips = [ int(zzip.strip()) if len(zzip.strip()) > 0 else 0 for zzip in zips]
    return zips


def clean_phone_number(phone):
    if phone:
        nums = re.findall(r'\d+', phone)
        phone = ''.join(nums)
        if phone.startswith("+"):
            # do nothing
            return phone
        elif phone.startswith("1"):
            # add a +
            return "+%s" % phone
        else:
            # add a +1
            return "+1%s" % phone
    else:
        return None


def validate_phone_number(phone_number):
    """Validates a given phone_number using libphonenumber port of python.
    According to routific, this is what they use to validate phone numbers.
    """
    try:
        x = phonenumbers.parse(phone_number, None)
    except phonenumbers.phonenumberutil.NumberParseException as npe:
        print("Could not parse %s" % phone_number)
        print(str(npe))
        return False
    return phonenumbers.is_valid_number(x)


def format_date_for_routific(given_date):
    """
    Assuming the date format was given in %m/%d/%Y, this function converts to
    "%Y-%m-%d" format required by routific
    :param given_date:
    :return:
    """
    try:
        project_date = datetime.datetime.strptime(given_date, "%m/%d/%Y")
    except Exception as ex:
        print("error : " + str(ex))
        project_date = (datetime.datetime.now() + datetime.timedelta(
            days=1)).strftime("%Y-%m-%d")
    project_date = project_date.strftime("%Y-%m-%d")
    return project_date


def get_productid_qty(nq_str):
    pre = '">'
    post = '<span class="pc-tooltiptext">'
    name_qty_breaker = ': '
    print("nq_str=%s" % nq_str)
    s = nq_str[nq_str.index(pre) + len(pre):nq_str.index(post)]

    # name actually may be empty, so return product_id instead
    name, qty = tuple(s.rsplit(name_qty_breaker, 1))
    data_id_str = 'data-id="'
    product_id = ''
    if data_id_str in nq_str:
        product_id = nq_str[nq_str.index(data_id_str) + len(data_id_str):]
        product_id = product_id[:product_id.index('"')]
    return product_id, qty


def celcius_to_farenheit(deg_celsius):
    if type(deg_celsius) != float:
        try:
            deg_celsius = float(deg_celsius)
        except ValueError as ve:
            Exception("Invalid value %s" % deg_celsius)
    return (deg_celsius * 1.8) + 32
