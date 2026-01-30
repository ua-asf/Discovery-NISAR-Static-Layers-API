from datetime import datetime
import pytest
from NISARStaticLayersAPI.application import (
    Granule,
    _get_granule,
    _get_file_name,
    StaticGranule,
)

# Below are examples of how data should be parsed from the granule ids of the 4 L2 products
gslc_test_data = {
    "file_name": "NISAR_L2_PR_GSLC_055_132_A_029_4005_SHSH_A_20241021T082112_20241021T082134_T00408_N_P_J_001.h5",
    "granule": Granule(
        **{
            "product_type": "GSLC",
            "track_id": "132",
            "frame_id": "029",
            "freq_a": "40",
            "freq_b": "05",
            "start_time": "20241021T082112",
        },
    ),
    "static_layer_prefix": "NISAR_L2_STATIC_132_A_029_005_005_",
    # "static_layer": "NISAR_L2_STATIC_132_A_029_020_020_20250921T082112_R05000_J_001",
}


gcov_test_data = {
    "file_name": "NISAR_L2_PR_GCOV_045_112_D_085_2005_DHDH_M_20240621T233525_20240621T233601_T00408_N_F_J_001.h5",
    "granule": Granule(
        **{
            "product_type": "GCOV",
            "track_id": "112",
            "frame_id": "085",
            "freq_a": "20",
            "freq_b": "05",
            "start_time": "20240621T233525",
        }
    ),
    "static_layer_prefix": "NISAR_L2_STATIC_112_A_085_020_020_",
    # "static_layer": "NISAR_L2_STATIC_132_A_029_020_020_20250921T082112_R05000_J_001",
}

gunw_test_data = {
    "file_name": "NISAR_L2_PR_GUNW_039_002_D_123_040_4000_SH_20240403T084941_20240403T084954_20240415T084941_20240415T084954_T00407_N_P_J_001.h5",
    "granule": Granule(
        **{
            "product_type": "GUNW",
            "track_id": "002",
            "frame_id": "123",
            "freq_a": "40",
            "freq_b": "00",
            "start_time": "20240403T084941",
        }
    ),
    "static_layer_prefix": "NISAR_L2_STATIC_002_A_123_080_080_",
    # "static_layer": "NISAR_L2_STATIC_132_A_029_020_020_20250921T082112_R05000_J_001",
}

goff_test_data = gunw_test_data = {
    "file_name": "NISAR_L2_PR_GOFF_039_002_D_123_040_4000_SH_20240403T084941_20240403T084954_20240415T084941_20240415T084954_T00408_N_P_J_001.h5",
    "granule": Granule(
        **{
            "product_type": "GOFF",
            "track_id": "002",
            "frame_id": "123",
            "freq_a": "40",
            "freq_b": "00",
            "start_time": "20240403T084941",
        }
    ),
    "static_layer_prefix": "NISAR_L2_STATIC_002_A_123_080_080_",
    # "static_layer": "NISAR_L2_STATIC_002_A_123_080_080_20250921T082112_R05000_J_001",
}

static_granule_example = {
    "file_name": "NISAR_L2_STATIC_132_A_029_020_020_20250921T082112_R05000_J_001",
    "static_granule": StaticGranule(
        file_name="NISAR_L2_STATIC_132_A_029_020_020_20250921T082112_R05000_J_001",
        validity_start_time="20250921T082112",
        crid="R05000",
        counter="001",
    ),
}

test_data = [gslc_test_data, gcov_test_data, gunw_test_data, goff_test_data]

