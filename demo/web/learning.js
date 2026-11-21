import { lessons } from "/lessons.js";
const $ = (id) => document.getElementById(id);
const entries = lessons.map(() => ({ step: 0, data: null, ready: false }));
let index = -1,
  version = 0,
  busy = false,
  failure = null,
  exploring = false;
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
function render() {
  const lesson = lessons[index],
    entry = entries[index],
    complete = entry.step >= lesson.steps;
  $("lesson-progress").textContent =
    `${lesson.chapter} · Lesson ${index + 1} of ${lessons.length}`;
  $("lesson-title").textContent = lesson.title;
  const action = complete
    ? "Next lesson →"
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
        ? "Press “Next lesson” when you are ready to continue."
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
  $("skip").hidden = complete;
}
async function go(next) {
  const token = ++version;
  busy = false;
  failure = null;
  index = next;
  if (index < 0) {
    screens("welcome");
    return;
  }
  if (index >= lessons.length) {
    screens("finish");
    $("takeaways").innerHTML =
      "<p>Smaller operands reduce storage and data movement.</p><p>Rounding can change a result.</p>";
    return;
  }
  screens("lesson");
  const lesson = lessons[index],
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
}
async function act() {
  if (busy || exploring) return;
  const lesson = lessons[index],
    entry = entries[index];
  if (entry.step >= lesson.steps && !failure) {
    await go(index + 1);
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
  } catch (error) {
    if (token !== version) return;
    busy = false;
    failure = error;
    render();
  }
}
function explore() {
  exploring = !exploring;
  $("learning-main").hidden = exploring;
  $("exploration").hidden = !exploring;
  $("explore-toggle").textContent = exploring
    ? "← Return to lesson"
    : "Explore";
  $("choose-lesson").hidden = exploring;
  if (exploring && !$("explore-frame").getAttribute("src"))
    $("explore-frame").src = "/explore";
}
function picker() {
  $("lesson-picker").showModal();
}
$("start-learning").onclick = () => go(0);
$("lesson-action").onclick = act;
$("back").onclick = () => go(index - 1);
$("skip").onclick = () => go(index + 1);
$("replay").onclick = () => {
  entries[index] = {
    step: 0,
    data: entries[index].data,
    ready: entries[index].ready,
  };
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
$("lesson-list").replaceChildren(
  ...lessons.map((lesson, i) => {
    const button = document.createElement("button");
    button.textContent = `${i + 1}. ${lesson.title}`;
    button.onclick = () => {
      $("lesson-picker").close();
      go(i);
    };
    return button;
  }),
);
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
