function Write-OrgSetupHtmlReport {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Alias,
        [string]$Since = '',
        [switch]$Open
    )

    $state = Read-OrgSetupState -Alias $Alias

    # Warnings for this run only (deduplicated)
    $allWarnings = @()
    if ($state.PSObject.Properties.Name -contains 'warnings') {
        $allWarnings = @($state.warnings)
    }
    if ($Since) { $allWarnings = @($allWarnings | Where-Object { $_.timestamp -ge $Since }) }
    $seen = @{}
    $warnings = @($allWarnings | Where-Object {
        $k = "$($_.step)|$($_.feature)"
        if ($seen[$k]) { return $false }
        $seen[$k] = $true
        return $true
    })

    # Latest outcome per step (this run)
    $latestByStep = [ordered]@{}
    foreach ($entry in @($state.log)) {
        if ($Since -and $entry.timestamp -lt $Since) { continue }
        $latestByStep[$entry.step] = @{
            outcome   = $entry.outcome
            message   = $entry.message
            timestamp = $entry.timestamp
        }
    }

    # Human-readable step metadata (ordered by pipeline sequence)
    $stepMeta = [ordered]@{
        'a-enable-data-cloud'     = @{ Icon = '&#9729;';  Title = 'Data Cloud Enabled';            Desc = 'Enabled Salesforce Data Cloud and kicked off tenant provisioning.' }
        'b-enable-einstein'       = @{ Icon = '&#129302;'; Title = 'Einstein AI Enabled';           Desc = 'Enabled Einstein Generative AI, beta models, and prompt template editing.' }
        'c-j-data-cloud-ready'    = @{ Icon = '&#10003;';  Title = 'Data Cloud Provisioned';        Desc = 'Confirmed the Data Cloud tenant is fully live and ready for use.' }
        'd-deploy-permset'        = @{ Icon = '&#128273;'; Title = 'Permission Set Deployed';       Desc = 'Deployed the Access Analytics Agent permission set to the org.' }
        'e-deploy-psg'            = @{ Icon = '&#128272;'; Title = 'Permission Group Deployed';     Desc = 'Deployed the Tableau Next Admin PSG with all Tableau, Data Cloud, and Agentforce permissions.' }
        'e-assign-psg'            = @{ Icon = '&#128100;'; Title = 'Permissions Self-Assigned';     Desc = 'Assigned the Tableau Next Admin PSG to your Salesforce user.' }
        'f-i-tableau-next-enable' = @{ Icon = '&#128202;'; Title = 'Tableau Next + Agentforce On';  Desc = 'Enabled Tableau Next, Analytics, Agentforce, EinsteinCopilot, and all sub-toggles (28 flags flipped).' }
        'g-feature-editor'        = @{ Icon = '&#9881;';   Title = 'Feature Editor Flags';          Desc = 'Data Cloud Feature Editor has no public API. Manual follow-up required (see warnings below).' }
        'h-dark-mode'             = @{ Icon = '&#127769;'; Title = 'Dark Mode Enabled';             Desc = 'Enabled SLDS v2 and dark mode org-wide. Each user sets their own appearance under the avatar menu.' }
        'k-create-agent'          = @{ Icon = '&#129470;'; Title = 'Agentforce Agent Created';      Desc = 'Created and activated the Analytics and Visualization Agentforce agent.' }
        'l-grant-agent-access'    = @{ Icon = '&#128275;'; Title = 'Agent Access Granted';          Desc = 'Wired the Access Analytics Agent permission set to the Agentforce agent via SetupEntityAccess.' }
        'm-heroku-connector'      = @{ Icon = '&#128024;'; Title = 'Heroku Connector Created';      Desc = 'Created the Heroku PostgreSQL external data connector in Data Cloud.' }
        'n-reckless-analyst'      = @{ Icon = '&#129514;'; Title = 'Reckless Analyst Deployed';     Desc = 'Deployed and activated the Reckless Analyst Employee sidebar agent.' }
        'o-tableau-sites'         = @{ Icon = '&#128506;'; Title = 'Tableau Sites Registered';      Desc = 'Registered PACE and PACE-NEXUS Tableau Cloud sites via TableauHostMapping (Salesforce side).' }
        'p-pace-trust'            = @{ Icon = '&#128202;'; Title = 'PACE Tableau Trust Configured';  Desc = 'Registered this org as a trusted identity provider on PACE and PACE-NEXUS; org user added to both sites.' }
        'extra-connected-app'     = @{ Icon = '&#128268;'; Title = 'Connected App Deployed';        Desc = 'Deployed the Command Center Connected App for Data Cloud authentication.' }
    }

    # Stats
    $completedCount = @($latestByStep.Keys | Where-Object { $latestByStep[$_].outcome -in @('completed','noop') }).Count
    $failedCount    = @($latestByStep.Keys | Where-Object { $latestByStep[$_].outcome -eq 'failed' }).Count
    $warnCount      = $warnings.Count

    # Whether PACE trust has ever been completed for this org
    $paceTrustDone = @($state.completed) -contains 'p-pace-trust'

    # Overall status
    $heroTitle = if ($failedCount -gt 0) { 'BUILD 1 COMPLETE &#8212; REVIEW NEEDED' } else { 'BUILD 1 COMPLETE' }
    $heroEmoji = if ($failedCount -gt 0) { '&#9888;' } else { '&#127881;' }
    $heroSubtitle = "Org: $Alias"
    $now = Get-Date -Format 'dddd, MMMM d yyyy  &#183;  h:mm tt'

    # ── Build step cards ──
    $stepCardsHtml = ''
    $cardIndex = 0
    foreach ($stepId in $stepMeta.Keys) {
        if (-not $latestByStep.Contains($stepId)) { continue }
        $meta    = $stepMeta[$stepId]
        $entry   = $latestByStep[$stepId]
        $outcome = $entry.outcome

        $statusClass = switch ($outcome) {
            'completed' { 'success' }
            'noop'      { 'noop'    }
            'skipped'   { 'skipped' }
            'failed'    { 'failed'  }
            default     { 'skipped' }
        }
        $statusLabel = switch ($outcome) {
            'completed' { 'Done'            }
            'noop'      { 'Already set'     }
            'skipped'   { 'Skipped'          }
            'failed'    { 'Failed'          }
            default     { 'Skipped'         }
        }
        $checkGlyph = switch ($outcome) {
            'completed' { '&#10003;' }
            'noop'      { '&#10003;' }
            'skipped'   { '&#33;'    }
            'failed'    { '&#10007;' }
            default     { '?'        }
        }

        $delay = [math]::Round($cardIndex * 0.05, 2)
        $stepCardsHtml += "        <div class=`"step-card step-$statusClass`" style=`"animation-delay:${delay}s`">`n"
        $stepCardsHtml += "          <div class=`"step-check $statusClass`">$checkGlyph</div>`n"
        $stepCardsHtml += "          <div class=`"step-icon`">$($meta.Icon)</div>`n"
        $stepCardsHtml += "          <div class=`"step-body`">`n"
        $stepCardsHtml += "            <div class=`"step-title`">$($meta.Title)</div>`n"
        $stepCardsHtml += "            <div class=`"step-desc`">$($meta.Desc)</div>`n"
        $stepCardsHtml += "          </div>`n"
        $stepCardsHtml += "          <div class=`"step-badge $statusClass`">$statusLabel</div>`n"
        $stepCardsHtml += "        </div>`n"
        $cardIndex++
    }

    # ── Build warnings ──
    $warningsHtml = ''
    if ($warnings.Count -gt 0) {
        $warningsHtml = "      <div class=`"warnings-section`">`n"
        $warningsHtml += "        <h2 class=`"section-title warn-title`">&#9888; Manual Follow-ups Required</h2>`n"
        $warningsHtml += "        <div class=`"warnings-list`">`n"
        $wi = 0
        foreach ($w in $warnings) {
            $wDelay = [math]::Round($wi * 0.07, 2)
            $featureHtml = ''
            if ($w.feature) { $featureHtml = "              <span class=`"warn-feature`">$($w.feature)</span>`n" }
            $warningsHtml += "          <div class=`"warn-card`" style=`"animation-delay:${wDelay}s`">`n"
            $warningsHtml += "            <div class=`"warn-header`">`n"
            $warningsHtml += $featureHtml
            $warningsHtml += "              <span class=`"warn-step`">$($w.step)</span>`n"
            $warningsHtml += "            </div>`n"
            $warningsHtml += "            <div class=`"warn-msg`">$($w.message)</div>`n"
            $warningsHtml += "          </div>`n"
            $wi++
        }
        $warningsHtml += "        </div>`n"
        $warningsHtml += "      </div>`n"
    }

    # ── Stats color classes ──
    $warnClass  = if ($warnCount  -gt 0) { 'warn-text'  } else { 'success-text' }
    $errorClass = if ($failedCount -gt 0) { 'error-text' } else { 'success-text' }
    $stateFilePath = ($stateFilePath = Get-OrgSetupStatePath -Alias $Alias) -replace '\\','/'

    # ── Static HTML top (single-quote = no interpolation = safe for CSS/JS with $) ──
    $htmlTop = @'
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Org Setup Complete</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{background:#0b0d11;color:#e2e8f0;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',system-ui,sans-serif;min-height:100vh;overflow-x:hidden}
#cc{position:fixed;inset:0;pointer-events:none;z-index:999}

/* Hero */
.hero{background:linear-gradient(135deg,#032D60 0%,#0176D3 45%,#7B5EA7 100%);padding:64px 32px 88px;text-align:center;position:relative;overflow:hidden}
.hero::after{content:'';position:absolute;inset:0;background:radial-gradient(ellipse at 50% 100%,rgba(0,0,0,.45) 0%,transparent 70%)}
.hc{position:relative;z-index:1}
.he{font-size:72px;display:block;margin-bottom:16px;animation:pop .6s cubic-bezier(.34,1.56,.64,1) both}
.ht{font-size:clamp(28px,5vw,52px);font-weight:800;letter-spacing:-.02em;color:#fff;text-shadow:0 2px 20px rgba(0,0,0,.3);margin-bottom:8px;animation:slideUp .5s .1s ease both}
.ha{font-size:18px;color:rgba(255,255,255,.75);font-weight:500;margin-bottom:6px;animation:slideUp .5s .2s ease both}
.hts{font-size:13px;color:rgba(255,255,255,.45);animation:slideUp .5s .3s ease both}

/* Stats */
.stats{display:grid;grid-template-columns:repeat(3,1fr);gap:16px;max-width:820px;margin:-44px auto 48px;padding:0 24px;position:relative;z-index:2}
.sc{background:#161b27;border:1px solid #1e2633;border-radius:16px;padding:24px 20px;text-align:center;box-shadow:0 8px 32px rgba(0,0,0,.35);animation:fadeUp .4s ease both}
.sn{font-size:52px;font-weight:800;line-height:1;margin-bottom:6px}
.sl{font-size:12px;color:#6b7280;font-weight:600;text-transform:uppercase;letter-spacing:.06em}
.success-text{color:#34d399}.warn-text{color:#fbbf24}.error-text{color:#f87171}

/* Layout */
.wrap{max-width:860px;margin:0 auto;padding:0 24px 48px}
.section-title{font-size:12px;font-weight:700;text-transform:uppercase;letter-spacing:.1em;color:#4b5563;margin-bottom:14px;padding-bottom:8px;border-bottom:1px solid #1e2633}
.warn-title{color:#fbbf24;border-color:#451a03}

/* Step cards */
.steps{display:flex;flex-direction:column;gap:8px;margin-bottom:40px}
.step-card{display:flex;align-items:center;gap:14px;background:#161b27;border:1px solid #1e2633;border-radius:12px;padding:14px 18px;animation:fadeUp .3s ease both;transition:transform .15s,box-shadow .15s}
.step-card:hover{transform:translateY(-1px);box-shadow:0 6px 24px rgba(0,0,0,.35)}
.step-card.step-failed{border-color:#3f1a1a}
.step-card.step-skipped{opacity:.85}
.step-check{width:28px;height:28px;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:13px;font-weight:700;flex-shrink:0}
.step-check.success{background:#052e16;color:#34d399;border:1.5px solid #34d399}
.step-check.noop{background:#062316;color:#34d399;border:1.5px solid #1a4d30}
.step-check.skipped{background:#1c1209;color:#fbbf24;border:1.5px solid #fbbf24}
.step-check.failed{background:#2d0a0a;color:#f87171;border:1.5px solid #f87171}
.step-icon{font-size:20px;flex-shrink:0;width:26px;text-align:center}
.step-body{flex:1;min-width:0}
.step-title{font-size:14px;font-weight:600;color:#e2e8f0}
.step-desc{font-size:12px;color:#6b7280;margin-top:2px;line-height:1.45}
.step-badge{font-size:11px;font-weight:700;padding:3px 10px;border-radius:999px;flex-shrink:0;text-transform:uppercase;letter-spacing:.05em}
.step-badge.success{background:#052e16;color:#34d399}
.step-badge.noop{background:#0a2a1a;color:#6ee7b7}
.step-badge.skipped{background:#1c1209;color:#fbbf24}
.step-badge.failed{background:#2d0a0a;color:#f87171}

/* Warnings */
.warnings-section{margin-bottom:40px}
.warnings-list{display:flex;flex-direction:column;gap:10px}
.warn-card{background:#1a1208;border:1px solid #451a03;border-radius:12px;padding:16px 18px;animation:fadeUp .3s ease both}
.warn-header{display:flex;align-items:center;gap:8px;margin-bottom:8px;flex-wrap:wrap}
.warn-feature{font-size:12px;font-weight:700;color:#fbbf24;background:#1c1209;border:1px solid #451a03;padding:2px 8px;border-radius:999px}
.warn-step{font-size:11px;color:#6b7280;font-family:monospace}
.warn-msg{font-size:13px;color:#d1d5db;line-height:1.65}

/* PACE action banner */
.pace-banner{background:linear-gradient(135deg,#032D60 0%,#0176D3 100%);border-radius:16px;padding:24px 28px;margin-bottom:32px;animation:fadeUp .4s .1s ease both}
.pace-banner-title{font-size:16px;font-weight:700;color:#fff;margin-bottom:6px}
.pace-banner-desc{font-size:13px;color:rgba(255,255,255,.8);margin-bottom:18px;line-height:1.55}
.pace-btn-row{display:flex;gap:12px;flex-wrap:wrap}
.pace-btn{display:inline-flex;align-items:center;gap:8px;background:rgba(255,255,255,.15);border:1px solid rgba(255,255,255,.3);color:#fff;font-size:13px;font-weight:600;padding:9px 18px;border-radius:8px;text-decoration:none;transition:background .15s,border-color .15s}
.pace-btn:hover{background:rgba(255,255,255,.25);border-color:rgba(255,255,255,.5)}

/* Footer */
.footer{border-top:1px solid #1e2633;padding:24px;text-align:center;font-size:12px;color:#374151}
.footer code{font-family:monospace;color:#4b5563}

/* Animations */
@keyframes pop{from{transform:scale(.2);opacity:0}to{transform:scale(1);opacity:1}}
@keyframes slideUp{from{transform:translateY(20px);opacity:0}to{transform:translateY(0);opacity:1}}
@keyframes fadeUp{from{transform:translateY(10px);opacity:0}to{transform:translateY(0);opacity:1}}
</style>
</head>
<body>
<canvas id="cc"></canvas>
'@

    $htmlBottom = @'
<script>
(function(){
  var c=document.getElementById('cc'),x=c.getContext('2d');
  function resize(){c.width=window.innerWidth;c.height=window.innerHeight}
  resize();window.addEventListener('resize',resize);
  var cols=['#0176D3','#34d399','#fbbf24','#f87171','#7B5EA7','#fff','#60a5fa','#a78bfa','#fb7185'],
      ps=[];
  for(var i=0;i<140;i++){
    ps.push({
      x:Math.random()*c.width,y:Math.random()*c.height-c.height,
      w:Math.random()*10+5,h:Math.random()*5+3,
      col:cols[Math.floor(Math.random()*cols.length)],
      vx:(Math.random()-.5)*3,vy:Math.random()*3.5+1.5,
      a:Math.random()*Math.PI*2,va:(Math.random()-.5)*.15,op:1
    });
  }
  var t0=null,dur=5000;
  function frame(ts){
    if(!t0)t0=ts;
    var el=ts-t0;
    x.clearRect(0,0,c.width,c.height);
    ps.forEach(function(p){
      p.x+=p.vx;p.y+=p.vy;p.a+=p.va;
      p.op=Math.max(0,1-(el-2500)/2500);
      if(p.y>c.height){p.y=-20;p.x=Math.random()*c.width;}
      x.save();x.globalAlpha=p.op;
      x.translate(p.x+p.w/2,p.y+p.h/2);
      x.rotate(p.a);x.fillStyle=p.col;
      x.fillRect(-p.w/2,-p.h/2,p.w,p.h);
      x.restore();
    });
    if(el<dur)requestAnimationFrame(frame);
    else x.clearRect(0,0,c.width,c.height);
  }
  requestAnimationFrame(frame);
})();
</script>
</body>
</html>
'@

    # ── Assemble full HTML ──
    $html = $htmlTop
    $html += "<div class=`"hero`">`n"
    $html += "  <div class=`"hc`">`n"
    $html += "    <span class=`"he`">$heroEmoji</span>`n"
    $html += "    <div class=`"ht`">$heroTitle</div>`n"
    $html += "    <div class=`"ha`">$heroSubtitle</div>`n"
    $html += "    <div class=`"hts`">$now</div>`n"
    $html += "  </div>`n"
    $html += "</div>`n"
    $html += "<div class=`"stats`">`n"
    $html += "  <div class=`"sc`"><div class=`"sn success-text`">$completedCount</div><div class=`"sl`">Steps Complete</div></div>`n"
    $html += "  <div class=`"sc`"><div class=`"sn $warnClass`">$warnCount</div><div class=`"sl`">Manual Follow-ups</div></div>`n"
    $html += "  <div class=`"sc`"><div class=`"sn $errorClass`">$failedCount</div><div class=`"sl`">Failures</div></div>`n"
    $html += "</div>`n"
    $html += "<div class=`"wrap`">`n"

    # PACE / PACE-NEXUS action banner -- only shown when trust has NOT been configured
    if (-not $paceTrustDone) {
        $html += "  <div class=`"pace-banner`">`n"
        $html += "    <div class=`"pace-banner-title`">&#9889; Action Required: Enable Tableau Embedding</div>`n"
        $html += "    <div class=`"pace-banner-desc`">Tableau Next dashboards won&#39;t load until this Salesforce org is registered as a trusted identity provider on both PACE sites. Rerun setup and answer <strong>Y</strong> to the PACE embedding prompt, or register manually via the buttons below.</div>`n"
        $html += "    <div class=`"pace-btn-row`">`n"
        $html += "      <a class=`"pace-btn`" href=`"https://prod-uswest-c.online.tableau.com/#/site/pace/connectedApplications`" target=`"_blank`">&#128202; Open PACE Connected Apps</a>`n"
        $html += "      <a class=`"pace-btn`" href=`"https://prod-uswest-c.online.tableau.com/#/site/pace-nexus/connectedApplications`" target=`"_blank`">&#128202; Open PACE-NEXUS Connected Apps</a>`n"
        $html += "    </div>`n"
        $html += "  </div>`n"
    }

    $html += "  <h2 class=`"section-title`">Setup Steps</h2>`n"
    $html += "  <div class=`"steps`">`n"
    $html += $stepCardsHtml
    $html += "  </div>`n"
    $html += $warningsHtml
    $html += "  <div class=`"footer`">State file: <code>$stateFilePath</code><br>Analytics SE Command Center</div>`n"
    $html += "</div>`n"
    $html += $htmlBottom

    # ── Save and open ──
    $reportPath = Join-Path (Resolve-CommandCenterPath 'notes/org-setup-state') "$Alias-report.html"
    [System.IO.File]::WriteAllText($reportPath, $html, [System.Text.Encoding]::UTF8)
    Write-Host "  Report saved: $reportPath" -ForegroundColor Cyan

    if ($Open) { Start-Process $reportPath }

    return $reportPath
}
