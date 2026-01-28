import pytest
from NISARStaticLayersAPI.application import Granule, _get_granule, _get_file_name

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
        }
    ),
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
