"""
Generate org-setup-guide.pdf with visual layout using reportlab.
Run from anywhere: python scripts/generate-org-setup-guide-pdf.py
Output: playbooks/org-setup-guide.pdf
"""

import os, sys
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, KeepTogether, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# ── paths ──────────────────────────────────────────────────────────────────────
SCRIPT_DIR  = os.path.dirname(os.path.abspath(__file__))
REPO_ROOT   = os.path.dirname(SCRIPT_DIR)
OUTPUT_PATH = os.path.join(REPO_ROOT, 'playbooks', 'org-setup-guide.pdf')

# A4 content width with 25mm margins on each side
PAGE_W = 160*mm

# ── colour palette ─────────────────────────────────────────────────────────────
NAVY      = colors.HexColor('#0A1628')
BLUE      = colors.HexColor('#0070D2')
LIGHT_BLUE= colors.HexColor('#E8F4FD')
TEAL      = colors.HexColor('#00A1B0')
ORANGE    = colors.HexColor('#FF5722')
AMBER     = colors.HexColor('#FFA000')
GREEN     = colors.HexColor('#2E7D32')
GREY_BG   = colors.HexColor('#F4F6F9')
GREY_LINE = colors.HexColor('#DDE1E8')
WHITE     = colors.white
TEXT      = colors.HexColor('#1A1A2E')
MUTED     = colors.HexColor('#555770')

# ── styles ─────────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

TITLE = S('DocTitle',
    fontName='Helvetica-Bold', fontSize=28, textColor=WHITE,
    spaceAfter=6, leading=34)
SUBTITLE = S('DocSubtitle',
    fontName='Helvetica', fontSize=13, textColor=colors.HexColor('#A8C4E0'),
    spaceAfter=0, leading=18)
H1 = S('H1',
    fontName='Helvetica-Bold', fontSize=16, textColor=NAVY,
    spaceBefore=18, spaceAfter=6, leading=20)
H2 = S('H2',
    fontName='Helvetica-Bold', fontSize=12, textColor=BLUE,
    spaceBefore=12, spaceAfter=4, leading=16)
H3 = S('H3',
    fontName='Helvetica-Bold', fontSize=10, textColor=NAVY,
    spaceBefore=8, spaceAfter=2, leading=14)
BODY = S('Body',
    fontName='Helvetica', fontSize=9.5, textColor=TEXT,
    spaceBefore=2, spaceAfter=4, leading=14)
BODY_MUTED = S('BodyMuted',
    fontName='Helvetica', fontSize=9, textColor=MUTED,
    spaceBefore=1, spaceAfter=3, leading=13)
MONO = S('Mono',
    fontName='Courier', fontSize=8.5, textColor=colors.HexColor('#2D3561'),
    spaceBefore=0, spaceAfter=0, leading=12,
    backColor=colors.HexColor('#EEF2FF'),
    leftIndent=4, rightIndent=4, borderPad=2)
BULLET = S('Bullet',
    fontName='Helvetica', fontSize=9.5, textColor=TEXT,
    spaceBefore=1, spaceAfter=2, leading=14,
    leftIndent=14, bulletIndent=4)
WARN = S('Warn',
    fontName='Helvetica', fontSize=9, textColor=colors.HexColor('#7B3900'),
    leading=13, leftIndent=4)
NOTE = S('Note',
    fontName='Helvetica-Oblique', fontSize=9, textColor=MUTED,
    leading=13, leftIndent=4)
TABLE_HDR = S('TableHdr',
    fontName='Helvetica-Bold', fontSize=9, textColor=WHITE, leading=12)
TABLE_CELL = S('TableCell',
    fontName='Helvetica', fontSize=8.5, textColor=TEXT, leading=12)
TABLE_CELL_MONO = S('TableCellMono',
    fontName='Courier', fontSize=8, textColor=colors.HexColor('#2D3561'), leading=12)

def p(text, style=BODY): return Paragraph(text, style)
def sp(h=4):             return Spacer(1, h)
def hr():                return HRFlowable(width='100%', thickness=0.5,
                                           color=GREY_LINE, spaceAfter=4, spaceBefore=4)

def section_box(title, content_rows, accent=BLUE):
    """A titled content box with left accent bar."""
    title_para = Paragraph(f'<b>{title}</b>',
                           ParagraphStyle('SBT', fontName='Helvetica-Bold',
                                          fontSize=11, textColor=accent, leading=14))
    rows = [[title_para]] + [[r] for r in content_rows]
    t = Table(rows, colWidths=[PAGE_W],
              style=[
                  ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#F0F6FF')),
                  ('BACKGROUND', (0,1), (-1,-1), GREY_BG),
                  ('LINEBEFORE', (0,0), (0,-1), 3, accent),
                  ('TOPPADDING', (0,0), (-1,-1), 5),
                  ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                  ('LEFTPADDING', (0,0), (-1,-1), 10),
                  ('RIGHTPADDING', (0,0), (-1,-1), 8),
              ])
    return t

def step_row(label, script, mechanism, failure, optional=False):
    opt_marker = ' ★' if optional else ''
    cells = [
        Paragraph(f'<b>{label}</b>{opt_marker}',
                  ParagraphStyle('SR1', fontName='Helvetica-Bold', fontSize=8.5,
                                 textColor=BLUE if not optional else TEAL, leading=11)),
        Paragraph(script, TABLE_CELL_MONO),
        Paragraph(mechanism, TABLE_CELL),
        Paragraph(failure, ParagraphStyle('SRF', fontName='Helvetica', fontSize=8,
                                          textColor=GREEN if failure=='Warning' else
                                          (ORANGE if failure=='Hard' else MUTED),
                                          leading=11))
    ]
    return cells

