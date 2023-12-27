from enum import Enum
from pathlib import Path
import re
from typing import Any, BinaryIO, Dict, Tuple
import json

SUPPORTED_MANIFEST_VERSIONS = {"min": 4, "max": 11}
SUPPORTED_CATALOG_VERSIONS = {"min": 1, "max": 1}


def extract_schema_version(input_file: Dict[str, Any]) -> Tuple[str, int]:
    dbt_schema_version_string = input_file["metadata"]["dbt_schema_version"]

    version_number = re.match(  # type: ignore [union-attr]
        "https://schemas.getdbt.com/dbt/.*/v([0-9]*).json", dbt_schema_version_string
    ).groups()[0]
    return dbt_schema_version_string, int(version_number)


def extract_invocation_id(input_file: Dict[str, Any]) -> str:
    return str(input_file["metadata"]["invocation_id"])


class DbtArtifactType(Enum):
    CATALOG = "catalog"
    MANIFEST = "manifest"


def verify_and_read_f(file: BinaryIO, artifact_type: DbtArtifactType) -> Dict[str, Any]:
    file.seek(0)
    loaded_file: Dict[str, Any] = json.load(file)

    try:
        version_string, version_number = extract_schema_version(loaded_file)
    except Exception:
        raise ValueError(
            f"Could not extract version number from provided {artifact_type.value} file."
        )

    if artifact_type == DbtArtifactType.CATALOG and (
        "/catalog/" in version_string
        and version_number >= SUPPORTED_CATALOG_VERSIONS["min"]
        and version_number <= SUPPORTED_CATALOG_VERSIONS["max"]
    ):
        return loaded_file
    elif artifact_type == DbtArtifactType.MANIFEST and (
        "/manifest/" in version_string
        and version_number >= SUPPORTED_MANIFEST_VERSIONS["min"]
        and version_number <= SUPPORTED_MANIFEST_VERSIONS["max"]
    ):
        return loaded_file
    else:
        min_version = SUPPORTED_CATALOG_VERSIONS["min"] if artifact_type == DbtArtifactType.CATALOG else SUPPORTED_MANIFEST_VERSIONS["min"]
        max_version = SUPPORTED_CATALOG_VERSIONS["max"] if artifact_type == DbtArtifactType.CATALOG else SUPPORTED_MANIFEST_VERSIONS["max"]
        raise ValueError(
            f"Unknown artifact type and/or unsupported version for {artifact_type.value}. " +
            f"Got version {version_number} but expected a version between {min_version} and {max_version}"
        )


def verify_and_read(file_path: Path, artifact_type: DbtArtifactType) -> Dict[str, Any]:
    with open(file_path, "r") as f:
        return verify_and_read_f(f, artifact_type)  # type: ignore [arg-type]
