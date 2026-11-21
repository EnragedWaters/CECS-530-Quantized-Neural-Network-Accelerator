"""Exercise the full local UI with external internet requests blocked.

Install demo/requirements-dev.txt and run `python -m playwright install chromium`,
then `python -m demo.tests.browser_check`. Optional --url checks a separately
started copy; --screenshots saves actual desktop/projector/mobile renderings.
"""

import argparse
from pathlib import Path
import socket
import threading
from urllib.parse import urlsplit
from unittest.mock import patch
from playwright.sync_api import sync_playwright, expect


def check(url, screenshots=None):
    screenshots = Path(screenshots) if screenshots else None
    if screenshots:
        screenshots.mkdir(parents=True, exist_ok=True)
    origin = urlsplit(url)
    with sync_playwright() as pw:
        browser = pw.chromium.launch()
        context = browser.new_context(viewport={"width": 1366, "height": 900})
        external = []
        errors = []

        def route(request):
            target = urlsplit(request.request.url)
            if (target.scheme, target.netloc) == (origin.scheme, origin.netloc):
                request.continue_()
            else:
                external.append(request.request.url)
                request.abort()

        context.route("**/*", route)
        page = context.new_page()
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(url, wait_until="networkidle")
        expect(page.locator("#welcome")).to_be_visible()
        page.locator("#start-learning").click()
        expect(page.locator("#lesson-action")).to_have_text("Convert 1.23")
        expect(page.locator("#lesson-result")).to_be_hidden()
        page.locator("#lesson-action").click()
        expect(page.locator("#lesson-result")).to_contain_text("0.03")
        page.set_viewport_size({"width": 1280, "height": 720})
        assert page.evaluate(
            "document.documentElement.scrollHeight <= innerHeight"
        ), "Lesson requires scrolling"
        if screenshots:
            page.screenshot(path=str(screenshots / "first-learning-lesson.png"))
        page.locator("#explore-toggle").click()
        expect(
            page.frame_locator("#explore-frame").locator("#toy-stage")
        ).to_be_visible()
        page.locator("#explore-toggle").click()
        expect(page.locator("#lesson-result")).to_contain_text("0.03")
        page.goto(url + "/explore", wait_until="networkidle")
        expect(page.locator("#toy-stage")).to_be_visible()
        expect(page.locator("#toy-total")).to_have_text("6")
        page.locator("#step").click()
        expect(page.locator("#cycle-label")).to_have_text("Cycle 1 of 6")
        page.locator("#reset").click()
        expect(page.locator("#cycle-label")).to_have_text("Cycle 0 of 6")
        page.locator("h1").click()
        page.keyboard.press("ArrowRight")
        expect(page.locator("#cycle-label")).to_have_text("Cycle 1 of 6")
        page.keyboard.press("ArrowLeft")
        expect(page.locator("#cycle-label")).to_have_text("Cycle 0 of 6")
        page.locator("#playback-speed").select_option("200")
        page.locator("#play").click()
        expect(page.locator("#cycle-label")).to_have_text("Cycle 6 of 6", timeout=10000)
        expect(page.locator("#event-explanation")).to_contain_text("29")
        # Capacity and issue limits cannot be displayed as a stale successful run.
        page.locator("#toy-preset").select_option("parallel")
        expect(page.locator("#toy-total")).to_have_text("6")
        page.locator("#toy-local").select_option("2")
        page.locator('[data-precision="fp32"]').click()
        expect(page.locator("#toy-error")).to_be_visible()
        expect(page.locator("#toy-stage")).to_be_hidden()
        page.locator("#toy-local").select_option("32")
        expect(page.locator("#toy-stage")).to_be_visible()
        expect(page.locator("#toy-total")).to_have_text("11")
        page.locator('[data-precision="int8"]').click()
        page.locator("#toy-local").select_option("8")
        expect(page.locator("#toy-stage")).to_be_visible()
        page.locator("#phase-timeline button").filter(has_text="Compute").click()
        expect(page.locator(".lane.waiting")).to_have_count(4)
        if screenshots:
            page.screenshot(
                path=str(screenshots / "accelerator-waiting.png"), full_page=True
            )
        page.locator("#toy-preset").select_option("tail")
        page.locator("#toy-local").select_option("32")
        expect(page.locator("#toy-answer")).to_have_text("64")
        expect(page.locator("#toy-equation")).to_contain_text("64")
        page.locator('[data-view="numbers"]').click()
        page.locator("#clip-example").click()
        expect(page.locator("#quant-stored")).to_have_text("127")
        expect(page.locator("#quant-explanation")).to_contain_text("clips")
        page.locator("#tie-example").click()
        expect(page.locator("#quant-stored")).to_have_text("0")
        page.locator("#quant-scale").fill("0")
        expect(page.locator("#quant-error")).to_be_visible()
        expect(page.locator("#quant-result")).to_be_hidden()
        page.locator("#round-example").click()
        expect(page.locator("#quant-reconstructed")).to_have_text("1.2")
        if screenshots:
            page.screenshot(path=str(screenshots / "numbers.png"), full_page=True)
        page.locator('[data-view="digit"]').click()
        expect(page.locator("#digit-result")).to_be_visible()
        page.locator('[aria-label="MNIST image 8, known digit 5"]').click()
        expect(page.locator("#selected-example")).to_have_text("MNIST image 8")
        expect(page.locator("#int-prediction")).to_have_text("6")
        expect(page.locator("#digit-result")).to_be_visible()
        expect(page.locator("#digit-verification")).to_contain_text("exact integer")
        for stage in ["first", "hidden", "second", "scores", "pixels"]:
            page.locator(f'[data-stage="{stage}"]').click()
            expect(page.locator("#stage-title")).not_to_be_empty()
        page.locator("#pixel-map").click(position={"x": 85, "y": 90})
        expect(page.locator("#pixel-details")).to_contain_text("Stored INT8")
        page.locator("#gallery-filter").select_option("different")
        expect(page.locator("#digit-gallery button")).to_have_count(15)
        expect(page.locator("#digit-result")).to_be_visible()
        page.wait_for_function(
            "document.querySelector('#fp-prediction').textContent!==document.querySelector('#int-prediction').textContent"
        )
        page.locator('[data-stage="scores"]').click()
        expect(page.locator("#score-chart rect")).to_have_count(20)
        expect(page.locator("#saved-fp-accuracy")).to_have_text("96.96%")
        expect(page.locator("#saved-int-accuracy")).to_have_text("96.98%")
        if screenshots:
            page.screenshot(path=str(screenshots / "digit-scores.png"), full_page=True)
        page.locator('[data-view="hardware"]').click()
        expect(page.locator("#hardware-results")).to_be_visible()
        page.locator('[data-hardware="baseline"]').click()
        expect(page.locator("#hardware-metrics")).to_contain_text("19,204")
        expect(page.locator("#hardware-metrics")).to_contain_text("8,025")
        expect(page.locator("#hardware-metrics")).to_contain_text("2.393×")
        page.locator('[data-hardware="capacity"]').click()
        expect(page.locator("#hardware-format-errors")).to_contain_text("FP32")
        expect(page.locator("#hardware-metrics")).to_contain_text("Unavailable")
        expect(page.locator("#hardware-metrics")).to_contain_text("8,025")
        page.locator('[data-hardware="extra"]').click()
        expect(page.locator("#hardware-metrics")).to_contain_text("4,825")
        page.locator("#hardware-clock").select_option("200")
        expect(page.locator("#hardware-metrics")).to_contain_text("200 MHz")
        expect(page.locator("#hardware-metrics")).to_contain_text("4,825")
        page.locator('[data-hardware="baseline"]').click()
        expect(page.locator("#hardware-metrics")).to_contain_text("2.393×")
        if screenshots:
            page.screenshot(path=str(screenshots / "hardware.png"), full_page=True)
        # Layout must remain readable without horizontal page scrolling.
        for width, height in [(1280, 720), (390, 844)]:
            page.set_viewport_size({"width": width, "height": height})
            for view in ["numbers", "accelerator", "digit", "hardware"]:
                page.locator(f'[data-view="{view}"]').click()
                page.wait_for_timeout(100)
                overflow = page.evaluate(
                    "document.documentElement.scrollWidth>window.innerWidth+1"
                )
                if overflow:
                    if screenshots:
                        page.screenshot(
                            path=str(screenshots / f"overflow-{view}.png"),
                            full_page=True,
                        )
                    offenders = page.evaluate(
                        "Array.from(document.querySelectorAll('body *')).filter(e => e.getBoundingClientRect().right > window.innerWidth + 1).map(e => [e.tagName, e.id, e.className, e.textContent.slice(0,80)])"
                    )
                    raise AssertionError(
                        (width, view, "horizontal overflow", offenders)
                    )
                if screenshots:
                    page.screenshot(
                        path=str(screenshots / f"{view}-{width}.png"), full_page=True
                    )
        assert not errors, errors
        assert not external, external
        context.close()
        browser.close()
    print(
        "PASS: playback, lane states, quantization, all inference stages, disagreements, hardware controls, error recovery, guided tour, and responsive layouts. External browser requests were blocked; none were attempted."
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url")
    parser.add_argument("--screenshots", type=Path)
    args = parser.parse_args()
    server = thread = guard = None
    try:
        if args.url:
            url = args.url
        else:
            connect = socket.socket.connect

            def loopback_only(connection, address):
                if connection.family in (socket.AF_INET, socket.AF_INET6) and address[
                    0
                ] not in ("127.0.0.1", "::1"):
                    raise AssertionError("External backend connection: " + str(address))
                return connect(connection, address)

            guard = patch.object(socket.socket, "connect", loopback_only)
            guard.start()
            from demo.server import make_server

            server = make_server(0)
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            url = f"http://127.0.0.1:{server.server_port}"
        check(url, args.screenshots)
    finally:
        if server:
            server.shutdown()
            server.server_close()
            thread.join()
        if guard:
            guard.stop()
