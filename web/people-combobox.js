// Mount an accessible searchable people picker with keyboard and pointer selection.
export function mountPeopleCombobox(container, { onSelect, fetcher = fetch } = {}) {
  const id = `people-${Math.random().toString(36).slice(2)}`;
  const wrap = document.createElement("div");
  wrap.className = "people-combobox";

  const input = document.createElement("input");
  input.id = `${id}-input`;
  input.type = "text";
  input.autocomplete = "off";
  input.placeholder = "Search by name or GitHub login";
  input.setAttribute("role", "combobox");
  input.setAttribute("aria-autocomplete", "list");
  input.setAttribute("aria-expanded", "false");
  input.setAttribute("aria-controls", `${id}-list`);
  input.setAttribute("aria-label", "Choose a Delta Lake contributor");

  const status = document.createElement("div");
  status.className = "picker-status muted";
  status.setAttribute("aria-live", "polite");
  const list = document.createElement("ul");
  list.id = `${id}-list`;
  list.className = "people-options hidden";
  list.setAttribute("role", "listbox");
  wrap.append(input, status, list);
  container.replaceChildren(wrap);

  let options = [];
  let active = -1;
  let timer = 0;
  let request = 0;
  let isOpen = false;

  function setOpen(open) {
    isOpen = open;
    list.classList.toggle("hidden", !open);
    input.setAttribute("aria-expanded", String(open));
    if (!open) input.removeAttribute("aria-activedescendant");
  }

  // Ignore stale responses when a newer search has already started.
  async function search(query = "") {
    const sequence = ++request;
    status.textContent = query ? "Searching contributors…" : "Loading active contributors…";
    setOpen(true);
    list.replaceChildren();
    options = [];
    active = -1;
    try {
      const response = await fetcher(`/api/people?q=${encodeURIComponent(query)}&limit=10`);
      if (!response.ok) {
        const message = response.status === 503
          ? "Contributor list is temporarily unavailable."
          : `Could not load contributors (${response.status}).`;
        throw new Error(message);
      }
      const data = await response.json();
      if (sequence !== request) return;
      options = data.people || [];
      status.textContent = options.length
        ? "Use the arrow keys to choose a contributor."
        : "No contributors matched. Try another name or login.";
      options.forEach((person, index) => addOption(person, index));
    } catch (error) {
      if (sequence === request) status.textContent = error.message;
    }
  }

  function addOption(person, index) {
    const item = document.createElement("li");
    item.id = `${id}-option-${index}`;
    item.setAttribute("role", "option");
    item.setAttribute("aria-selected", "false");
    item.className = "person-option";
    const name = person.name || person.login || "Contributor";
    const initials = name.trim().split(/\s+/).slice(0, 2)
      .map(part => part[0]).join("").toUpperCase();
    const avatar = document.createElement("span");
    avatar.className = "avatar";
    avatar.textContent = initials || "?";
    const info = document.createElement("span");
    info.className = "person-info";
    const display = document.createElement("strong");
    display.textContent = name;
    const login = document.createElement("span");
    login.textContent = `@${person.login}`;
    const count = document.createElement("span");
    count.className = "commit-count";
    count.textContent = `${Number(person.recentCommits || 0).toLocaleString()} recent commits`;
    info.append(display, login, count);
    item.append(avatar, info);
    item.addEventListener("mousedown", event => event.preventDefault());
    item.addEventListener("click", () => choose(index));
    list.append(item);
  }

  function highlight(index) {
    if (!options.length) return;
    active = (index + options.length) % options.length;
    [...list.children].forEach((item, itemIndex) => {
      item.setAttribute("aria-selected", String(itemIndex === active));
      item.classList.toggle("active", itemIndex === active);
    });
    input.setAttribute("aria-activedescendant", `${id}-option-${active}`);
    list.children[active]?.scrollIntoView({ block: "nearest" });
  }

  function choose(index) {
    const person = options[index];
    if (!person) return;
    input.value = `${person.name || person.login} (@${person.login})`;
    input.dataset.selected = "true";
    setOpen(false);
    status.textContent = "";
    onSelect?.(person);
  }

  input.addEventListener("focus", () => {
    clearTimeout(timer);
    search(input.dataset.selected ? input.value : "");
    input.dataset.selected = "";
  });
  input.addEventListener("input", () => {
    input.dataset.selected = "";
    request++;
    clearTimeout(timer);
    timer = setTimeout(() => search(input.value.trim()), 150);
  });
  input.addEventListener("keydown", event => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      if (!isOpen) search(input.value.trim()).then(() => highlight(0));
      else highlight(active + 1);
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      if (!isOpen) search(input.value.trim()).then(() => highlight(options.length - 1));
      else highlight(active < 0 ? options.length - 1 : active - 1);
    } else if (event.key === "Home" && isOpen) {
      event.preventDefault();
      highlight(0);
    } else if (event.key === "End" && isOpen) {
      event.preventDefault();
      highlight(options.length - 1);
    } else if (event.key === "Enter" && isOpen && active >= 0) {
      event.preventDefault();
      choose(active);
    } else if (event.key === "Escape") {
      setOpen(false);
      status.textContent = "";
    }
  });
  input.addEventListener("blur", () => setTimeout(() => setOpen(false), 120));

  return {
    focus: () => input.focus(),
    setValue: value => {
      input.value = value;
      input.dataset.selected = "true";
    },
    input,
  };
}
