from dataclasses import dataclass
from pathlib import Path
import re
import boto3
import botocore
import requests
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

GRANULE_PATTERN_STR = r"NISAR_L2_\D{2}_(?P<product_type>\D{4})_\d{3}_(?P<track_id>\d{3})_\D_(?P<frame_id>\d{3})_(?:\d{3}_)?(?P<freq_a>\d{2})(?P<freq_b>\d{2})\D*(?P<start_time>\d{8}T\d{6})"
GRANULE_PATTERN = re.compile(GRANULE_PATTERN_STR)

"""Maps frequency range bandwidth values to corresponding postings, the first item being the preferred posting for that frequency
and the remainder being backups in ascending order
"""
# TODO: verify with Sam, the final ordering is
# TODO: verify 2.5 format (Is it like '2.5'/'02.5'/'2_5'?)
FREQ_POSTING_MAP = {
    "GCOV": {
        "05": [("080", "080"), ("020", "020"), ("010", "010")],
        "20": [("020", "020"), ("010", "010"), ("080", "080")],
        "77": [("020", "020"), ("010", "010"), ("080", "080")],
        "40": [("010", "010"), ("020", "020"), ("080", "080")],
    },
    "GSLC": {
        "05": [
            ("005", "040"),
            ("005", "010"),
            ("005", "005"),
            ("005", "2.5"),
            ("010", "010"),
            ("020", "020"),
            ("080", "080"),
        ],
        "20": [
            ("005", "010"),
            ("005", "005"),
            ("005", "2.5"),
            ("005", "040"),
            ("010", "010"),
            ("020", "020"),
            ("080", "080"),
        ],
        "40": [
            ("005", "005"),
            ("005", "2.5"),
            ("005", "010"),
            ("005", "040"),
            ("010", "010"),
            ("020", "020"),
            ("080", "080"),
        ],
        "77": [
            ("005", "2.5"),
            ("005", "005"),
            ("005", "010"),
            ("005", "040"),
            ("010", "010"),
            ("020", "020"),
            ("080", "080"),
        ],
    },
    # in vertex, GUNW should return both 080 and 020 version
    "GUNW": {
        "20": [("080", "080"), ("020", "020"), ("010", "010")],
        "40": [("080", "080"), ("020", "020"), ("010", "010")],
        "77": [("080", "080"), ("020", "020"), ("010", "010")],
    },
    "GOFF": {
        "20": [("080", "080"), ("020", "020"), ("010", "010")],
        "40": [("080", "080"), ("020", "020"), ("010", "010")],
        "77": [("080", "080"), ("020", "020"), ("010", "010")],
    },
}


# Template: https://nisar-services.earthdata.nasa.gov/redirect/NISAR_L2_STATIC/{granule_id}.h5
@dataclass
class Granule:
    product_type: str
    track_id: str
    frame_id: str
    freq_a: str
    freq_b: str
    start_time: str

    def match(self):
        pass

    def get_static_layer_prefix(self):
        return f"NISAR_L2_STATIC_{self.track_id}_A_{self.frame_id}_{self._get_posting()}_"
        

    def _get_posting(self) -> str:
        freq = self.freq_a if self.freq_a != '00' else self.freq_b
        posting = FREQ_POSTING_MAP[self.product_type][freq][0]
        return f'{posting[0]}_{posting[1]}'



def lambda_handler(event, context):
    print(f"boto3 version: {boto3.__version__}")
    print(f"botocore version: {botocore.__version__}")

    http_method = event["requestContext"]["http"]["method"]
    path: str = str(event["requestContext"]["http"]["path"])  # '.../.../{granule_id}.h5'

    if http_method == "GET":
        file_name = _get_file_name(path)
        granule = _get_granule(file_name)

    pass
    # return {
    #     'statusCode': 200,
    #     'body': 'Success'
    # }


def _get_granule(file_name: str) -> Granule:
    # Grab granule metadata from granule_id via regex
    result = GRANULE_PATTERN.match(file_name)

    if result is None:
        raise ValueError(f"Source granule file name {file_name} is not valid")

    data = result.groupdict()

    if any(v is None for v in data.values()):
        raise ValueError(f"Source granule file name {file_name} is not valid")

    return Granule(**data)


def _get_file_name(path: str) -> str:
    # verify no additional path parameters are in request and file has the expected extension
    p = Path(path)

    if len(p.parts) != 2:
        raise ValueError('Invalid file name provided. Expected "/{granule_id}.h5"')

    if p.suffix.lower() != ".h5":
        raise ValueError("Invalid file name provided. Expected .h5 file")

    return p.name
