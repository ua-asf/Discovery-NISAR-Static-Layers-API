import boto3.session
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime
import re
import boto3
import botocore
import logging
from http import HTTPStatus


logger = logging.getLogger()
logger.setLevel(logging.INFO)

GRANULE_PATTERN_STR = r"NISAR_L2_\D{2}_(?P<product_type>\D{4})_\d{3}_(?P<track_id>\d{3})_\D_(?P<frame_id>\d{3})_(?:\d{3}_)?(?P<freq_a>\d{2})(?P<freq_b>\d{2})\D*(?P<start_time>\d{8}T\d{6})"
GRANULE_PATTERN = re.compile(GRANULE_PATTERN_STR)

STATIC_PATTERN_STR = r"NISAR_L2_STATIC_.*(?P<validity_start_time>\d{8}T\d{6})_(?P<crid>R\d{5})_\D_(?P<counter>\d{3})"
STATIC_PATTERN = re.compile(STATIC_PATTERN_STR)
"""Maps frequency range bandwidth values to corresponding postings, the first item being the preferred posting for that frequency
and the remainder being backups in ascending order
"""
# TODO: verify with Sam, the final ordering is
# TODO: verify 2.5 format (Is it like '2.5'/'02.5'/'2_5'?)
# may add extra 0, ie: 0.2 -> 0025, 080 -> 0800, etc, or drop zero (800, 200, 025, etc)
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
# boto_client = boto3.client("s3")

# example static
# NISAR_L2_STATIC_132_A_029_020_020_20250921T082112_R05000_J_001


# Template: https://nisar-services.earthdata.nasa.gov/redirect/NISAR_L2_STATIC/{granule_id}.h5


@dataclass
class StaticGranule:
    file_name: str
    validity_start_time: str
    crid: str  # TODO: Find out crid numbering convention and whether it's relevant, or if only counter is necessary
    counter: str

    def get_datetime(self):
        return datetime.fromisoformat(self.validity_start_time)

    def get_static_layer_url(self):
        # Tentative cloudfront url
        return f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_STATIC/{self.file_name[:-3]}/{self.file_name}"


@dataclass
class Granule:
    product_type: str
    track_id: str
    frame_id: str
    freq_a: str
    freq_b: str
    start_time: str

    def get_static_layer_prefix(self, freq: str, preferred_posting_idx: int = 0):
        return f"NISAR_L2_STATIC_{self.track_id}_A_{self.frame_id}_{self._get_posting(freq, preferred_posting_idx)}_"

    def _get_posting(self, freq: str, preferred_posting_idx: int) -> str:
        posting = FREQ_POSTING_MAP[self.product_type][freq][preferred_posting_idx]
        return f"{posting[0]}_{posting[1]}"

    def get_static_layer_granule(self) -> StaticGranule:
        freq = self.freq_a if self.freq_a != "00" else self.freq_b
        total_postings = len(FREQ_POSTING_MAP[self.product_type][freq])

        target: StaticGranule | None = None
        for posting in range(total_postings):
            response = self.query_bucket(freq, posting)
            start_time = self.get_datetime()
            target = self.get_latest_valid_static_granule(response, start_time)
            if target is not None:
                break

        if target is None:
            raise FileNotFoundError("Unable to find valid static layer for granule")

        return target

    @staticmethod
    def get_latest_valid_static_granule(
        results: dict, start_time: datetime
    ) -> StaticGranule | None:
        """Returns latest valid static granule file name from boto3 s3 client response for given granule start time
        Validity Criteria:
        1. Validity start time must be before granule start time
        2. Validity start time must latest available date
        3. If two static layer share a validity start time, take the one with the higher CRID count
        """
        target: StaticGranule | None = None
        for item in results["Contents"]:
            file_name: str = item["Key"]
            static_granule = Granule.parse_static(file_name=file_name)

            validity_start_time = static_granule.get_datetime()

            if validity_start_time < start_time:
                if target is None:
                    target = static_granule
                else:
                    target_date = target.get_datetime()
                    if target_date < validity_start_time:
                        target = static_granule
                    elif target_date == validity_start_time:
                        if int(target.counter) < int(static_granule.counter):
                            target = static_granule

        return target

    def query_bucket(self, freq: str, posting: int):
        try:
            response = boto_client.list_objects_v2(
                # TODO: Get the actual bucket name
                Bucket="s3://sds-n-cumulus-prod-nisar-products",
                MaxKeys=50,
                Prefix=f"NISAR_L2_STATIC/{self.get_static_layer_prefix(freq, posting)}",
            )
        except Exception as e:
            raise FileNotFoundError(
                f"Unable to find valid file (unable to find source bucket). {e}"
            )

        return response

    def get_datetime(self):
        return datetime.fromisoformat(self.start_time)

    @staticmethod
    def parse_static(file_name: str) -> StaticGranule:
        result = STATIC_PATTERN.match(file_name)

        if result is None:
            raise ValueError(f"unable to parse static granule {file_name} is not valid")

        return StaticGranule(file_name, **result.groupdict())


def lambda_handler(event, context):
    print(f"boto3 version: {boto3.__version__}")
    print(f"botocore version: {botocore.__version__}")
    try:
        http_method = event["requestContext"]["http"]["method"]
        path: str = str(
            event["requestContext"]["http"]["path"]
        )  # '.../.../{granule_id}.h5'
    except Exception as e:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": "{'error': 'Invalid url format'}",
        }
    # if http_method == "GET":
    #     file_name = _get_file_name(path)
    #     granule = _get_granule(file_name)
    #     static_layer = granule.get_static_layer_file_key()

    http_method = event["requestContext"]["http"]["method"]
    path: str = str(
        event["requestContext"]["http"]["path"]
    )  # '.../.../{granule_id}.h5'

    if http_method == "GET":
        file_name = _get_file_name(path)
        granule = _get_granule(file_name)
        static_layer = granule.get_static_layer_granule()

        return static_layer.get_static_layer_url()
    else:
        return {"statusCode": "405", "body": HTTPStatus.METHOD_NOT_ALLOWED}
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

    return Granule(**data)


def _get_file_name(path: str) -> str:
    # verify no additional path parameters are in request and file has the expected extension
    p = Path(path)

    if len(p.parts) != 2:
        raise ValueError('Invalid file name provided. Expected "/{granule_id}.h5"')

    if p.suffix.lower() != ".h5":
        raise ValueError("Invalid file name provided. Expected .h5 file")

    return p.name
