from dataclasses import dataclass
import re
import boto3
import botocore
import requests
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

GRANULE_PATTERN_STR = r'NISAR_L2_\D{2}_(?P<product_type>\D{4})_\d{3}_(?P<track_id>\d{3})_\D_(?P<frame_id>\d{3})_(?:\d{3}_)?(?P<freq_a>\d{2})(?P<freq_b>\d{2})\D*(?P<start_time>\d{8}T\d{6})'
GRANULE_PATTERN = re.compile(GRANULE_PATTERN_STR)

# Template: https://nisar-services.earthdata.nasa.gov/redirect/NISAR_L2_STATIC/{granule_id}.h5
@dataclass
class Granule:
    product_type: str
    track_id: str
    frame_id: str
    freq_a: str
    freq_b: str
    start_time: str

def lambda_handler(event, context):
    print(f'boto3 version: {boto3.__version__}')
    print(f'botocore version: {botocore.__version__}')

    http_method = event['requestContext']['http']['method']
    path: str = str(event['requestContext']['http']['path']) # '.../.../{granule_id}.h5'


    if http_method == "GET": 
        granule_id = ""
        if (path.rfind("/") > -1):
            granule_id = path[path.rfind("/") +1: len(path)]
            if not granule_id.endswith('.h5'):
                return {
                    'statusCode': 400,
                    'body': "Invalid file, expected .h5 extension"
                }
        granule = _get_granule(granule_id)

    pass
    # return {
    #     'statusCode': 200,
    #     'body': 'Success'
    # }


def _get_granule(granule_id: str) -> Granule:
    # Grab granule metadata from granule_id via regex
    result = GRANULE_PATTERN.match(granule_id)
    data = result.groupdict()

    if any(v is None for v in data.values()):
        raise ValueError("Invalid source granule file name")

    return Granule(**data)
