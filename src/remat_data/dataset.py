from __future__ import annotations

import json
from pathlib import Path

import typer
import tomli
from pyclowder.client import ClowderClient
from rich.console import Console
from rich.progress import track
from rich.table import Table

with Path.open(Path("clowder_key.txt")) as f:
    key = f.read().strip()


def load_config():
    with Path("pyproject.toml").open("rb") as f:
        config = tomli.load(f)
    return config["tool"]["remat_data"]

properties = load_config()
config = properties["config"]
space_map = properties["spaces"]

clowder = ClowderClient(host="https://re-mat.clowder.ncsa.illinois.edu/", key=key)

console = Console()

app = typer.Typer(no_args_is_help=True)
spaces_app = typer.Typer(no_args_is_help=True)
datasets_app = typer.Typer(no_args_is_help=True)

app.add_typer(spaces_app, name="spaces")
app.add_typer(datasets_app, name="datasets")


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


@spaces_app.command("upload", no_args_is_help=True)
def upload_file(space_name: str, file_names: list[str] = typer.Argument(...)) -> None:
    """
       Upload given files to a specified space

    This command uploads the files given in the arguments to the specified space_name.
    A default dataset is created and the files are uploaded under the newly created dataset

    Args:
        space_name (str): The Clowder space name where the files must be uploaded.
        file_names List[str]: List of filenames to be uploaded. Files must be present at the directory where remat-data is run
    Usage:
      remat-data spaces upload <space_name> <file_name1> <file_name2> <file_name3> ...

    Example:
      remat-data spaces upload sample_space test_file.txt test_file2.txt

    Note:
    - The space name must match exactly with the one in Clowder
    - Files to be uploaded must be in the directory where remat-data is installed/run
    """
    space_id = space_map[space_name]

    # STEP 1: Create a new dummy dataset:
    payload  = {
  "name": config['default_new_dataset_name'], #TODO: Change this to the actual file name from arg
  "description": "Default dataset created by CLI",
  "space": [space_id],
  "collection": []
}
    resp = clowder.post("/datasets/createempty", payload)
    if not resp:
        console.print("Upload Failed: Failed to create a new dataset")
        return
    dataset_id = resp["id"]
    dataset_url = f"{config[f'clowder_base_url']}/{config['dataset_path']}/{dataset_id}?space={space_id}"

    # STEP 2: Upload files to the newly created dataset
    for file_name in track(file_names, description="Uploading..."):

        file_id = clowder.post_file(f"/uploadToDataset/{dataset_id}", file_name)
        if not file_id:
            console.print(f"Error uploading file {file_name}")


    console.print(f"Uploaded Files to newly created dataset: {dataset_url}")


def main():
    app()


