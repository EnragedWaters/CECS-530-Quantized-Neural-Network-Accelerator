"""Headless acceptance checks for the short presentation route and optional details."""

from playwright.sync_api import expect


def jump(page, name, extra=False):
    page.locator("#choose-lesson").click()
    if extra and page.locator("#lesson-list details").get_attribute("open") is None:
        page.locator("#lesson-list summary").click()
    page.locator(f'[data-lesson="{name}"]').click()
    expect(page.locator("#lesson-action")).to_be_enabled()


def check_fit(page, screenshots, name):
    overflow = page.evaluate(
        "document.documentElement.scrollWidth>innerWidth+1 || document.documentElement.scrollHeight>innerHeight+1"
    )
    if screenshots:
        page.screenshot(path=str(screenshots / (name + ".png")), full_page=True)
    assert not overflow, (name, "Default lesson needs scrolling")
    assert page.locator("#lesson .primary:visible").count() == 1
    assert len(page.locator("#lesson-instruction").inner_text().split()) <= 35


def check_learning(page, url, screenshots):
    page.set_viewport_size({"width": 1280, "height": 720})
    page.goto(url, wait_until="networkidle")
    expect(page.locator("#welcome")).to_be_visible()
    page.locator("#start-learning").click()
    ids = ["rounding", "cycles", "lanes", "digit", "performance", "capacity"]
    for index, actions in enumerate([1, 6, 2, 5, 1, 1]):
        expect(page.locator("#lesson-progress")).to_contain_text(f"Step {index+1} of 6")
        expect(page.locator("#lesson-action")).to_be_enabled()
        check_fit(page, screenshots, f"{ids[index]}-before")
        for action in range(actions):
            page.locator("#lesson-action").click()
            expect(page.locator("#lesson-action")).to_be_enabled()
            expect(page.locator("#lesson-result")).to_be_visible()
            check_fit(page, screenshots, f"{ids[index]}-{action+1}")
            if index < 3 or (index == 3 and action < 4):
                expect(page.locator(".prediction-reveal")).to_have_count(0)
            if index == 0:
                expect(page.locator("#lesson-result")).to_contain_text("0.03")
            if index == 1:
                expect(page.locator(".cycle-state")).to_contain_text(
                    f"Clock cycle {action+1} of 6"
                )
            if index == 2:
                expect(page.locator(".learning-lane.working")).to_have_count(
                    8 if action == 0 else 4
                )
                expect(page.locator(".learning-lane.waiting")).to_have_count(
                    0 if action == 0 else 4
                )
            if index == 3 and action == 1:
                expect(page.locator(".dot-inspection")).to_contain_text(
                    "3 of 784 terms"
                )
            if index == 3 and action == 3:
                expect(page.locator(".learning-scores rect")).to_have_count(20)
            if index == 3 and action == 4:
                expect(page.locator(".prediction-reveal")).to_contain_text(
                    "FP32 7 · INT8 7"
                )
            if index == 4:
                expect(page.locator(".comparison-bars")).to_contain_text("19,204")
                expect(page.locator(".comparison-bars")).to_contain_text("8,025")
                expect(page.locator(".speed-result")).to_contain_text("2.393")
            if index == 5:
                expect(page.locator("#lesson-result")).to_contain_text("FP32 does not")
        if index == 3:
            before = page.locator("#lesson-visual").inner_text()
            page.locator("#explore-toggle").click()
            frame = page.frame_locator("#explore-frame")
            expect(frame.locator("#toy-stage")).to_be_visible()
            frame.locator("#toy-lanes").select_option("16")
            page.locator("#explore-toggle").click()
            expect(page.locator("#lesson-visual")).to_be_visible()
            assert page.locator("#lesson-visual").inner_text() == before
            page.locator("#explore-toggle").click()
            expect(frame.locator("#toy-lanes")).to_have_value("16")
            page.locator("#explore-toggle").click()
        page.locator("#lesson-action").click()
    expect(page.locator("#finish")).to_be_visible()
    expect(page.locator("#takeaways")).to_contain_text("96.96%")
    expect(page.locator("#takeaways")).to_contain_text("96.98%")
    expect(page.locator("#takeaways")).to_contain_text("PowerPoint")
    page.locator("#restart").click()
    expect(page.locator("#lesson-action")).to_have_text("Convert 1.23")
    # Extra explanations are reachable, but never inserted into the presentation route.
    for name, actions in [
        ("clipping", 1),
        ("adding", 3),
        ("wide", 1),
        ("parallel", 1),
        ("waiting", 1),
        ("pixels", 1),
        ("first", 1),
        ("hidden", 3),
        ("second", 1),
        ("scores", 1),
        ("disagreement", 1),
    ]:
        jump(page, name, True)
        expect(page.locator("#lesson-progress")).to_contain_text("Extra explanation")
        for _ in range(actions):
            page.locator("#lesson-action").click()
            expect(page.locator("#lesson-action")).to_be_enabled()
        expect(page.locator("#lesson-action")).to_have_text("Return to demo")
        expect(page.locator("#lesson-result")).to_be_visible()
        check_fit(page, screenshots, "extra-" + name)
        if name == "adding":
            expect(page.locator(".running-total strong")).to_have_text("29")
        if name == "wide":
            expect(page.locator("#lesson-result")).to_contain_text("16,129")
        if name == "disagreement":
            expect(page.locator("#lesson-result")).to_contain_text("Fifteen")
        page.locator("#lesson-action").click()
        expect(page.locator("#lesson-action")).to_have_text("Convert 1.23")
    # Failed actions keep their place and offer Retry without stale results.
    failed = [False]

    def fail_once(route):
        if not failed[0]:
            failed[0] = True
            route.fulfill(
                status=503,
                content_type="application/json",
                body='{"error":"Temporary check failure"}',
            )
        else:
            route.continue_()

    page.route("**/api/quantize", fail_once)
    page.locator("#lesson-action").click()
    expect(page.locator("#lesson-action")).to_have_text("Retry")
    expect(page.locator("#lesson-error")).to_contain_text("Temporary check failure")
    expect(page.locator("#lesson-visual")).to_be_hidden()
    page.locator("#lesson-action").click()
    expect(page.locator("#lesson-result")).to_contain_text("0.03")
    page.unroute("**/api/quantize", fail_once)
    # Repeated activation makes one request; navigating away rejects its late result.
    page.locator("#replay").click()
    held = []

    def hold(route):
        held.append(route)

    page.route("**/api/quantize", hold)
    page.evaluate(
        "document.querySelector('#lesson-action').click(); document.querySelector('#lesson-action').click()"
    )
    page.wait_for_timeout(100)
    assert len(held) == 1, "Repeated click sent duplicate requests"
    page.locator("#back").click()
    expect(page.locator("#welcome")).to_be_visible()
    with page.expect_response("**/api/quantize"):
        held[0].continue_()
    expect(page.locator("#welcome")).to_be_visible()
    page.unroute("**/api/quantize", hold)
    page.locator("#start-learning").click()
    expect(page.locator("#lesson-result")).to_be_hidden()
    page.locator("#lesson-action").click()
    expect(page.locator("#lesson-result")).to_contain_text("0.03")
    # Step jumping, Back and replay do not silently advance or retain the wrong result.
    jump(page, "cycles")
    page.locator("#lesson-action").click()
    page.locator("#back").click()
    expect(page.locator("#lesson-result")).to_contain_text("0.03")
    jump(page, "cycles")
    expect(page.locator(".cycle-state")).to_contain_text("Clock cycle 1 of 6")
    for _ in range(5):
        page.locator("#lesson-action").click()
    page.locator("#replay").click()
    expect(page.locator(".cycle-state")).to_contain_text("Clock cycle 0 of 6")
    page.locator("#lesson-title").click()
    page.keyboard.press("ArrowRight")
    expect(page.locator(".cycle-state")).to_contain_text("Clock cycle 1 of 6")
    page.locator("#fullscreen").click()
    page.wait_for_function("document.fullscreenElement!==null")
    page.locator("#fullscreen").click()
    page.wait_for_function("document.fullscreenElement===null")
    # Projector, reduced-motion, narrow layouts and enlarged text retain usable controls.
    page.emulate_media(reduced_motion="reduce")
    for width, height in [(1366, 768), (390, 844)]:
        page.set_viewport_size({"width": width, "height": height})
        for name in ids:
            jump(page, name)
            if width == 1366:
                check_fit(page, screenshots, name + "-projector")
            assert page.evaluate(
                "document.documentElement.scrollWidth<=innerWidth+1"
            ), (name, width)
    page.set_viewport_size({"width": 1280, "height": 720})
    page.evaluate("document.body.style.zoom='2'")
    jump(page, "digit")
    assert page.evaluate(
        "document.documentElement.scrollWidth<=innerWidth+1"
    ), "Enlarged page overflows horizontally"
    page.locator("#lesson-action").scroll_into_view_if_needed()
    expect(page.locator("#lesson-action")).to_be_in_viewport()
    page.evaluate("document.body.style.zoom='1'")
