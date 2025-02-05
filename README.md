# RE-MAT Data 

[![Actions Status][actions-badge]][actions-link]
[![Documentation Status][rtd-badge]][rtd-link]

[![PyPI version][pypi-version]][pypi-link]
[![Conda-Forge][conda-badge]][conda-link]
[![PyPI platforms][pypi-platforms]][pypi-link]

[![GitHub Discussion][github-discussions-badge]][github-discussions-link]

This package provides a simple interface to download and upload datasets used in the ReMat
project.

## Installation

This is a python package and can be installed using pip:

```bash
pip install remat-data-downloader
```

## Authentication

You need to obtain a Clowder API key to use this package. You can obtain this
key by logging into the
[RE-MAT Clowder instance](https://re-mat.clowder.ncsa.illinois.edu/) and going
to your user settings page (grey silhouette in the upper right corner of the
page). Click on the _API Keys_ tab and create a new key. Save this key in a file
nameed `clowder_key.txt` in the directory where you will be running the
`remat-download-data` command.

## Usage

The remat-data command can be run from your command line. It has
commands to interact with Clowder spaces and with datasets.

### List Spaces

```bash
remat-data spaces list

                      Clowder Spaces
┏━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Name              ┃ ID                       ┃ datasets ┃
┡━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ Front velocities  │ 6674972be4b0a2d1b9ba0228 │ 303      │
│ DSC Post Cures    │ 6669d4d0e4b0a2d1b9b9a797 │ 228      │
│ DSC Cure Kinetics │ 64343b6be4b01a23c58bad90 │ 307      │
└───────────────────┴──────────────────────────┴──────────┘

```

### Download Datasets

Now that you know the unique ID for the space you want to download, you can
download the datasets using the `download` command. This command will create
subdirectories for each dataset and download the metadata as a json file and the
DSC Curve as a csv file.

You can re-run this command, and it will skip downloads of datasets that already
exist in the directory.

```bash
remat-data spaces download 6669d4d0e4b0a2d1b9b9a797
```


### Upload Files to Space

Using the `upload` command, you can upload files to a space. The command takes
the space name and a list of file name to upload. A default dataset is created and the files are uploaded under the newly created dataset
Enclose in quotes if space name contains spaces

Space names and UUIDs Mapping, and other configurations are stored in the pyproject.toml file.

```bash
remat-data spaces upload "DSC Post Cures" data.csv data2.csv
```

<!-- SPHINX-START -->

<!-- prettier-ignore-start -->
[actions-badge]:            https://github.com/re-mat/remat-data-downloader/workflows/CI/badge.svg
[actions-link]:             https://github.com/re-mat/remat-data-downloader/actions
[conda-badge]:              https://img.shields.io/conda/vn/conda-forge/remat-data-downloader
[conda-link]:               https://github.com/conda-forge/remat-data-downloader-feedstock
[github-discussions-badge]: https://img.shields.io/static/v1?label=Discussions&message=Ask&color=blue&logo=github
[github-discussions-link]:  https://github.com/re-mat/remat-data-downloader/discussions
[pypi-link]:                https://pypi.org/project/remat-data-downloader/
[pypi-platforms]:           https://img.shields.io/pypi/pyversions/remat-data-downloader
[pypi-version]:             https://img.shields.io/pypi/v/remat-data-downloader
[rtd-badge]:                https://readthedocs.org/projects/remat-data-downloader/badge/?version=latest
[rtd-link]:                 https://remat-data-downloader.readthedocs.io/en/latest/?badge=latest

<!-- prettier-ignore-end -->
