$relationships = @(
    @{
        apiName = 'projects_affiliate_id_to_affiliates_affiliate_id'
        label = 'projects.affiliate_id -> affiliates.affiliate_id'
        leftSemanticDefinitionApiName = 'Projects5'
        rightSemanticDefinitionApiName = 'Affiliates5'
        criteria = @(@{
            leftSemanticFieldApiName = 'affiliate_id7'
            rightSemanticFieldApiName = 'affiliate_id7'
        })
    },
    @{
        apiName = 'milestones_project_id_to_projects_project_id'
        label = 'milestones.project_id -> projects.project_id'
        leftSemanticDefinitionApiName = 'Milestones5'
        rightSemanticDefinitionApiName = 'Projects5'
        criteria = @(@{
            leftSemanticFieldApiName = 'project_id7'
            rightSemanticFieldApiName = 'project_id7'
        })
    },
    @{
        apiName = 'bom_lines_project_id_to_projects_project_id'
        label = 'bom_lines.project_id -> projects.project_id'
        leftSemanticDefinitionApiName = 'Bom_Lines5'
        rightSemanticDefinitionApiName = 'Projects5'
        criteria = @(@{
            leftSemanticFieldApiName = 'project_id7'
            rightSemanticFieldApiName = 'project_id7'
        })
    },
    @{
        apiName = 'procurement_orders_project_id_to_projects_project_id'
        label = 'procurement_orders.project_id -> projects.project_id'
        leftSemanticDefinitionApiName = 'Procurement_Orders5'
        rightSemanticDefinitionApiName = 'Projects5'
        criteria = @(@{
            leftSemanticFieldApiName = 'project_id7'
            rightSemanticFieldApiName = 'project_id7'
        })
    },
    @{
        apiName = 'procurement_orders_distributor_id_to_distributors_distributor_id'
        label = 'procurement_orders.distributor_id -> distributors.distributor_id'
        leftSemanticDefinitionApiName = 'Procurement_Orders5'
        rightSemanticDefinitionApiName = 'Distributors5'
        criteria = @(@{
            leftSemanticFieldApiName = 'distributor_id6'
            rightSemanticFieldApiName = 'distributor_id6'
        })
    }
)

foreach ($relationship in $relationships) {
    $bodyPath = Join-Path $PSScriptRoot ("{0}.json" -f $relationship.apiName)
    $relationship | ConvertTo-Json -Depth 10 | Set-Content -LiteralPath $bodyPath -Encoding UTF8
    Write-Host ("POST {0}" -f $relationship.apiName)
    sf api request rest '/services/data/v66.0/ssot/semantic/models/Sunrun_Residential_Solar_Operations_Semantic_Model_20260420_2332/relationships' --target-org STORM_TABLEAU_NEXT --method POST --body ("@{0}" -f $bodyPath)
}
