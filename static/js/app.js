(() => {
  const input = document.getElementById("job_title");
  const box = document.getElementById("suggestions");
  if (!input || !box) return;

  const suggestUrl = input.getAttribute("data-suggest-url");
  let abortController = null;

  function hide() {
    box.classList.add("d-none");
    box.innerHTML = "";
  }

  function show(items) {
    if (!items.length) return hide();
    box.classList.remove("d-none");
    box.innerHTML = items
      .map(
        (t) =>
          `<button type="button" class="list-group-item list-group-item-action">${t}</button>`
      )
      .join("");
  }

  box.addEventListener("click", (e) => {
    const btn = e.target.closest("button");
    if (!btn) return;
    input.value = btn.textContent || "";
    hide();
    input.focus();
  });

  document.addEventListener("click", (e) => {
    if (e.target === input || box.contains(e.target)) return;
    hide();
  });

  input.addEventListener("input", async () => {
    const q = (input.value || "").trim();
    if (!suggestUrl || q.length < 2) return hide();

    if (abortController) abortController.abort();
    abortController = new AbortController();

    try {
      const res = await fetch(`${suggestUrl}?q=${encodeURIComponent(q)}`, {
        signal: abortController.signal,
        headers: { "X-Requested-With": "fetch" },
      });
      if (!res.ok) return hide();
      const data = await res.json();
      show((data && data.titles) || []);
    } catch {
      hide();
    }
  });
})();

