from __future__ import annotations

import json
import mimetypes
from pathlib import Path

import requests
import typer
from pyclowder.client import ClowderClient
from rich.console import Console
from rich.progress import track
from rich.table import Table

from .config import config, space_map

with Path.open(Path("clowder_key.txt")) as f:
    key = f.read().strip()

clowder = ClowderClient(host="https://re-mat.clowder.ncsa.illinois.edu/", key=key)
console = Console()

app = typer.Typer(no_args_is_help=True)
spaces_app = typer.Typer(no_args_is_help=True)
datasets_app = typer.Typer(no_args_is_help=True)

app.add_typer(spaces_app, name="spaces")
app.add_typer(datasets_app, name="datasets")


def _upload_file_with_mimetype(dataset_id: str, file_path: str) -> bool:
    """Upload a file to Clowder with an explicit MIME type.

    Ensures formats like .mp4 are sent as video/mp4 instead of application/octet-stream
    so preview extractors can trigger correctly.
    """
    url = f"{config['clowder_base_url']}/api/uploadToDataset/{dataset_id}"
    guessed_mime_type, _ = mimetypes.guess_type(file_path)
    if not guessed_mime_type and file_path.lower().endswith(".mp4"):
        guessed_mime_type = "video/mp4"
    mime_type = guessed_mime_type or "application/octet-stream"
    console.print(f"Uploading {file_path} with MIME type {mime_type}")
    with Path.open(Path(file_path), "rb") as fp:
        files = {"file": (Path(file_path).name, fp, mime_type)}
        headers = {"X-API-Key": key}
        resp = requests.post(url, files=files, headers=headers, timeout=1800)
        return bool(resp.ok)


@spaces_app.command("list")
def spaces() -> None:
    """
    List all Clowder spaces.

    This command retrieves information about all spaces in your Clowder instance
    and displays them in a formatted table.
    """
    spaces_dict = clowder.get("/spaces")
    table = Table(title="Clowder Spaces")
    table.add_column("Name", style="cyan")
    table.add_column("ID", style="magenta")
    table.add_column("datasets", style="green")

    for space in spaces_dict:
        datasets = clowder.get(f"/spaces/{space['id']}/datasets")
        table.add_row(space["name"], space["id"], str(len(datasets)))

    console.print(table)


@spaces_app.command("download", no_args_is_help=True)
def download_space(space_id: str) -> None:
    """
    Download all datasets from a specified Clowder space.

    This command retrieves all datasets associated with the given space ID
    and downloads them to the current directory. The results are placed in
    a subdirectory named with the dataset's ID. It skips the download if the
    directory already exists.

    For each dataset it downloads a jsonld metadata file and a DSC_Curve.csv file.

    Args:
        space_id (str): The unique identifier of the Clowder space to download.

    Usage:
      remat-download-data spaces download <space_id>

    Example:
      remat-download-data spaces download abc123xyz

    Note:
    - Ensure you have sufficient disk space before downloading large spaces.
    - The download process may take some time depending on the number and size of datasets.
    """

    # First collect the datasets that need to be downloaded
    to_download = []
    datasets = clowder.get(f"/spaces/{space_id}/datasets")
    for dataset_rec in datasets:
        if not Path(dataset_rec["id"]).is_dir():
            to_download.append(dataset_rec)

    for dataset_rec in track(to_download, description="Downloading..."):
        download_dataset(dataset_rec["id"])


@datasets_app.command("list")
def list_datasets(space: str):
    """
    List all datasets in a specific space.
    """
    datasets = clowder.get(f"/spaces/{space}/datasets")  # Assuming this endpoint exists

    table = Table(title=f"Datasets in Space: {space}")
    table.add_column("Name", style="cyan")
    table.add_column("ID", style="magenta")

    for dataset in datasets:
        table.add_row(
            dataset.get("name", "N/A"),
            dataset.get("id", "N/A"),
        )

    console.print(table)