def warning_box(text):
    t = Table([[Paragraph('⚠  ' + text, WARN)]],
              colWidths=[PAGE_W],
              style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFF8E1')),
                     ('LINEBEFORE', (0,0), (0,-1), 3, AMBER),
                     ('TOPPADDING', (0,0), (-1,-1), 6),
                     ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                     ('LEFTPADDING', (0,0), (-1,-1), 8),
                     ('RIGHTPADDING', (0,0), (-1,-1), 8)])
    return t

def note_box(text):
    t = Table([[Paragraph('ℹ  ' + text, NOTE)]],
              colWidths=[PAGE_W],
              style=[('BACKGROUND', (0,0), (-1,-1), LIGHT_BLUE),
                     ('LINEBEFORE', (0,0), (0,-1), 3, BLUE),
                     ('TOPPADDING', (0,0), (-1,-1), 6),
                     ('BOTTOMPADDING', (0,0), (-1,-1), 6),
                     ('LEFTPADDING', (0,0), (-1,-1), 8),
                     ('RIGHTPADDING', (0,0), (-1,-1), 8)])
    return t

def cmd_box(cmd):
    t = Table([[Paragraph(cmd,
                          ParagraphStyle('CMD', fontName='Courier', fontSize=7.5,
                                         textColor=colors.HexColor('#E8F0FE'),
                                         leading=11))]],
              colWidths=[PAGE_W],
              style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#1A237E')),
                     ('TOPPADDING', (0,0), (-1,-1), 7),
                     ('BOTTOMPADDING', (0,0), (-1,-1), 7),
                     ('LEFTPADDING', (0,0), (-1,-1), 10),
                     ('RIGHTPADDING', (0,0), (-1,-1), 10)])
    return t

# ── pipeline diagram ───────────────────────────────────────────────────────────
def pipeline_diagram():
    col_w = 69*mm

    def phase_col(title, steps, bg, accent):
        rows = [[Paragraph(f'<b>{title}</b>',
                           ParagraphStyle('PC', fontName='Helvetica-Bold',
                                          fontSize=11, textColor=WHITE, leading=14))]]
        for s in steps:
            rows.append([Paragraph(s, ParagraphStyle('PS', fontName='Helvetica',
                                                     fontSize=8.5, textColor=TEXT,
                                                     leading=13))])
        t = Table(rows, colWidths=[col_w],
                  style=[
                      ('BACKGROUND', (0,0), (-1,0), accent),
                      ('BACKGROUND', (0,1), (-1,-1), bg),
                      ('LINEBEFORE', (0,0), (0,-1), 3, accent),
                      ('TOPPADDING', (0,0), (-1,-1), 5),
                      ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                      ('LEFTPADDING', (0,0), (-1,-1), 8),
                      ('RIGHTPADDING', (0,0), (-1,-1), 8),
                  ])
        return t

    kickoff_steps = [
        '[a]  Enable Data Cloud',
        '[b]  Enable Einstein',
        '[d]  Deploy permset + PSG',
        '[e]  Self-assign PSG',
        '★  Deploy CommandCenterAuth  (opt)',
    ]
    resume_steps = [
        '[c]  Poll: Data Cloud ready',
        '[f]  Enable Tableau Next + Agentforce toggles',
        '[g]  Feature Editor flags  (manual)',
        '[h]  Enable dark mode',
        '[k]  Create Analytics & Viz agent',
        '[l]  Grant agent access',
        '★  Heroku connector  (opt)',
        '★  Reckless Analyst agent  (opt)',
        '[o]  Register Tableau Cloud sites',
    ]

    wait_w = PAGE_W - 2*col_w
    wait_cell = Table(
        [[Paragraph('<b>~30 min</b>',
                    ParagraphStyle('WC', fontName='Helvetica-Bold', fontSize=9,
                                   textColor=AMBER, leading=12,
                                   alignment=TA_CENTER))],
         [Paragraph('Data Cloud\nprovisioning',
                    ParagraphStyle('WC2', fontName='Helvetica', fontSize=7.5,
                                   textColor=MUTED, leading=11,
                                   alignment=TA_CENTER))]],
        colWidths=[wait_w],
        style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFDE7')),
               ('LINEBEFORE', (0,0), (0,-1), 2, AMBER),
               ('LINEAFTER', (0,0), (0,-1), 2, AMBER),
               ('TOPPADDING', (0,0), (-1,-1), 4),
               ('BOTTOMPADDING', (0,0), (-1,-1), 4),
               ('LEFTPADDING', (0,0), (-1,-1), 3),
               ('RIGHTPADDING', (0,0), (-1,-1), 3),
               ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]
    )

    outer = Table(
        [[phase_col('PHASE 1 — KICKOFF', kickoff_steps,
                    colors.HexColor('#F0F6FF'), BLUE),
          wait_cell,
          phase_col('PHASE 2 — RESUME', resume_steps,
                    colors.HexColor('#F0FFF4'), TEAL)]],
        colWidths=[col_w, wait_w, col_w],
        style=[('VALIGN', (0,0), (-1,-1), 'TOP'),
               ('LEFTPADDING', (0,0), (-1,-1), 0),
               ('RIGHTPADDING', (0,0), (-1,-1), 0),
               ('TOPPADDING', (0,0), (-1,-1), 0),
               ('BOTTOMPADDING', (0,0), (-1,-1), 0)])
    return outer

