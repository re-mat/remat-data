from __future__ import annotations

from pathlib import Path

import pytest

from remat_data.regen import validate_directory
from remat_data.regen.identity import DirectoryNameResolver, FilenameStemResolver


class TestSimpleChain:
    def test_simple_chain(self, simple_chain: Path):
        report = validate_directory(simple_chain)

        assert report.ok, f"Expected success, got errors: {report.errors}"
        assert len(report.ordered_subdirs) == 3
        assert report.ordered_subdirs[0].name == "Gen 0"
        assert report.ordered_subdirs[1].name == "Gen 1"
        assert report.ordered_subdirs[2].name == "Gen 2"

        assert "Gen 0" in report.roots
        assert "Gen 1" not in report.roots
        assert "Gen 2" not in report.roots

        assert report.graph["Gen 0"] == []
        assert report.graph["Gen 1"] == ["Gen 0"]
        assert report.graph["Gen 2"] == ["Gen 1"]


class TestDiamond:
    def test_diamond(self, diamond: Path):
        report = validate_directory(diamond)

        assert report.ok, f"Expected success, got errors: {report.errors}"
        assert len(report.ordered_subdirs) == 4

        order = [d.name for d in report.ordered_subdirs]
        assert order[0] == "A"
        assert set(order[1:3]) == {"B", "C"}
        assert order[3] == "D"

        assert report.graph["D"] == ["B", "C"]


class TestMultiParent:
    def test_multi_parent(self, multi_parent: Path):
        report = validate_directory(multi_parent)

        assert report.ok, f"Expected success, got errors: {report.errors}"
        assert len(report.ordered_subdirs) == 3

        child_sheet = report.sheets["Child"]
        assert len(child_sheet.parents) == 2
        assert [p.value for p in child_sheet.parents] == ["Parent1", "Parent2"]


class TestMultiChild:
    def test_multi_child(self, multi_child: Path):
        report = validate_directory(multi_child)

        assert report.ok, f"Expected success, got errors: {report.errors}"
        assert len(report.ordered_subdirs) == 3

        assert report.graph["Parent"] == []
        assert report.graph["Child1"] == ["Parent"]
        assert report.graph["Child2"] == ["Parent"]


class TestRootsOnly:
    def test_roots_only(self, roots_only: Path):
        report = validate_directory(roots_only)

        assert report.ok, f"Expected success, got errors: {report.errors}"
        assert len(report.ordered_subdirs) == 3
        assert set(report.roots) == {"Exp1", "Exp2", "Exp3"}


class TestMissingParent:
    def test_missing_parent(self, missing_parent: Path):
        report = validate_directory(missing_parent)

        assert not report.ok
        assert len(report.errors) == 1
        assert report.errors[0].code == "MISSING_PARENT"
        assert "NonExistentParent" in report.errors[0].involved


class TestCycle:
    def test_cycle(self, cycle_fixture: Path):
        report = validate_directory(cycle_fixture)

        assert not report.ok
        assert any(e.code == "CYCLE" for e in report.errors)


class TestSelfReference:
    def test_self_reference(self, self_reference: Path):
        report = validate_directory(self_reference)

        assert not report.ok
        assert len(report.errors) == 1
        assert report.errors[0].code == "SELF_REFERENCE"


class TestNoXlsx:
    def test_no_xlsx(self, no_xlsx: Path):
        report = validate_directory(no_xlsx)

        assert not report.ok
        assert any(e.code == "NO_XLSX" for e in report.errors)


class TestMultipleXlsx:
    def test_multiple_xlsx(self, multiple_xlsx: Path):
        report = validate_directory(multiple_xlsx)

        assert not report.ok
        assert any(e.code == "MULTIPLE_XLSX" for e in report.errors)


class TestIdentityResolvers:
    def test_directory_name_resolver(self, simple_chain: Path):
        resolver = DirectoryNameResolver()
        report = validate_directory(simple_chain, resolver=resolver)

        assert report.ok
        assert "Gen 0" in report.roots
