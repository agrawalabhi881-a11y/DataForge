# DataForge automated tests

Run from the repository root with the virtual environment active:

```powershell
python -m pytest data_engineering/tests -v
```

The tests exercise schema mapping, quality, sufficiency, provenance and merging, splitting, lineage/version integrity, and service orchestration. They use in-memory synthetic examples and do not access external datasets or the network. They do not constitute complete coverage of loaders, cleaning modules, or the four domain processors; add dedicated tests for those modules and full backend integration before declaring the project complete.

The tests import implementation modules directly where possible, to avoid depending on package-level exports. Any failures must be investigated rather than skipped.