# ── feature flags panel ────────────────────────────────────────────────────────
def feature_flags_table():
    c1, c2, c3, c4 = 35*mm, 38*mm, 18*mm, PAGE_W - 35*mm - 38*mm - 18*mm
    rows = [
        [Paragraph('<b>Flag</b>', TABLE_HDR),
         Paragraph('<b>Parameter</b>', TABLE_HDR),
         Paragraph('<b>Phase</b>', TABLE_HDR),
         Paragraph('<b>What it installs</b>', TABLE_HDR)],
        [Paragraph('CommandCenterAuth', TABLE_CELL),
         Paragraph('-WithConnectedApp', TABLE_CELL_MONO),
         Paragraph('Kickoff', TABLE_CELL),
         Paragraph('OAuth external client app for Data Cloud CSV upload auth. '
                   'Required only if this org will be a Data Cloud publish target.', TABLE_CELL)],
        [Paragraph('Heroku PostgreSQL', TABLE_CELL),
         Paragraph('-WithHeroku', TABLE_CELL_MONO),
         Paragraph('Resume', TABLE_CELL),
         Paragraph('External data connector to the PACE curriculum shared PostgreSQL. '
                   'Required only for orgs following the PACE lab guide.', TABLE_CELL)],
        [Paragraph('Reckless Analyst Agent', TABLE_CELL),
         Paragraph('-WithRecklessAgent', TABLE_CELL_MONO),
         Paragraph('Resume', TABLE_CELL),
         Paragraph('Custom Employee Agent visible in Concierge sidebar dropdown. '
                   'Deploys agent + permset + access grant + self-assignment. '
                   'Demo orgs only.', TABLE_CELL)],
    ]
    t = Table(rows, colWidths=[c1, c2, c3, c4],
              style=[
                  ('BACKGROUND', (0,0), (-1,0), NAVY),
                  ('BACKGROUND', (0,1), (-1,-1), WHITE),
                  ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, GREY_BG]),
                  ('GRID', (0,0), (-1,-1), 0.4, GREY_LINE),
                  ('TOPPADDING', (0,0), (-1,-1), 5),
                  ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                  ('LEFTPADDING', (0,0), (-1,-1), 6),
                  ('RIGHTPADDING', (0,0), (-1,-1), 6),
                  ('VALIGN', (0,0), (-1,-1), 'TOP'),
              ])
    return t

# ── step reference table ───────────────────────────────────────────────────────
def step_reference_table():
    c1, c2, c3, c4 = 20*mm, 50*mm, 65*mm, PAGE_W - 20*mm - 50*mm - 65*mm
    hdr = [Paragraph(h, TABLE_HDR) for h in
           ['Guide step', 'Script', 'Mechanism', 'On failure']]
    rows = [hdr,
        step_row('[a]', '01-enable-data-cloud.ps1',
                 'Metadata deploy Settings:CustomerDataPlatform', 'Hard'),
        step_row('[b]', '02-enable-einstein.ps1',
                 'Metadata deploy Settings:EinsteinGpt (3 flags)', 'Hard'),
        step_row('[d+e]', '03-deploy-permsets-and-psg.ps1',
                 'Metadata deploy PermissionSet + PermissionSetGroup', 'Hard'),
        step_row('[e]', '04-assign-psg-to-self.ps1',
                 'Polls PSG status, inserts PermissionSetAssignment', 'Hard'),
        step_row('[c+j]', '05-wait-for-data-cloud.ps1',
                 'Polls GET /ssot/data-connections (60 min timeout)', 'Hard (timeout)'),
        step_row('[f+i]', '06-enable-tableau-next.ps1',
                 'Retrieve+flip enable* fields, per-record Metadata deploy', 'Warning'),
        step_row('[g]', '07-enable-feature-manager-flags.ps1',
                 'No API — emits 5 manual warnings', 'Warning only'),
        step_row('[h]', '12-enable-dark-mode.ps1',
                 'Metadata deploy Settings:UserInterface', 'Warning'),
        step_row('[k]', '08-create-analytics-agent.ps1',
                 'sf agent create + sf agent activate', 'Warning'),
        step_row('[l]', '09-grant-agent-access.ps1',
                 'SetupEntityAccess insert via REST', 'Warning'),
        step_row('[m] ★', '10-create-heroku-connector.ps1',
                 'POST /ssot/external-data-connectors', 'Warning', optional=True),
        step_row('[extra] ★', '11-deploy-connected-app.ps1',
                 'Delegates to setup-command-center-connected-app.ps1', 'Hard', optional=True),
        step_row('[n] ★', '13-deploy-reckless-analyst-agent.ps1',
                 'sf agent publish authoring-bundle + permset + SetupEntityAccess', 'Warning', optional=True),
        step_row('[o]', '14-register-tableau-sites.ps1',
                 'TableauHostMapping REST inserts (Salesforce side only). Tableau-side Direct Trust setup is manual — always emits warning.', 'Warning'),
    ]
    t = Table(rows, colWidths=[c1, c2, c3, c4],
              style=[
                  ('BACKGROUND', (0,0), (-1,0), NAVY),
                  ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, GREY_BG]),
                  ('GRID', (0,0), (-1,-1), 0.4, GREY_LINE),
                  ('TOPPADDING', (0,0), (-1,-1), 4),
                  ('BOTTOMPADDING', (0,0), (-1,-1), 4),
                  ('LEFTPADDING', (0,0), (-1,-1), 5),
                  ('RIGHTPADDING', (0,0), (-1,-1), 5),
                  ('VALIGN', (0,0), (-1,-1), 'TOP'),
              ])
    return t