@datasets_app.command("download")
def download_dataset(dataset_id: str):
    download_dir = Path(dataset_id)
    download_dir.mkdir()
    metadata = clowder.get(f"/datasets/{dataset_id}/metadata.jsonld")
    with Path.open(Path(f"{dataset_id}/metadata.json"), "w") as metadata_file:
        json.dump(metadata, metadata_file, indent=4)

    dsc_file = [
        file
        for file in clowder.get(f"/datasets/{dataset_id}/files")
        if file["filename"] == "DSC_Curve.csv"
    ]

    if dsc_file:
        clowder.get_file(
            f"/files/{dsc_file[0]['id']}", download_dir / Path("DSC_Curve.csv")
        )


# To Avoid using function call in the fn signature
file_names_default = typer.Argument(...)


# Each space is a typer option
@spaces_app.command("upload", no_args_is_help=True)
def upload_file(
    cure: bool = typer.Option(False, "--Cure", help=" Space: DSC Cure Kinetics"),
    post_cure: bool = typer.Option(False, "--PostCure", help=" Space: DSC Post Cures"),
    front_velocity: bool = typer.Option(
        False, "--FrontVelocity", help=" Space: Front velocities"
    ),
    # Below is test space for batch upload
    # Remove the code after testing
    test: bool = typer.Option(
        False, "--Test", help=" Space: TEST Batch Upload (NOT FOR REAL EXPERIMENTS"
    ),
    dataset_name: str = typer.Option(
        None, "--name", help="Optional name for the dataset"
    ),
    file_names: list[str] = file_names_default,
) -> None:
    """
       Upload given files to a specified space

    This command uploads the files given in the arguments to the specified space_name.
    A default dataset is created and the files are uploaded under the newly created dataset

    Args:
        cure (bool): Flag to specify the DSC Cure Kinetics space
        post_cure (bool): Flag to specify the DSC Post Cures space,
        front_velocity (bool): Flag to specify the Front velocities space.
        dataset_name (str): Optional name for the dataset. If not provided, a default name is used.
        file_names List[str]: List of filenames to be uploaded. Files must be present at the directory where remat-data is run
    Usage:
       remat-data spaces upload --<space_name> --name <dataset_name> <file1> <file2>

    Example:
    remat-data spaces upload --DSC_Cure_Kinetics --name Test_Dataset test3.csv DSC_Curve.csv
    Note:
    - The space_name flag is mandatory. Use --help to see valid space names
    - Files to be uploaded must be in the directory where remat-data is installed/run
    """

    # Keep this dictionary consistent with the space_map in src/remat_data/config.py
    space_names = {
        "DSC Cure Kinetics": cure,
        "DSC Post Cures": post_cure,
        "Front velocities": front_velocity,
        "Test": test,
    }

    # Check if more than one space is specified or no space is specified
    if sum(space_names.values()) != 1:
        console.print("Error: You must specify exactly one space.")
        raise typer.Exit(code=1)

    if len(file_names) == 0:
        console.print("Error: You must specify at least one file to upload.")
        raise typer.Exit(code=1)

    # Get the first space name that is True (The space given by the user)
    space_name = next((name for name, value in space_names.items() if value), None)
    dataset_name = dataset_name if dataset_name else config["default_new_dataset_name"]
    space_id = space_map[space_name]
    console.print(f"Uploading to Space: {space_name} and {space_id}")

    # STEP 1: Create a new dummy dataset:
    payload = {
        "name": dataset_name,
        "description": "Dataset created by CLI",
        "space": [space_id],
        "collection": [],
    }

    resp = clowder.post("/datasets/createempty", payload)
    if not resp:
        console.print("Upload Failed: Failed to create a new dataset")
        return
    dataset_id = resp["id"]
    dataset_url = f"{config['clowder_base_url']}/{config['dataset_path']}/{dataset_id}?space={space_id}"

    # STEP 2: Upload files to the newly created dataset
    for file_name in track(file_names, description="Uploading...", console=console):
        mime_type, _ = mimetypes.guess_type(file_name)
        if mime_type == "video/mp4":
            ok = _upload_file_with_mimetype(dataset_id, file_name)
            if not ok:
                console.print(f"Error uploading file {file_name}")
        else:
            file_id = clowder.post_file(f"/uploadToDataset/{dataset_id}", file_name)
            if not file_id:
                console.print(f"Error uploading file {file_name}")

    console.print(f"Uploaded Files to newly created dataset: {dataset_url}")


def main():
    app()
