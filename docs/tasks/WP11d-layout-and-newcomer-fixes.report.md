1. **Layout:** Each view now has one left-column wrapper beside its evidence panel; added a structure regression test.
2. **Ask chat:** Starter chips precede the transcript; the desktop composer stays at the bottom, and new questions and answers scroll into view.
3. **Evidence:** Empty panels show a compact placeholder; the Leave view clears prior evidence when no maintainer is selected.
4. **Starter tools:** Tool chips open departure details or show readable tables with evidence graphs instead of raw JSON.
5. **Memory:** The banner recalls the last question and mentions new commits only when present; added the anonymous ID explanation.
6. **Departure graph:** Focus view keeps people, components, and decisions, with role-based concentric layout and 11px labels.

**Checks:** pytest: 96 passed; Node syntax checks and graph-cap checks passed.

**Couldn’t verify:** Browser access was unavailable, so I couldn’t measure chip/composer positions at 1280×765. Commit was blocked because `.git/index.lock` could not be created. The untracked WP11d brief remains untouched.