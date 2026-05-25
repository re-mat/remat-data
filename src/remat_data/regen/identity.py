from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path

from openpyxl import Workbook


class IdentityResolver(ABC):
    @abstractmethod
    def resolve(self, subdir: Path, workbook: Workbook) -> str:
        pass


class DirectoryNameResolver(IdentityResolver):
    """Option 1: Use directory name as identity."""

    def resolve(self, subdir: Path, workbook: Workbook) -> str:
        return subdir.name


class FilenameStemResolver(IdentityResolver):
    """Option 2: Use xlsx filename stem as identity."""

    def resolve(self, subdir: Path, workbook: Workbook) -> str:
        xlsx_files = list(subdir.glob("Data Entry_*.xlsx"))
        if xlsx_files:
            return xlsx_files[0].stem
        return subdir.name


class OligoIdCellResolver(IdentityResolver):
    """Option 3: Read identity from a specific cell (e.g., general!B40)."""

    def __init__(self, sheet: str = "general", cell: str = "B40"):
        self.sheet = sheet
        self.cell = cell

    def resolve(self, subdir: Path, workbook: Workbook) -> str:
        try:
            if self.sheet in workbook.sheetnames:
                ws = workbook[self.sheet]
                value = ws[self.cell].value
                if value is not None:
                    return str(value).strip()
        except Exception:
            pass
        return subdir.name
