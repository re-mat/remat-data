from __future__ import annotations

from pathlib import Path

from .graph import ValidationError, build_graph, topological_sort
from .identity import DirectoryNameResolver, IdentityResolver
from .parser import find_xlsx_in_subdir, parse_regen_sheet
from .report import ValidationReport


def validate_directory(
    submission_path: Path | str,
    resolver: IdentityResolver | None = None,
) -> ValidationReport:
    """
    Validate a ReGen submission directory.

    Args:
        submission_path: Root directory containing subdirs (each with one Data Entry_*.xlsx)
        resolver: IdentityResolver (default: DirectoryNameResolver)

    Returns:
        ValidationReport with ordered subdirs, graph, roots, and any errors
    """
    if resolver is None:
        resolver = DirectoryNameResolver()

    submission_path = Path(submission_path)
    if not submission_path.is_dir():
        return ValidationReport(
            ordered_subdirs=[],
            graph={},
            roots=[],
            sheets={},
            errors=[
                ValidationError(
                    code="INVALID_PATH",
                    subdir=None,
                    message=f"Path does not exist or is not a directory: {submission_path}",
                )
            ],
        )

    errors = []
    sheets = {}
    all_subdirs = sorted([d for d in submission_path.iterdir() if d.is_dir()])

    for subdir in all_subdirs:
        xlsx_files = find_xlsx_in_subdir(subdir)

        if len(xlsx_files) == 0:
            errors.append(
                ValidationError(
                    code="NO_XLSX",
                    subdir=subdir,
                    message=f"No Data Entry_*.xlsx found in {subdir.name}",
                )
            )
            continue
        if len(xlsx_files) > 1:
            errors.append(
                ValidationError(
                    code="MULTIPLE_XLSX",
                    subdir=subdir,
                    message=f"Multiple Data Entry_*.xlsx files found in {subdir.name}",
                    involved=[f.name for f in xlsx_files],
                )
            )
            continue

        sheet = parse_regen_sheet(subdir, resolver)
        if sheet is None:
            errors.append(
                ValidationError(
                    code="PARSE_ERROR",
                    subdir=subdir,
                    message=f"Failed to parse {xlsx_files[0].name}",
                )
            )
            continue

        identity = resolver.resolve(
            subdir, sheet.workbook_handle or sheet.load_workbook()
        )
        sheet.identity = identity

        if identity in sheets:
            errors.append(
                ValidationError(
                    code="DUPLICATE_IDENTITY",
                    subdir=subdir,
                    message=f"Identity '{identity}' is not unique",
                    involved=[identity],
                )
            )
            continue

        sheets[identity] = sheet

    if errors:
        return ValidationReport(
            ordered_subdirs=[], graph={}, roots=[], sheets=sheets, errors=errors
        )

    graph, graph_errors = build_graph(sheets)
    errors.extend(graph_errors)

    if graph_errors:
        return ValidationReport(
            ordered_subdirs=[], graph=graph, roots=[], sheets=sheets, errors=errors
        )

    topo_order, cycle_errors = topological_sort(graph)
    errors.extend(cycle_errors)

    if cycle_errors:
        return ValidationReport(
            ordered_subdirs=[],
            graph=graph,
            roots=[s for s in sheets.values() if s.is_root],
            sheets=sheets,
            errors=errors,
        )

    roots = [identity for identity, sheet in sheets.items() if sheet.is_root]

    ordered_subdirs = [
        sheets[identity].subdir for identity in topo_order if identity in sheets
    ]

    return ValidationReport(
        ordered_subdirs=ordered_subdirs,
        graph=graph,
        roots=roots,
        sheets=sheets,
        errors=errors,
    )