# ── manual follow-ups table ────────────────────────────────────────────────────
def manual_steps_table():
    c1 = 80*mm
    c2 = PAGE_W - c1
    hdr = [Paragraph(h, TABLE_HDR) for h in ['What', 'Where / Instructions']]
    rows = [hdr,
        [Paragraph('Feature Editor — Semantic Authoring AI', TABLE_CELL),
         Paragraph('Data Cloud Setup → Feature Editor / Feature Manager', TABLE_CELL)],
        [Paragraph('Feature Editor — Connectors (Beta)', TABLE_CELL),
         Paragraph('Data Cloud Setup → Feature Editor / Feature Manager', TABLE_CELL)],
        [Paragraph('Feature Editor — Accelerated Data Ingest', TABLE_CELL),
         Paragraph('Data Cloud Setup → Feature Editor / Feature Manager', TABLE_CELL)],
        [Paragraph('Feature Editor — Code Extension', TABLE_CELL),
         Paragraph('Data Cloud Setup → Feature Editor / Feature Manager', TABLE_CELL)],
        [Paragraph('Feature Editor — Content Tagging', TABLE_CELL),
         Paragraph('Data Cloud Setup → Feature Editor / Feature Manager', TABLE_CELL)],
        [Paragraph('Per-user dark mode', TABLE_CELL),
         Paragraph('Profile avatar → Appearance → Dark', TABLE_CELL)],
        [Paragraph('CommandCenterAuth final auth wiring', TABLE_CELL),
         Paragraph('Follow playbooks/set-up-command-center-connected-app.md', TABLE_CELL)],
        [Paragraph('Tableau Cloud Connected App trust — PACE site', TABLE_CELL),
         Paragraph('In Tableau Cloud: update the PACE site Connected App to trust this '
                   "Salesforce org's EntityId (Direct Trust). Requires Tableau admin access.", TABLE_CELL)],
        [Paragraph('Tableau Cloud Connected App trust — PACE-NEXUS site', TABLE_CELL),
         Paragraph('Same as above for the PACE-NEXUS site. One registration per org, per site.', TABLE_CELL)],
    ]
    t = Table(rows, colWidths=[c1, c2],
              style=[
                  ('BACKGROUND', (0,0), (-1,0), NAVY),
                  ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, GREY_BG]),
                  ('GRID', (0,0), (-1,-1), 0.4, GREY_LINE),
                  ('TOPPADDING', (0,0), (-1,-1), 5),
                  ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                  ('LEFTPADDING', (0,0), (-1,-1), 6),
                  ('RIGHTPADDING', (0,0), (-1,-1), 6),
                  ('VALIGN', (0,0), (-1,-1), 'TOP'),
              ])
    return t

# ── cover page ─────────────────────────────────────────────────────────────────
def cover_page():
    elems = []

    # Full-width header band — single column, title and subtitle stacked
    header = Table(
        [[Paragraph('Org Setup Automation', TITLE)],
         [Paragraph('Tableau Next + Data Cloud + Agentforce — Complete Human Guide', SUBTITLE)]],
        colWidths=[PAGE_W],
        style=[('BACKGROUND', (0,0), (-1,-1), NAVY),
               ('TOPPADDING', (0,0), (0,0), 22),
               ('BOTTOMPADDING', (0,-1), (-1,-1), 22),
               ('TOPPADDING', (0,1), (-1,-1), 0),
               ('BOTTOMPADDING', (0,0), (-1,0), 2),
               ('LEFTPADDING', (0,0), (-1,-1), 14),
               ('RIGHTPADDING', (0,0), (-1,-1), 14)])
    elems.append(header)
    elems.append(sp(14))

    elems.append(p('scripts/salesforce/org-setup/', MONO))
    elems.append(sp(6))
    elems.append(p(
        'This guide covers every action the Org Setup automation takes '
        'against a fresh Salesforce org — what each script does, why it does it, '
        'what happens when it fails, and which parts are optional.',
        BODY))
    elems.append(sp(10))

    # Quick stats row
    stat_style = ParagraphStyle('Stat', fontName='Helvetica-Bold',
                                fontSize=18, textColor=BLUE, leading=22, alignment=TA_CENTER)
    stats = Table(
        [[Paragraph('<b>14</b>\nScripts', stat_style),
          Paragraph('<b>2</b>\nPhases',
                    ParagraphStyle('Stat2', fontName='Helvetica-Bold',
                                   fontSize=18, textColor=TEAL, leading=22, alignment=TA_CENTER)),
          Paragraph('<b>3</b>\nOptional\nfeature flags',
                    ParagraphStyle('Stat3', fontName='Helvetica-Bold',
                                   fontSize=18, textColor=ORANGE, leading=22, alignment=TA_CENTER)),
          Paragraph('<b>~35 min</b>\nTotal runtime',
                    ParagraphStyle('Stat4', fontName='Helvetica-Bold',
                                   fontSize=14, textColor=NAVY, leading=18, alignment=TA_CENTER))]],
        colWidths=[PAGE_W/4, PAGE_W/4, PAGE_W/4, PAGE_W/4],
        style=[('BACKGROUND', (0,0), (-1,-1), GREY_BG),
               ('BOX', (0,0), (-1,-1), 0.5, GREY_LINE),
               ('INNERGRID', (0,0), (-1,-1), 0.5, GREY_LINE),
               ('TOPPADDING', (0,0), (-1,-1), 10),
               ('BOTTOMPADDING', (0,0), (-1,-1), 10),
               ('VALIGN', (0,0), (-1,-1), 'MIDDLE')])
    elems.append(stats)
    elems.append(sp(14))
    elems.append(hr())
    return elems

