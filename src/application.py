import json
import traceback
from typing import Literal
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

STATIC_PATTERN_STR = r"NISAR_L2_STATIC_.*(?P<validity_start_time>\d{8}T\d{6})_(?P<crid>\D\d{5})_\D_(?P<counter>\d{3})"
STATIC_PATTERN = re.compile(STATIC_PATTERN_STR)

S3_BUCKET = 'sds-n-cumulus-prod-nisar-products'
"""Maps frequency range bandwidth values to corresponding postings, the first item being the preferred posting for that frequency
and the remainder being backups in ascending order
"""
# TODO: verify with Sam, the final ordering is
   # first preferred posting is accurate, secondary ordering subject to change
FREQ_POSTING_MAP = {
    "GCOV": {
        "05": [("0800", "0800"), ("0200", "0200"), ("0100", "0100")],
        "20": [("0200", "0200"), ("0100", "0100"), ("0800", "0800")],
        "77": [("0200", "0200"), ("0100", "0100"), ("0800", "0800")],
        "40": [("0100", "0100"), ("0200", "0200"), ("0800", "0800")],
    },
    "GSLC": {
        "05": [
            ("0050", "0400"),
            ("0050", "0100"),
            ("0050", "0050"),
            ("0050", "0025"),
            ("0100", "0100"),
            ("0200", "0200"),
            ("0800", "0800"),
        ],
        "20": [
            ("0050", "0100"),
            ("0050", "0050"),
            ("0050", "0025"),
            ("0050", "0400"),
            ("0100", "0100"),
            ("0200", "0200"),
            ("0800", "0800"),
        ],
        "40": [
            ("0050", "0050"),
            ("0050", "0025"),
            ("0050", "0100"),
            ("0050", "0400"),
            ("0100", "0100"),
            ("0200", "0200"),
            ("0800", "0800"),
        ],
        "77": [
            ("0050", "0025"),
            ("0050", "0050"),
            ("0050", "0100"),
            ("0050", "0400"),
            ("0100", "0100"),
            ("0200", "0200"),
            ("0800", "0800"),
        ],
    },
    # in vertex, GUNW should return both 080 and 020 version
    "GUNW": {
        "20": [("0800", "0800"), ("0200", "0200"), ("0100", "0100")],
        "40": [("0800", "0800"), ("0200", "0200"), ("0100", "0100")],
        "77": [("0800", "0800"), ("0200", "0200"), ("0100", "0100")],
    },
    "GOFF": {
        "20": [("0800", "0800"), ("0200", "0200"), ("0100", "0100")],
        "40": [("0800", "0800"), ("0200", "0200"), ("0100", "0100")],
        "77": [("0800", "0800"), ("0200", "0200"), ("0100", "0100")],
    },
}
boto_client = boto3.client("s3")

# example static
# NISAR_L2_STATIC_132_A_029_0200_0200_20250921T082112_R05000_J_001


# Template: https://nisar-services.earthdata.nasa.gov/redirect/NISAR_L2_STATIC/{granule_id}.h5


