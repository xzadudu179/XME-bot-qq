from xme.xmetools.reqtools import fetch_data_post
from keys import afdian_sign

async def fetch_afdian_post(method, **params):
    post_params = afdian_sign(params)
    return await fetch_data_post(f"https://afdian.com/api/open/{method}", **post_params)

