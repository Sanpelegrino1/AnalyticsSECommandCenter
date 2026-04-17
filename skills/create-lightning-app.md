# Create a Lightning App

## Purpose

Create a Lightning app quickly for a demo org and make the result easy to revisit.

## When to use it

Use this when a demo needs a dedicated app shell or cleaner navigation context.

## Inputs

- Org alias.
- App name.
- Target profiles or permission sets.

## Prerequisites

- Authenticated org alias.
- Admin access in the org.

## Exact steps

1. Run `scripts/salesforce/open-setup-surface.ps1 -TargetOrg YOUR_ALIAS -Surface LightningApps`.
2. Create the Lightning app in Setup.
3. Add the tabs and branding needed for the demo.
4. Make the app visible to the required audiences.
5. If metadata retrieval is important, retrieve the application metadata afterward.

## Validation

- The app appears in App Launcher.
- The intended users can see it.
- The retrieved metadata reflects the app definition if you pulled it into source.

## Failure modes

- Visibility not applied: review app assignment and permission sets.
- Setup page opened in the wrong org: switch default alias and retry.

## Cleanup or rollback

- Remove the app from visibility assignments or delete it in Setup if it was created in error.

## Commands and links

- `scripts/salesforce/open-setup-surface.ps1`
- `scripts/salesforce/retrieve-metadata.ps1`
