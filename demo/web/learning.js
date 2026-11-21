import { lessons, extraLessons, summary } from "/lessons.js";
const $ = (id) => document.getElementById(id);
const catalog = [...lessons, ...extraLessons];
const entries = catalog.map(() => ({ step: 0, data: null, ready: false }));
let index = -1,
  version = 0,
  busy = false,
  failure = null,
  exploring = false,
  detailReturn = 0;
export async function api(path, body) {
  const response = await fetch(
    path,
    body === undefined
      ? {}
      : {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify(body),
        },
  );
  const data = await response.json();
  if (!response.ok) throw Error(data.error || "This example could not load.");
  return data;
}
function screens(name) {
  for (const id of ["welcome", "lesson", "finish"]) $(id).hidden = id !== name;
}
function focusAction() {
  $("lesson-action").focus({ preventScroll: true });
}
function nextIndex() {
  return index >= lessons.length
    ? detailReturn
    : index === lessons.length - 1
      ? -2
      : index + 1;
}
function render() {
  const lesson = catalog[index],
    entry = entries[index],
    complete = entry.step >= lesson.steps,
    extra = index >= lessons.length;
  $("lesson-progress").textContent = extra
    ? `Extra explanation · ${lesson.chapter}`
    : `${lesson.chapter} · Step ${index + 1} of ${lessons.length}`;
  $("lesson-title").textContent = lesson.title;
  const after = extra
    ? "Return to demo"
    : index === lessons.length - 1
      ? "Finish demo"
      : "Next step →";
  const action = complete
    ? after
    : typeof lesson.button === "function"
      ? lesson.button(entry)
      : lesson.button;
  $("lesson-action").textContent = busy
    ? "Loading…"
    : failure
      ? "Retry"
      : action;
  $("lesson-action").disabled = busy;
  $("lesson-instruction").textContent = busy
    ? "Loading this example…"
    : failure
      ? "This action could not finish. Press “Retry” to try again."
      : complete
        ? `Press “${after.replace(" →", "")}” when you are ready to continue.`
        : typeof lesson.instruction === "function"
          ? lesson.instruction(entry)
          : lesson.instruction;
  $("lesson-visual").hidden = Boolean(failure);
  if (!failure) $("lesson-visual").innerHTML = lesson.render(entry);
  $("lesson-error").hidden = !failure;
  $("lesson-error").textContent = failure?.message || "";
  $("lesson-result").hidden = !entry.step || Boolean(failure) || busy;
  $("lesson-result").textContent = entry.step ? lesson.explain(entry) : "";
  $("replay").hidden = !complete;
  $("skip").hidden = complete || extra;
  $("back").textContent = extra ? "← Return to demo" : "← Back";
  $("back").hidden = extra && complete;
}
async function finish() {
  screens("finish");
  $("takeaways").textContent = "Loading the saved full-test summary…";
  const token = version;
  try {
    const content = await summary(api);
    if (version === token) $("takeaways").innerHTML = content;
  } catch {
    if (version !== token) return;
    $("takeaways").textContent = "The saved summary could not load. ";
    const button = document.createElement("button");
    button.textContent = "Retry summary";
    button.onclick = finish;
    $("takeaways").append(button);
  }
}
async function go(next) {
  const token = ++version;
  busy = false;
  failure = null;
  index = next;
  if (index === -1) {
    screens("welcome");
    $("start-learning").focus({ preventScroll: true });
    return;
  }
  if (index === -2) {
    await finish();
    return;
  }
  screens("lesson");
  const lesson = catalog[index],
    entry = entries[index];
  if (lesson.load && !entry.ready) {
    busy = true;
    render();
    try {
      const data = await lesson.load(api);
      if (token !== version) return;
      entry.data = data;
      entry.ready = true;
    } catch (error) {
      if (token !== version) return;
      failure = error;
    }
    busy = false;
  }
  render();
  window.scrollTo({ top: 0, behavior: "instant" });
  focusAction();
}
async function act() {
  if (busy || exploring || index < 0) return;
  const lesson = catalog[index],
    entry = entries[index];
  if (entry.step >= lesson.steps && !failure) {
    await go(nextIndex());
    return;
  }
  if (lesson.load && !entry.ready) {
    await go(index);
    return;
  }
  const token = version;
  busy = true;
  failure = null;
  render();
  try {
    const data = await lesson.act(entry, api);
    if (token !== version) return;
    if (data !== undefined) entry.data = data;
    entry.step++;
    busy = false;
    render();
    focusAction();
  } catch (error) {
    if (token !== version) return;
    busy = false;
    failure = error;
    render();
    focusAction();
  }
}
function explore() {
  exploring = !exploring;
  $("learning-main").hidden = exploring;
  $("exploration").hidden = !exploring;
  $("explore-toggle").textContent = exploring ? "← Return to demo" : "Explore";
  $("choose-lesson").hidden = exploring;
  if (exploring && !$("explore-frame").getAttribute("src"))
    $("explore-frame").src = "/explore";
  if (!exploring) {
    $("explore-frame").contentWindow?.postMessage(
      "pause-explore",
      location.origin,
    );
    $("explore-toggle").focus({ preventScroll: true });
  }
}
function picker() {
  $("lesson-picker").showModal();
}
$("start-learning").onclick = () => go(0);
$("lesson-action").onclick = act;
$("back").onclick = () =>
  go(index >= lessons.length ? detailReturn : index - 1);
