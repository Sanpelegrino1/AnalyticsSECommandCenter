# Rotate Tableau PAT Safely

## Inputs

- New Tableau PAT name and secret.
- Optional target key to validate after rotation.

## Steps

1. Create the new PAT in Tableau Cloud.
2. Update only your local `.env.local` or user environment variables.
3. Do not store the PAT in tracked files or registries.
4. Run `scripts/tableau/auth-status.ps1` to validate the new credential.
5. Remove the old PAT from Tableau Cloud after validation succeeds.

## Validation

- `scripts/tableau/auth-status.ps1` returns an authenticated session.
- `scripts/tableau/list-projects.ps1` lists projects without errors.

## Failure modes

- PAT copied incorrectly: update `.env.local` and retry.
- Wrong site content URL: fix the target registry or `.env.local` and retry.
