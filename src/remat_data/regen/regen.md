# ReGen Bulk Submission Guide

ReGen (Regeneration) experiments track multi-generation polymer cycles — each
generation is deconstructed into oligomers and repolymerized into the next
generation. This tool validates a folder of ReGen experiments before uploading
to Clowder.

---

## Directory Layout

Create one subdirectory per experiment. Each subdirectory must contain exactly
one `Data Entry_*.xlsx` file.

```
submission_folder/
├── Batch_A/
│   └── Data Entry_Batch_A.xlsx
├── Batch_B/
│   └── Data Entry_Batch_B.xlsx
│   └── run_log.txt              ← auxiliary files are fine
└── Batch_C/
    └── Data Entry_Batch_C.xlsx
```

> The directory name is the experiment's unique identifier. It does not need to
> follow any ordering scheme — `Batch_A`, `Sample_042`, `Run_2024_05` are all
> valid. The tool builds the lineage from the parent references inside the xlsx,
> not from the names.

---

## Recording Parent References

Open the `oligomers` tab in your `Data Entry_*.xlsx`. List the **exact directory
name(s)** of any parent experiments in column A starting at row 2.

|     | A                      | B                 |
| --- | ---------------------- | ----------------- |
| 1   | Oligo ID               | Measured mass (g) |
| 2   | Batch_A                | 2.5               |
| 3   | _(next parent if any)_ |                   |
| …   |                        |                   |
| 13  | PROCEDURE              |                   |

- **Root experiments** (no parents) — leave A2 blank or go straight to
  `PROCEDURE`.
- **Multiple parents** — list each parent on a new row (A2, A3, A4, …).
- Stop adding rows before the `PROCEDURE` sentinel.
- The parent name must match the directory name **exactly**, including spaces
  and capitalisation.

---

## Supported Lineage Patterns

The tool supports any directed acyclic graph (DAG) of experiments.

```
# Linear chain          # Multiple parents         # Fan-out
Batch_A                 Batch_A   Batch_B           Batch_A
  └── Batch_B               └──┬──┘                ├── Batch_B
        └── Batch_C         Batch_C                 └── Batch_C
```

---

## Running the Validator

```bash
# Human-readable output
remat-data regen validate /path/to/submission_folder

# JSON output (for scripting)
remat-data regen validate /path/to/submission_folder --json
```

A successful run prints the dependency graph and the creation order (parents
always before children). Exit code is `0` on success, `1` if any errors are
found.

---

## Running the Test Suite

From the repo root:

```bash
# Run all ReGen tests
pytest tests/test_regen -v

# Run a specific test class
pytest tests/test_regen -v -k "TestSimpleChain"

# Run only error/failure cases
pytest tests/test_regen -v -k "TestMissing or TestCycle or TestSelf or TestNo or TestMultiple"
```

All tests use programmatically generated fixtures — no real xlsx files are
needed.

---

## Validation Errors

| Error            | Cause                                                                  | Fix                                     |
| ---------------- | ---------------------------------------------------------------------- | --------------------------------------- |
| `NO_XLSX`        | A subdirectory has no `Data Entry_*.xlsx`                              | Add the file or remove the empty folder |
| `MULTIPLE_XLSX`  | A subdirectory has more than one `Data Entry_*.xlsx`                   | Keep only one                           |
| `MISSING_PARENT` | A parent name in the oligomers tab doesn't match any sibling directory | Check spelling and capitalisation       |
| `SELF_REFERENCE` | An experiment lists its own directory name as a parent                 | Remove the self-referencing row         |
| `CYCLE`          | Two or more experiments reference each other in a loop                 | Break the circular dependency           |

---

## Example

Given this folder:

```
/data/regen_run/
├── Sample_042/        ← root (no parents)
├── Sample_043/        ← parent: Sample_042
└── Sample_044/        ← parents: Sample_042, Sample_043
```

`Sample_044/Data Entry_*.xlsx` oligomers tab:

```
A2: Sample_042
A3: Sample_043
```

Running the validator:

```bash
remat-data regen validate /data/regen_run
```

Output:

```
Dependency Graph
└── Sample_042 (root)
    ├── Sample_043
    │   └── Sample_044
    └── Sample_044

 Creation Order
 1   Sample_042   root
 2   Sample_043   child
 3   Sample_044   child
```
