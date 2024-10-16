import hmac
import hashlib
import base64

def get_luck(__identifier__, __key__, date=None, digits=8):
    """
    Calculates a luck value based on the given identifier, key, and optional date.

    Args:
        __identifier__: A unique identifier, usually a long integer.
        __key__: A secret key used for HMAC calculation, in base64 format.
        date: An optional date object. If not provided, the current date is used.
        digits: The number of digits in the returned luck value.

    Returns:
        An integer representing the luck value.
    """

    # Get the day since the beginning of the common era
    if date is None:
        import datetime
        date = datetime.datetime.now()
    day = date.toordinal()

    # Create a 64-bit seed by combining the identifier and day
    seed = (__identifier__ & 0x000000FFFFFFFFFF) | (day << 40)

    # Convert the seed to bytes
    seed_bytes = seed.to_bytes(8, byteorder='big')

    # Calculate the HMAC-SHA1 hash
    try:
        __key__ = base64.b64decode(__key__)
        hmac_sha1 = hmac.new(__key__, seed_bytes, hashlib.sha1)
        hash_value = hmac_sha1.digest()

        # Dynamic truncation
        offset = hash_value[19] & 0x0f
        code = int.from_bytes(hash_value[offset:offset+4], byteorder='big') & 0x7fffffff

        # Adjust the code based on the desired number of digits
        divider = 10 ** digits
        code %= divider

        return code
    except (TypeError, ValueError) as ex:
        print(ex)
        return -1