@dataclass
class StaticGranule:
    file_name: str
    validity_start_time: str
    crid: str # EMMmmp (Environment, Major release (zero padded), minor release (zero padded), patch release)
    counter: str

    def get_datetime(self):
        return datetime.fromisoformat(self.validity_start_time)

    def get_static_layer_url(self):
        # Tentative cloudfront url
        return f"https://nisar.asf.earthdatacloud.nasa.gov/NISAR/NISAR_L2_STATIC/{self.file_name[:-3]}/{self.file_name}"

    @staticmethod
    def _parse_crid(crid: str) -> dict:
        return {
        'environment': crid[0],
        'version': crid[1:],
    }

    @staticmethod
    def compare_crids(lhs: 'StaticGranule', rhs: 'StaticGranule') -> Literal[-1, 0, 1]:
        lhs_crid_info = StaticGranule._parse_crid(lhs.crid)
        rhs_crid_info = StaticGranule._parse_crid(rhs.crid)

        environment_comparison = StaticGranule._compare_crid_env(lhs_crid_info, rhs_crid_info)
        if environment_comparison != 0:
            return environment_comparison
        
        return StaticGranule._compare_crid_versions(lhs_crid_info, rhs_crid_info)
        
    @staticmethod
    def _compare_crid_env(lhs: dict, rhs: dict) -> Literal[-1, 0, 1]:
        # TODO: Confirm crid environment initials
        ranking = {
            'R': 3,
            'X': 2,
            'P': 1,
        }

        if ranking[lhs['environment']] > ranking[rhs['environment']]:
            return 1
        if ranking[lhs['environment']] < ranking[rhs['environment']]:
            return -1
        
        return 0

    @staticmethod
    def _compare_crid_versions(lhs: dict, rhs: dict) -> Literal[-1, 0, 1]:
        lhs_version = int(lhs['version'])
        rhs_version = int(rhs['version'])
        if lhs_version > rhs_version:
            return 1
        elif lhs_version < rhs_version:
            return -1
        
        return 0

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
            if not item["Key"].endswith('.h5'):
                continue
            file_name: str = item["Key"].split('/').pop()
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
                        crid_comparison = StaticGranule.compare_crids(target, static_granule)
                        if crid_comparison == 0:
                            if int(target.counter) < int(static_granule.counter):
                                target = static_granule
                        elif crid_comparison == -1:
                            target = static_granule

        return target

    def query_bucket(self, freq: str, posting: int):
        try:
            response = boto_client.list_objects_v2(
                # TODO: Get the actual bucket name
                Bucket=S3_BUCKET,
                MaxKeys=50,
                Prefix=f"NISAR_L2_STATIC/{self.get_static_layer_prefix(freq, posting)}",
            )

        except Exception as e:
            raise FileNotFoundError(
                f"Unable to find valid file (unable to find source bucket). {e}"
            )

        if "Contents" not in response:
            raise FileNotFoundError("Unable to find valid file (unable to find source bucket).")
        
        return response

    def get_datetime(self):
        return datetime.fromisoformat(self.start_time)

    @staticmethod
    def parse_static(file_name: str) -> StaticGranule:
        result = STATIC_PATTERN.match(file_name)

        if result is None:
            raise ValueError(f"unable to parse static granule {file_name} is not valid")

        return StaticGranule(file_name, **result.groupdict())

def redirect_interface(event, context):
    body = """
    <html>
        <head>
            <title>NISAR Static Layers</title>
        </head>
        <style>
            body {
                background: rgb(28 25 23 / var(--tw-bg-opacity, 1));
                color: rgb(214, 211, 209);
                font-family:
                    ui-sans-serif, system-ui, sans-serif, "Apple Color Emoji",
                    "Segoe UI Emoji", "Segoe UI Symbol", "Noto Color Emoji";
                display: flex;
                place-items: center;
                flex-direction: column;
                margin-top: 5%;
            }
            h1 {
                color: #ffffff;
            }
            a {
                color: #ffffff;
            }
            hr {
                width: 80%;
            }
        </style>
        <body>
            <h1>NISAR Static Layers</h1>
            <hr />
            <p>
                Some ancillary datasets are the same for each frame over time.
                Rather than packaging these files in the main HDF5 files, they will
                be made available as a separate static layers file for each frame.
            </p>

            <p>These NISAR static layers are not yet available.</p>
            <h3>
                For more info visit the
                <a href="https://nisar-docs.asf.alaska.edu/static-layers/"
                    >NISAR Docs</a
                >
            </h3>
        </body>
    </html>
    """
    return {
            "statusCode": 200,
            "body": body,
            "headers": {
                'Content-Type': 'text/html',
            },
        }

def lambda_handler(event, context):
    print(f"boto3 version: {boto3.__version__}")
    print(f"botocore version: {botocore.__version__}")
    try:
        http_method = event["requestContext"]["httpMethod"]
        path: str = str(event["requestContext"]["path"])  # '.../.../{granule_id}.h5'

        if http_method == "GET":
            file_name = _get_file_name(path)
            granule = _get_granule(file_name)
            static_layer = granule.get_static_layer_granule()

            return static_layer.get_static_layer_url()
        else:
            return {"statusCode": "405", "body": HTTPStatus.METHOD_NOT_ALLOWED}
    except ValueError as e:
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": json.dumps({"error": str(e)}),
        }
    except FileNotFoundError:
        return {
            "statusCode": 404,
            "headers": {"Content-Type": "application/json"},
            "body": "{'error': 'File Not Found'}",
        }
    except Exception as e:
        traceback.print_exc()
        return {
            "statusCode": 400,
            "headers": {"Content-Type": "application/json"},
            "body": "{'error': 'Invalid url format'}",
        }


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
