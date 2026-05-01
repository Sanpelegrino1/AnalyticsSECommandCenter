# Stage Demo Dataset From Downloads

## Purpose

Find a newly downloaded dataset zip under the local Downloads folder, create a stable folder under `Demos/`, extract the dataset there, and inventory the manifest and CSV files for the next Data Cloud steps.

## When to use it

Use this when a user says they downloaded a new demo dataset, wants the zip found in Downloads, wants a folder provisioned under `Demos/`, or wants the extracted files and manifest path gathered before Data Cloud setup.

## Inputs

- Optional zip path or file name when the archive is known exactly.
- Optional zip name pattern when the archive should be selected from Downloads by a partial name.
- Optional demo folder name when the folder under `Demos/` should differ from the archive name.
- Optional output path if the inventory should be persisted as JSON.

## Prerequisites

- The dataset is available as a `.zip` file in the local Downloads folder, or the operator knows the exact archive path.
- The repo workspace is available so the extracted files can be staged under `Demos/`.
- PowerShell `Expand-Archive` is available.

## Exact steps

1. Resolve the archive from Downloads with `scripts/bootstrap/stage-demo-dataset-from-downloads.ps1`, using `-ZipPath` when the file is known or `-ZipNamePattern` when it should be discovered.
2. Let the script derive the `Demos/<name>/` folder from the archive name, or pass `-DemoName` when a different stable demo folder name is needed.
3. Extract the archive into the staged demo folder and capture the returned inventory, especially the `manifest.json` path and the CSV list.
4. Use the returned manifest path as the starting point for `guided-data-cloud-manifest-setup.md`, `provision-data-cloud-manifest-streams.md`, or `publish-data-through-command-center.md`.

## Validation

- A new folder exists under `Demos/` for the dataset.
- The extracted directory contains the expected `manifest.json` and CSV files.
- The script output or JSON inventory lists the manifest and file count.

## Failure modes

- No zip file in Downloads matches the provided pattern.
- The destination folder already exists and should be replaced, but `-Force` was not supplied.
- The archive expands into an unexpected nested structure, so the manifest path must be taken from the returned inventory instead of guessed.

## Cleanup or rollback

- Remove the staged `Demos/<name>/` directory if the wrong archive was extracted.
- Rerun the script with `-Force` to replace an existing extracted dataset cleanly.

## Commands and links

- `scripts/bootstrap/stage-demo-dataset-from-downloads.ps1`
- `Demos/`
- `skills/guided-data-cloud-manifest-setup.md`
- `skills/provision-data-cloud-manifest-streams.md`
- `skills/publish-data-through-command-center.md`