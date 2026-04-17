# Salesforce Source Root

This is the standard Salesforce DX source-format root for active non-legacy metadata retrieved from and deployed to Salesforce orgs.

Typical folders will appear here after retrieval, such as:

- `applications`
- `connectedApps`
- `layouts`
- `lwc`
- `objects`
- `permissionsets`
- `staticresources`
- `triggers`

Retired Apex prompt-runtime classes and prompt flows were moved under `Salesforce Apex Legacy - No Longer Used/salesforce/force-app/main/default/`. The old `GenAiPromptTemplate` metadata mirror was removed during retirement cleanup.

Retrieve metadata into this tree with:

```powershell
sf project retrieve start --manifest manifest/package.xml --target-org MY_SANDBOX_ALIAS
```