# ── document assembly ──────────────────────────────────────────────────────────
def build():
    doc = SimpleDocTemplate(
        OUTPUT_PATH,
        pagesize=A4,
        leftMargin=25*mm, rightMargin=25*mm,
        topMargin=20*mm, bottomMargin=20*mm,
        title='Org Setup Automation — Complete Human Guide',
        author='AnalyticsSECommandCenter'
    )

    story = []

    # ── Cover ──────────────────────────────────────────────────────────────────
    story += cover_page()

    # ── Section 1: Pipeline overview ───────────────────────────────────────────
    story.append(p('Pipeline Overview', H1))
    story.append(p(
        'The automation runs in two phases separated by a ~30 minute wait for '
        'Data Cloud provisioning. Phase 1 (Kickoff) starts the slow async work '
        'immediately. Phase 2 (Resume) finishes everything once provisioning completes.',
        BODY))
    story.append(sp(8))
    story.append(pipeline_diagram())
    story.append(sp(6))
    story.append(p('★ = optional feature flag', BODY_MUTED))
    story.append(sp(10))
    story.append(hr())

    # ── Section 2: Optional feature flags ─────────────────────────────────────
    story.append(p('Optional Feature Flags', H1))
    story.append(p(
        'Three features are off by default. Pass the corresponding flag to the '
        'orchestrator script to include them in the run.',
        BODY))
    story.append(sp(8))
    story.append(feature_flags_table())
    story.append(sp(10))
    story.append(hr())

    # ── Section 3: Prerequisites ───────────────────────────────────────────────
    story.append(p('Prerequisites', H1))
    prereqs = [
        '<b>PowerShell</b> — 5.1+ on Windows, <font name="Courier">pwsh</font> on macOS/Linux. '
        'If Salesforce CLI is missing, the scripts will prompt to auto-install via winget (Windows) or brew (macOS).',
        '<b>Salesforce CLI (sf)</b> — authenticated against the target org.',
        '<b>Org registered</b> — the target org must be in '
        '<font name="Courier">notes/registries/salesforce-orgs.json</font>.',
        '<b>Repo metadata present</b> — '
        '<font name="Courier">salesforce/force-app/main/default/</font> must contain '
        '<font name="Courier">Access_Analytics_Agent</font> and '
        '<font name="Courier">Tableau_Next_Admin_PSG</font> (both ship in this repo).',
    ]
    for pr in prereqs:
        story.append(p('•  ' + pr, BULLET))
    story.append(sp(10))
    story.append(hr())

    # ── Section 4: Usage ───────────────────────────────────────────────────────
    story.append(p('Usage', H1))
    story.append(p('Phase 1 — Kickoff', H2))
    story.append(cmd_box(
        'powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-kickoff.ps1 -Alias MFG-Nexus\n\n'
        '# Also deploy CommandCenterAuth connected app:\n'
        'powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-kickoff.ps1 -Alias MFG-Nexus -WithConnectedApp'))
    story.append(sp(8))
    story.append(p('(Wait ~30 min — or monitor in a separate terminal)', BODY_MUTED))
    story.append(sp(4))
    story.append(cmd_box(
        'powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/05-wait-for-data-cloud.ps1 -Alias MFG-Nexus'))
    story.append(sp(8))
    story.append(p('Phase 2 — Resume', H2))
    story.append(cmd_box(
        '# Standard\n'
        'powershell -ExecutionPolicy Bypass -File scripts/salesforce/org-setup/run-resume.ps1 -Alias MFG-Nexus\n\n'
        '# Skip Data Cloud poll (if already confirmed live)\n'
        'run-resume.ps1 -Alias MFG-Nexus -NoWait\n\n'
        '# All optional flags\n'
        'run-resume.ps1 -Alias MFG-Nexus -WithHeroku -WithRecklessAgent'))
    story.append(sp(10))
    story.append(hr())

    # ── Section 5: Phase 1 detail ──────────────────────────────────────────────
    story.append(PageBreak())
    story.append(p('Phase 1 — Kickoff: Step by Step', H1))

    steps_p1 = [
        ('[a] Enable Data Cloud', '01-enable-data-cloud.ps1', BLUE,
         'Deploys <font name="Courier">Settings:CustomerDataPlatform</font> with '
         '<font name="Courier">enableCustomerDataPlatform=true</font> via Metadata API. '
         'The Tooling API PATCH on this settings object returns a 500 — Metadata deploy '
         'is the only supported headless path.',
         'Kicks off ~30 min async tenant provisioning. The script returns immediately; '
         'nothing downstream works until provisioning finishes.',
         'Queries <font name="Courier">CustomerDataPlatformSettings.IsCustomerDataPlatformEnabled</font> '
         'first. If already true, logs noop and exits.',
         None),
        ('[b] Enable Einstein', '02-enable-einstein.ps1', BLUE,
         'Deploys <font name="Courier">Settings:EinsteinGpt</font> with three flags set to true: '
         '<font name="Courier">enableEinsteinGptPlatform</font> (master toggle), '
         '<font name="Courier">enableAIModelBeta</font> (beta models), '
         '<font name="Courier">enableEinsteinGptAllowUnsafePTInputChanges</font> (prompt template customisation).',
         'Einstein must be on before Agentforce agents can be created in step k.',
         'Deploy is a server-side no-op if all three flags are already true.',
         None),
        ('[d+e] Deploy Permission Set and PSG', '03-deploy-permsets-and-psg.ps1', BLUE,
         'Deploys two metadata components from the repo: '
         '<b>Access_Analytics_Agent</b> (PermissionSet) — grants access to run the Analytics and Visualization agent; '
         '<b>Tableau_Next_Admin_PSG</b> (PermissionSetGroup) — bundles 8 standard permsets: '
         'CopilotSalesforceUser, CopilotSalesforceAdmin, CDPAdmin, TableauEinsteinAdmin, '
         'TableauUser, TableauEinsteinAnalyst, TableauSelfServiceAnalyst, SlackElevateUser.',
         'The 8 standard permsets must already exist in the target org — they ship with STORM pre-enablement.',
         None,
         None),
        ('[e] Self-Assign PSG', '04-assign-psg-to-self.ps1', BLUE,
         'Assigns <font name="Courier">Tableau_Next_Admin_PSG</font> to the currently authenticated user. '
         'Permission Set Groups are recalculated asynchronously after deploy, so the script polls '
         'until <font name="Courier">Status = Updated</font> (up to 5 min) before inserting the '
         '<font name="Courier">PermissionSetAssignment</font> record.',
         None,
         'Checks for an existing assignment before inserting.',
         None),
    ]

    for (title, script, accent, what, why, idempotent, warn) in steps_p1:
        content = [p(f'<font name="Courier" color="#555770">{script}</font>', BODY_MUTED),
                   sp(3),
                   p(what, BODY)]
        if why:
            content += [sp(3), p(f'<b>Why:</b> {why}', BODY)]
        if idempotent:
            content += [sp(3), p(f'<b>Idempotent:</b> {idempotent}', BODY)]
        if warn:
            content += [sp(4), warning_box(warn)]
        story.append(KeepTogether([section_box(title, content, accent), sp(8)]))

    # Optional: Connected App
    content = [
        p('<font name="Courier" color="#555770">11-deploy-connected-app.ps1</font> — flag: <font name="Courier">-WithConnectedApp</font> on run-kickoff.ps1', BODY_MUTED),
        sp(3),
        p('Deploys the <font name="Courier">CommandCenterAuth</font> external client app — the OAuth '
          'credential store used by Command Center to authenticate Data Cloud CSV upload sessions.', BODY),
        sp(3),
        p('<b>Only required</b> if this org will be used as a Data Cloud publish target.', BODY),
        sp(4),
        note_box('After deploy, follow playbooks/set-up-command-center-connected-app.md to complete '
                 'the auth wiring — the DataCloudAlias and LaunchLogin steps cannot be automated.'),
    ]
    story.append(KeepTogether([section_box('★ Deploy CommandCenterAuth (Optional)', content, TEAL), sp(8)]))
    story.append(sp(10))
    story.append(hr())

    # ── Section 6: The wait ────────────────────────────────────────────────────
    wait_block = Table(
        [[Paragraph('~ 30 minute wait', ParagraphStyle('WH', fontName='Helvetica-Bold',
                                                        fontSize=14, textColor=AMBER, leading=18)),
          Paragraph(
              'Data Cloud provisioning runs asynchronously on Salesforce\'s backend. '
              'Nothing in Phase 2 will work until it completes. You can walk away, '
              'or run <font name="Courier">05-wait-for-data-cloud.ps1</font> in a separate '
              'terminal to monitor readiness. Pass <font name="Courier">-NoWait</font> to '
              '<font name="Courier">run-resume.ps1</font> if you have already confirmed it\'s live.',
              BODY)]],
        colWidths=[40*mm, PAGE_W - 40*mm],
        style=[('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#FFFDE7')),
               ('LINEBEFORE', (0,0), (0,-1), 4, AMBER),
               ('TOPPADDING', (0,0), (-1,-1), 10),
               ('BOTTOMPADDING', (0,0), (-1,-1), 10),
               ('LEFTPADDING', (0,0), (-1,-1), 10),
               ('RIGHTPADDING', (0,0), (-1,-1), 10),
               ('VALIGN', (0,0), (-1,-1), 'MIDDLE')])
    story.append(wait_block)
    story.append(sp(10))
    story.append(hr())

    # ── Section 7: Phase 2 detail ──────────────────────────────────────────────
    story.append(PageBreak())
    story.append(p('Phase 2 — Resume: Step by Step', H1))

    story.append(p('[c] Poll for Data Cloud Readiness', H2))
    story.append(p('Script: <font name="Courier">05-wait-for-data-cloud.ps1</font>', BODY_MUTED))
    story.append(p(
        'Polls <font name="Courier">GET /services/data/v60.0/ssot/data-connections</font> at '
        '60-second intervals until the endpoint returns a success response. This confirms the '
        'Data Cloud tenant is fully provisioned and the <font name="Courier">MktDataConnection</font> '
        'sObject is available. Times out after 60 minutes. If it times out, wait longer and re-run resume.',
        BODY))
    story.append(sp(8))

    story.append(p('[f+i] Enable Tableau Next and Agentforce Toggles', H2))
    story.append(p('Script: <font name="Courier">06-enable-tableau-next.ps1</font>', BODY_MUTED))
    story.append(p(
        'The most complex step. Uses a dynamic "flip everything" strategy rather than a hardcoded '
        'list, because Salesforce adds new toggles with every release.',
        BODY))
    how_it_works = [
        '<b>Static seed list:</b> Always targets Bot, EinsteinCopilot, EinsteinAgent, AgentPlatform, Analytics',
        '<b>Dynamic discovery:</b> Enumerates all Settings metadata records; adds any containing "Tableau", "Concierge", or "Semantic"',
        '<b>Retrieves</b> current state of all targets via Metadata API',
        '<b>Identifies</b> every field named <font name="Courier">enable*</font> currently set to false',
        '<b>Skips</b> license-gated fields (e.g. enableCrmaDataCloudIntegration, enableSnowflakeOutputConnector)',
        '<b>Deploys each Settings record individually</b> — one record failing does not block the others',
    ]
    for h in how_it_works:
        story.append(p('•  ' + h, BULLET))
    story.append(sp(4))
    story.append(note_box(
        'The Bot record\'s enableBots flag is the master Agentforce toggle. '
        'This is what makes BotDefinition a valid sObject and allows agents to be created.'))
    story.append(sp(8))

    story.append(p('[g] Data Cloud Feature Editor Flags', H2))
    story.append(p('Script: <font name="Courier">07-enable-feature-manager-flags.ps1</font>', BODY_MUTED))
    story.append(warning_box(
        'This step CANNOT be automated. The Data Cloud Feature Editor has no public REST endpoint, '
        'no Tooling sObject, and no Metadata API surface. The script only emits warnings.'))
    story.append(sp(4))
    story.append(p('Five features require manual enablement in Setup → Feature Editor:', BODY))
    for f in ['Semantic Authoring AI', 'Connectors (Beta)',
              'Accelerated Data Ingest', 'Code Extension', 'Content Tagging']:
        story.append(p(f'•  {f}', BULLET))
    story.append(sp(8))

    story.append(p('[h] Enable Org-Level Dark Mode', H2))
    story.append(p('Script: <font name="Courier">12-enable-dark-mode.ps1</font>', BODY_MUTED))
    story.append(p(
        'Deploys <font name="Courier">Settings:UserInterface</font> with '
        '<font name="Courier">enableSldsV2</font> and '
        '<font name="Courier">enableSldsV2DarkModeInCosmos</font> set to true.',
        BODY))
    story.append(sp(3))
    story.append(warning_box(
        'Per-user dark mode cannot be set via API. Each user must click: '
        'Profile avatar → Appearance → Dark.'))
    story.append(sp(8))

    story.append(p('[k] Create and Activate Analytics and Visualization Agent', H2))
    story.append(p('Script: <font name="Courier">08-create-analytics-agent.ps1</font>', BODY_MUTED))
    story.append(p(
        'Creates the OOTB "Analytics and Visualization" Agentforce agent using '
        '<font name="Courier">sf agent create --spec</font> with a hand-authored spec YAML. '
        'Defines three topics: Data Analysis, Data Alert Management, Data Pro. '
        'Then activates with <font name="Courier">sf agent activate</font>. '
        'If activation fails, automatically attempts a deactivate + reactivate cycle.',
        BODY))
    story.append(sp(3))
    story.append(note_box(
        'Requires step [f+i] to have enabled Bot.enableBots. If BotDefinition is not yet '
        'a valid sObject, the step skips gracefully with a warning.'))
    story.append(sp(8))

    story.append(p('[l] Grant Agent Access via Permission Set', H2))
    story.append(p('Script: <font name="Courier">09-grant-agent-access.ps1</font>', BODY_MUTED))
    story.append(p(
        'Inserts a <font name="Courier">SetupEntityAccess</font> record binding '
        '<font name="Courier">Access_Analytics_Agent</font> (permset) → '
        '<font name="Courier">Analytics_and_Visualization</font> (bot). '
        'Without this, the agent exists and is active but no user can see it.',
        BODY))
    story.append(sp(3))
    story.append(note_box(
        'Uses Tooling API REST insert rather than Metadata XML, because the '
        'agentAccesses XML element name varies across API versions.'))
    story.append(sp(10))
    story.append(hr())

    # ── Section 8: Optional steps detail ──────────────────────────────────────
    story.append(p('Optional Steps — Detail', H1))

    story.append(p('★  Heroku PostgreSQL Connector', H2))
    story.append(p('Script: <font name="Courier">10-create-heroku-connector.ps1</font>  |  '
                   'Flag: <font name="Courier">-WithHeroku</font>', BODY_MUTED))
    story.append(p(
        'POSTs to <font name="Courier">/services/data/v60.0/ssot/external-data-connectors</font> '
        'to create an external data connector pointing at the shared PACE curriculum Heroku '
        'PostgreSQL instance. Best-effort — the endpoint is not officially documented. '
        'Falls back to a manual instruction on failure.',
        BODY))
    story.append(sp(8))

    story.append(p('★  Reckless Analyst Agent', H2))
    story.append(p('Script: <font name="Courier">13-deploy-reckless-analyst-agent.ps1</font>  |  '
                   'Flag: <font name="Courier">-WithRecklessAgent</font>', BODY_MUTED))
    story.append(p(
        'Deploys a custom Agentforce <b>Employee Agent</b> ("Reckless Analyst") that appears '
        'in the Concierge sidebar agent-switcher dropdown alongside the default agent.',
        BODY))
    story.append(sp(4))
    story.append(note_box(
        'Uses the authoring-bundle publish path — the ONLY CLI path that produces an '
        'InternalCopilot (Employee Agent). The sf agent create --spec path always produces '
        'an ExternalCopilot (Service Agent), which never appears in the sidebar.'))
    story.append(sp(4))
    story.append(p('Four actions in sequence:', BODY))
    for i, s in enumerate([
        'Publish <font name="Courier">Reckless_Analyst_Employee</font> via <font name="Courier">sf agent publish authoring-bundle --skip-retrieve</font>',
        'Activate the published version with <font name="Courier">sf agent activate</font>',
        'Deploy the <font name="Courier">Reckless_Analyst_Access</font> permission set from repo source',
        'Wire <font name="Courier">SetupEntityAccess</font> and assign the permset to the running user',
    ], 1):
        story.append(p(f'{i}.  {s}', BULLET))
    story.append(sp(10))
    story.append(hr())

    # ── Section 9: Step o — Tableau site registration ─────────────────────────
    story.append(p('[o] Register Tableau Cloud Sites', H1))
    story.append(p('Script: <font name="Courier">14-register-tableau-sites.ps1</font>', BODY_MUTED))
    story.append(p(
        'Inserts two <font name="Courier">TableauHostMapping</font> records — one for PACE, '
        'one for PACE-NEXUS. This is the Salesforce-side site registry that tells Tableau Next '
        'which Tableau Cloud site to route to when loading dashboards.',
        BODY))
    story.append(sp(6))

    # Sites table
    sites_rows = [
        [Paragraph('<b>Site</b>', TABLE_HDR),
         Paragraph('<b>UrlMatch</b>', TABLE_HDR),
         Paragraph('<b>SiteLuid</b>', TABLE_HDR)],
        [Paragraph('PACE', TABLE_CELL),
         Paragraph('prod-uswest-c.online.tableau.com/pace', TABLE_CELL_MONO),
         Paragraph('5a81db69-14f1-42c7-b6a5-65ec087bf57d', TABLE_CELL_MONO)],
        [Paragraph('PACE-NEXUS', TABLE_CELL),
         Paragraph('prod-uswest-c.online.tableau.com/pace-nexus', TABLE_CELL_MONO),
         Paragraph('6901a397-fe8d-4795-83a0-7a6e7685434f', TABLE_CELL_MONO)],
    ]
    c1, c2, c3 = 25*mm, PAGE_W*0.45, PAGE_W - 25*mm - PAGE_W*0.45
    story.append(Table(sites_rows, colWidths=[c1, c2, c3],
                       style=[('BACKGROUND', (0,0), (-1,0), NAVY),
                              ('ROWBACKGROUNDS', (0,1), (-1,-1), [WHITE, GREY_BG]),
                              ('GRID', (0,0), (-1,-1), 0.4, GREY_LINE),
                              ('TOPPADDING', (0,0), (-1,-1), 5),
                              ('BOTTOMPADDING', (0,0), (-1,-1), 5),
                              ('LEFTPADDING', (0,0), (-1,-1), 6),
                              ('RIGHTPADDING', (0,0), (-1,-1), 6),
                              ('VALIGN', (0,0), (-1,-1), 'MIDDLE')]))
    story.append(sp(8))

    story.append(warning_box(
        'What this step does NOT do: it does not configure authentication between this '
        'Salesforce org and the Tableau sites. Registering the host mapping only tells '
        'Salesforce where the sites are — Tableau still needs to trust this org before '
        'dashboards will load for any user.'))
    story.append(sp(6))
    story.append(p('<b>Tableau-side Direct Trust setup (manual, per-org, per-site):</b>', BODY))
    story.append(p(
        'For each site, a Tableau admin must register this Salesforce org as a trusted issuer '
        'on the site\'s Connected App (Direct Trust). This cannot be scripted without embedding '
        'a Tableau admin PAT — which is not acceptable in a shared script. The step always '
        'emits a warning in the run summary as a reminder.',
        BODY))
    story.append(sp(4))
    story.append(note_box(
        'UI equivalent of the Salesforce side: Setup → Quick Find → "Tableau" → '
        'Embedded Tableau → Add Site. Each row you create there is a TableauHostMapping record.'))
    story.append(sp(10))
    story.append(hr())

    # ── Section 10: After the scripts ─────────────────────────────────────────
    story.append(p('After the Scripts Complete', H1))
    story.append(p(
        'The run summary printed at the end of <font name="Courier">run-resume.ps1</font> '
        'lists every warning and completed step. Items that always require manual follow-up:',
        BODY))
    story.append(sp(8))
    story.append(manual_steps_table())
    story.append(sp(8))
    story.append(p(
        'Once warnings are cleared, the org is at the "ready to connect data and build '
        'Semantic Data Models" milestone — the end of PACE BUILD 1.',
        BODY))
    story.append(sp(10))
    story.append(hr())

    # ── Section 11: Step reference ─────────────────────────────────────────────
    story.append(PageBreak())
    story.append(p('Step Reference', H1))
    story.append(p('★ = optional feature flag', BODY_MUTED))
    story.append(sp(6))
    story.append(step_reference_table())
    story.append(sp(10))

    # ── Section 12: State file ─────────────────────────────────────────────────
    story.append(hr())
    story.append(p('State File', H1))
    story.append(p(
        'Every step writes its outcome to '
        '<font name="Courier">notes/org-setup-state/&lt;alias&gt;.json</font>. '
        'Rerunning either orchestrator is safe — completed steps become noops and '
        'the warning list only includes warnings from the current run.',
        BODY))
    story.append(sp(6))
    story.append(cmd_box(
        '{\n'
        '  "alias": "MFG-Nexus",\n'
        '  "completed": ["a-enable-data-cloud", "b-enable-einstein", "..."],\n'
        '  "warnings": [\n'
        '    { "step": "g-feature-editor", "feature": "Semantic Authoring AI",\n'
        '      "message": "Enable manually: Data Cloud > Feature Editor..." },\n'
        '    { "step": "o-tableau-sites",\n'
        '      "message": "Tableau-side Direct Trust setup required..." }\n'
        '  ],\n'
        '  "log": [...]\n'
        '}'))

    doc.build(story)
    print(f'PDF written to: {OUTPUT_PATH}')

if __name__ == '__main__':
    build()