$("skip").onclick = () => go(nextIndex());
$("replay").onclick = () => {
  entries[index] = { ...entries[index], step: 0 };
  go(index);
};
$("restart").onclick = () => {
  entries.forEach((e) => (e.step = 0));
  go(0);
};
$("explore-toggle").onclick = explore;
$("finish-explore").onclick = explore;
$("choose-lesson").onclick = picker;
$("finish-lessons").onclick = picker;
$("close-picker").onclick = () => $("lesson-picker").close();
function lessonButton(l, i) {
  const button = document.createElement("button");
  button.dataset.lesson = l.id;
  button.textContent = l.title;
  button.onclick = () => {
    if (i >= lessons.length && index < lessons.length) detailReturn = index;
    $("lesson-picker").close();
    go(i);
  };
  return button;
}
$("lesson-list").replaceChildren(...lessons.map((l, i) => lessonButton(l, i)));
const details = document.createElement("details"),
  label = document.createElement("summary"),
  extra = document.createElement("div");
label.textContent = "Extra explanations (optional)";
extra.className = "extra-list";
extra.append(
  ...extraLessons.map((l, i) => lessonButton(l, i + lessons.length)),
);
details.append(label, extra);
$("lesson-list").append(details);
$("fullscreen").onclick = async () => {
  try {
    if (document.fullscreenElement) await document.exitFullscreen();
    else await document.documentElement.requestFullscreen();
  } catch {
    $("fullscreen").textContent = "Use your browser’s full screen";
  }
};
document.addEventListener(
  "fullscreenchange",
  () =>
    ($("fullscreen").textContent = document.fullscreenElement
      ? "Exit full screen"
      : "Full screen"),
);
document.addEventListener("keydown", (event) => {
  if (
    exploring ||
    $("lesson-picker").open ||
    index < 0 ||
    ["INPUT", "SELECT", "TEXTAREA", "BUTTON", "A"].includes(
      document.activeElement.tagName,
    )
  )
    return;
  if (event.code === "ArrowRight") {
    event.preventDefault();
    act();
  }
  if (event.code === "ArrowLeft") {
    event.preventDefault();
    go(index >= lessons.length ? detailReturn : index - 1);
  }
});
window.addEventListener("message", (event) => {
  if (
    event.origin === location.origin &&
    event.source === $("explore-frame").contentWindow &&
    event.data === "close-explore" &&
    exploring
  )
    explore();
});
