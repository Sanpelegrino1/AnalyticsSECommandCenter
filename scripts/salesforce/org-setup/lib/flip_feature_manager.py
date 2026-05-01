"""
Flip Data Cloud Feature Manager toggles via headless Playwright.

Usage:
    python flip_feature_manager.py --instance-url https://xxx.salesforce.com
                                   --access-token 00Dxxx...
                                   --features "Semantic Authoring AI,Connectors (Beta),Accelerated Data Ingest,Code Extension,Content Tagging"
                                   [--headless false]   # show browser window (debug)
                                   [--debug]            # save screenshot + HTML on failure

Page structure (confirmed from live snapshot):
    Each feature is a <lightning-card> containing:
      - <span data-tid="name">Feature Name</span>  (the label)
      - <button aria-pressed="false|true">          (the Enable/Disable toggle)
        inside a <lightning-button-stateful class="enablement-toggle-btn">

Exits 0 on success (all targets found and enabled).
Exits 1 if any target feature could not be found or toggled.
Prints JSON results to stdout on completion.
"""

import argparse
import json
import os
import sys
import time
from urllib.parse import quote


def _save_debug(page, label, debug_dir):
    try:
        os.makedirs(debug_dir, exist_ok=True)
        safe = label.replace(' ', '_').replace('/', '_').replace('(', '').replace(')', '')
        page.screenshot(path=os.path.join(debug_dir, f'{safe}.png'), full_page=True)
        with open(os.path.join(debug_dir, f'{safe}.html'), 'w', encoding='utf-8') as f:
            f.write(page.content())
        sys.stderr.write(f'[debug] saved snapshot: {debug_dir}/{safe}.png\n')
    except Exception as ex:
        sys.stderr.write(f'[debug] could not save snapshot: {ex}\n')


def _confirm_popup(page, feature, do_debug, debug_dir):
    """
    If a confirmation modal appears after clicking Enable, click the confirm button.
    Uses JS dispatch to bypass Playwright's pointer-interception check, then waits
    for the modal to fully disappear before returning.
    """
    from playwright.sync_api import TimeoutError as PWTimeout

    # Wait specifically for the SLDS confirmation modal (section.slds-modal), NOT
    # generic [role=dialog] which matches the always-present Copilot panel too.
    modal_sel = 'section.slds-modal'
    modal_visible = False
    try:
        page.wait_for_selector(modal_sel, state='visible', timeout=5000)
        modal_visible = True
    except PWTimeout:
        pass

    if not modal_visible:
        sys.stderr.write(f'[info] no confirmation popup for: {feature}\n')
        return

    if do_debug:
        _save_debug(page, f'popup_{feature}', debug_dir)

    # Some Beta features require ticking a "I understand / accept terms" checkbox
    # before the Enable button becomes active. Check and tick it if present.
    terms_checkbox = page.locator(f'{modal_sel} input[type="checkbox"]').first
    try:
        has_checkbox = terms_checkbox.count() > 0 and terms_checkbox.is_visible()
    except Exception:
        has_checkbox = False

    if has_checkbox:
        try:
            already_checked = terms_checkbox.is_checked()
        except Exception:
            already_checked = False
        if not already_checked:
            sys.stderr.write(f'[info] ticking terms checkbox for: {feature}\n')
            try:
                terms_checkbox.evaluate('el => el.click()')
            except Exception:
                try:
                    terms_checkbox.click(force=True)
                except Exception as e:
                    sys.stderr.write(f'[warn] could not tick checkbox: {e}\n')
            time.sleep(0.3)

    # Find the Enable button inside the SLDS modal
    confirm_btn = page.locator(f'{modal_sel} button:has-text("Enable")').first
    try:
        found = confirm_btn.count() > 0 and confirm_btn.is_visible()
    except Exception:
        found = False

    if not found:
        confirm_btn = page.locator(f'{modal_sel} button.slds-button_brand').first
        try:
            found = confirm_btn.count() > 0
        except Exception:
            found = False

    if not found:
        sys.stderr.write(f'[warn] modal open but confirm button not found for: {feature}\n')
        return

    sys.stderr.write(f'[info] confirming popup for: {feature}\n')

    # Use JS click to bypass Playwright overlay-interception block
    try:
        confirm_btn.evaluate('el => el.click()')
    except Exception as e:
        sys.stderr.write(f'[warn] JS click failed, trying normal click: {e}\n')
        try:
            confirm_btn.click(force=True)
        except Exception as e2:
            sys.stderr.write(f'[warn] force click also failed: {e2}\n')
            return

    # Wait for the SLDS modal to disappear before continuing
    try:
        page.wait_for_selector(modal_sel, state='hidden', timeout=10000)
        sys.stderr.write(f'[info] modal closed for: {feature}\n')
    except PWTimeout:
        sys.stderr.write(f'[warn] modal did not close within 10s for: {feature}\n')

    time.sleep(0.5)