test_granule_paths = [
    {
        "path": "/NISAR_L2_PR_GSLC_055_132_A_029_4005_SHSH_A_20241021T082112_20241021T082134_T00408_N_P_J_001.h5",
        "file_name": "NISAR_L2_PR_GSLC_055_132_A_029_4005_SHSH_A_20241021T082112_20241021T082134_T00408_N_P_J_001.h5",
    },
    {
        "path": "/NISAR_L2_PR_GCOV_045_112_D_085_2005_DHDH_M_20240621T233525_20240621T233601_T00408_N_F_J_001.h5",
        "file_name": "NISAR_L2_PR_GCOV_045_112_D_085_2005_DHDH_M_20240621T233525_20240621T233601_T00408_N_F_J_001.h5",
    },
    {
        "path": "/NISAR_L2_PR_GUNW_039_002_D_123_040_4000_SH_20240403T084941_20240403T084954_20240415T084941_20240415T084954_T00407_N_P_J_001.h5",
        "file_name": "NISAR_L2_PR_GUNW_039_002_D_123_040_4000_SH_20240403T084941_20240403T084954_20240415T084941_20240415T084954_T00407_N_P_J_001.h5",
    },
    {
        "path": "/NISAR_L2_PR_GOFF_039_002_D_123_040_4000_SH_20240403T084941_20240403T084954_20240415T084941_20240415T084954_T00408_N_P_J_001.h5",
        "file_name": "NISAR_L2_PR_GOFF_039_002_D_123_040_4000_SH_20240403T084941_20240403T084954_20240415T084941_20240415T084954_T00408_N_P_J_001.h5",
    },
    {
        "path": "/hidden/path/NISAR_L2_PR_GOFF_039_002_D_123_040_4000_SH_20240403T084941_20240403T084954_20240415T084941_20240415T084954_T00408_N_P_J_001.h5",
        "raises": True,
    },
    {
        "path": "/hidden/path/NISAR_L2_PR_GOFF_039_002_D_123_040_4000_SH_20240403T084941_20240403T084954_20240415T084941_20240415T084954_T00408_N_P_J_001",
        "raises": True,
    },
    {
        "path": "/NISAR_L2_PR_GOFF_039_002_D_123_040_4000_SH_20240403T084941_20240403T084954_20240415T084941_20240415T084954_T00408_N_P_J_001",
        "raises": True,
    },
    {
        "path": "NISAR_L2_PR_GOFF_039_002_D_123_040_4000_SH_20240403T084941_20240403T084954_20240415T084941_20240415T084954_T00408_N_P_J_001",
        "raises": True,
    },
]


def test_get_granule():
    for data in test_data:
        assert data["granule"] == _get_granule(data["file_name"])

    # No match test
    with pytest.raises(ValueError):
        _get_granule("This_Should_Raise")

    # Partial match test
    with pytest.raises(ValueError):
        _get_granule("NISAR_L2_PR_GOFF_039.h5")


def test_get_granule_name():
    for granule in test_granule_paths:
        if granule.get("raises"):
            with pytest.raises(ValueError):
                _get_file_name(granule["path"])
        else:
            assert _get_file_name(granule["path"]) == granule["file_name"]


def test_Granule_match():
    for item in test_data:
        assert (
            item["granule"].get_static_layer_prefix(item["granule"].freq_a)
            == item["static_layer_prefix"]
        )
    pass


def test_static_granule_example():
    assert static_granule_example["static_granule"] == Granule.parse_static(
        static_granule_example["file_name"]
    )


def test_Granule_get_latest_valid_static_granule():
    start_time = datetime.fromisoformat("20251021T082112")
    latest_static_layer = Granule.get_latest_valid_static_granule(
        test_response, start_time
    )

    assert (
        latest_static_layer.file_name
        == "NISAR_L2_STATIC_132_A_029_020_020_20250921T082112_R05000_J_002"
    )
    pass


test_response = {
    "Contents": [
        {
            "Key": "NISAR_L2_STATIC_132_A_029_020_020_20251121T082112_R05000_J_001",
        },
        {
            "Key": "NISAR_L2_STATIC_132_A_029_020_020_20250921T082112_R05000_J_001",
        },
        {
            "Key": "NISAR_L2_STATIC_132_A_029_020_020_20250921T082112_R05000_J_002",
        },
        {
            "Key": "NISAR_L2_STATIC_132_A_029_020_020_20250821T082112_R05000_J_002",
        },
    ],
}