def _find_card_for_feature(page, feature):
    """
    Returns the lightning-card locator that contains the feature name,
    or None if not found.

    The Feature Manager page renders each feature as a lightning-card.
    Playwright serialises the full Shadow DOM into page.content(), so
    locators with :has-text() work against the rendered text.
    """
    # Primary: lightning-card whose rendered text contains the feature name.
    # Use filter to be precise about exact text match within the card.
    card = page.locator('lightning-card').filter(has_text=feature)
    try:
        count = card.count()
    except Exception:
        count = 0

    if count > 0:
        return card.first

    return None


def _get_button(card):
    """Return the enablement button inside the card."""
    # Primary: stateful enable/disable button
    btn = card.locator('lightning-button-stateful.enablement-toggle-btn button')
    if btn.count() > 0:
        return btn.first

    # aria-pressed variant
    btn2 = card.locator('button[aria-pressed]')
    if btn2.count() > 0:
        return btn2.first

    # Processing/Enabled plain button (no aria-pressed, no stateful host)
    # These appear in the card actions slot after a feature is enabled/processing
    btn3 = card.locator('.slds-no-flex button, [slot="actions"] button')
    if btn3.count() > 0:
        return btn3.first

    return None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--instance-url')
    parser.add_argument('--access-token')
    parser.add_argument('--features', help='Comma-separated feature names')
    parser.add_argument('--headless', default='true')
    parser.add_argument('--debug', action='store_true',
                        help='Save screenshot + HTML on failure')
    parser.add_argument('--args-file', help='JSON file with instance_url/access_token/features/debug')
    args = parser.parse_args()

    # Load from args file if provided (avoids shell quoting issues with tokens)
    if args.args_file:
        with open(args.args_file, 'r', encoding='utf-8-sig') as f:
            file_args = json.load(f)
        args.instance_url = file_args.get('instance_url', args.instance_url)
        args.access_token = file_args.get('access_token', args.access_token)
        args.features     = file_args.get('features', args.features)
        if file_args.get('debug'):
            args.debug = True
        try:
            os.remove(args.args_file)
        except Exception:
            pass

    if not args.instance_url or not args.access_token or not args.features:
        sys.stderr.write('[error] --instance-url, --access-token, and --features are required\n')
        sys.exit(1)

    targets = [f.strip() for f in args.features.split(',') if f.strip()]
    headless = args.headless.lower() != 'false'
    instance = args.instance_url.rstrip('/')
    debug_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'feature_manager_debug')

    try:
        from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout
    except ImportError:
        print(json.dumps({'error': 'playwright not importable', 'results': []}))
        sys.exit(1)

    results = []

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        context = browser.new_context(viewport={'width': 1440, 'height': 900})
        page = context.new_page()

        ret_url = '/lightning/setup/BetaFeaturesSetup/home'
        frontdoor = f"{instance}/secur/frontdoor.jsp?sid={quote(args.access_token)}&retURL={quote(ret_url)}"

        sys.stderr.write('[info] navigating to Feature Manager...\n')
        try:
            page.goto(frontdoor, wait_until='domcontentloaded', timeout=45000)
        except PWTimeout:
            sys.stderr.write('[warn] domcontentloaded timed out; continuing\n')

        # Wait for feature cards to appear. On fresh orgs Data Cloud Feature Manager
        # can take 30-60s to populate; if we still see zero cards after that, the
        # feature set is not yet available and we should bail cleanly rather than
        # marking each target as not_found.
        sys.stderr.write('[info] waiting for feature cards (up to 60s)...\n')
        try:
            page.wait_for_selector('lightning-card', timeout=60000)
            sys.stderr.write('[info] feature cards found\n')
        except PWTimeout:
            sys.stderr.write('[warn] lightning-card not found within 60s\n')

        # Extra settle time for all cards to render
        time.sleep(3)

        if args.debug:
            _save_debug(page, 'page_loaded', debug_dir)

        card_count = page.locator('lightning-card').count()
        sys.stderr.write(f'[info] {card_count} feature card(s) visible on page\n')
        if card_count == 0:
            sys.stderr.write('[warn] no feature cards rendered -- DC Feature Manager may still be initializing on this org\n')
            for feature in targets:
                results.append({
                    'feature': feature,
                    'status': 'page_not_ready',
                    'message': 'Data Cloud Feature Manager page had no features rendered yet. Rerun setup in a few minutes.'
                })
            print(json.dumps({'success': False, 'results': results, 'reason': 'page_not_ready'}))
            context.close()
            browser.close()
            return 2

        for feature in targets:
            result = {'feature': feature, 'status': 'not_found', 'message': ''}
            sys.stderr.write(f'[info] looking for: {feature}\n')
            try:
                card = _find_card_for_feature(page, feature)

                if card is None:
                    result['status'] = 'not_found'
                    result['message'] = f'Could not locate card for "{feature}" on the page.'
                    sys.stderr.write(f'[warn] card not found: {feature}\n')
                    if args.debug:
                        _save_debug(page, f'not_found_{feature}', debug_dir)
                    results.append(result)
                    continue

                btn = _get_button(card)
                if btn is None:
                    result['status'] = 'not_found'
                    result['message'] = f'Found card for "{feature}" but no enablement button inside it.'
                    sys.stderr.write(f'[warn] button not found in card: {feature}\n')
                    if args.debug:
                        _save_debug(page, f'no_button_{feature}', debug_dir)
                    results.append(result)
                    continue

                # aria-pressed="true" OR button text "Enabled"/"Processing" means already on
                aria_pressed = btn.get_attribute('aria-pressed')
                try:
                    btn_label = btn.inner_text().strip().lower()
                except Exception:
                    btn_label = ''
                already_on = (aria_pressed == 'true') or (btn_label in {'enabled', 'processing', 'disabling', 'disable'})

                if already_on:
                    result['status'] = 'already_enabled'
                    result['message'] = f'"{feature}" was already enabled.'
                    sys.stderr.write(f'[info] already enabled: {feature}\n')
                else:
                    sys.stderr.write(f'[info] clicking Enable for: {feature}\n')
                    btn.scroll_into_view_if_needed()
                    btn.click(force=True)

                    # Handle confirmation popup
                    _confirm_popup(page, feature, args.debug, debug_dir)

                    # Re-locate the card/button after modal closes (DOM may have refreshed)
                    time.sleep(1.5)
                    card2 = _find_card_for_feature(page, feature)
                    btn2 = _get_button(card2) if card2 else None

                    aria_after = None
                    btn_text = None
                    if btn2:
                        try:
                            aria_after = btn2.get_attribute('aria-pressed')
                        except Exception:
                            pass
                        try:
                            btn_text = btn2.inner_text().strip().lower()
                        except Exception:
                            pass

                    # Success conditions:
                    #   aria-pressed="true"  -- standard stateful button
                    #   button text is "enabled" or "processing" -- SF sometimes
                    #   transitions through "Processing" before settling on "Enabled"
                    success_texts = {'enabled', 'processing', 'disabling', 'disable'}
                    if aria_after == 'true' or (btn_text and btn_text in success_texts):
                        result['status'] = 'enabled'
                        result['message'] = f'"{feature}" successfully enabled.'
                        sys.stderr.write(f'[info] enabled: {feature}\n')
                    else:
                        result['status'] = 'failed'
                        result['message'] = f'Clicked Enable for "{feature}" but aria-pressed did not become true (got: {aria_after}, btn_text: {btn_text}).'
                        sys.stderr.write(f'[warn] click did not flip: {feature}\n')
                        if args.debug:
                            _save_debug(page, f'failed_{feature}', debug_dir)

            except Exception as e:
                result['status'] = 'error'
                result['message'] = str(e)
                sys.stderr.write(f'[error] {feature}: {e}\n')
                if args.debug:
                    _save_debug(page, f'error_{feature}', debug_dir)

            results.append(result)

        browser.close()

    any_failed = any(r['status'] in ('not_found', 'failed', 'error') for r in results)
    print(json.dumps({'results': results}))
    sys.exit(1 if any_failed else 0)


if __name__ == '__main__':
    main()
