// Keep the navbar's tabs on one line, however many tags there are. When they
// don't fit, the line scrolls sideways: with arrow buttons at either end, a
// trackpad or touch swipe, or a mouse wheel.
$(function () {
  const tabs = document.getElementById("tabs");
  const strip = document.createElement("div");
  strip.className = "hub-tab-strip";
  tabs.parentNode.insertBefore(strip, tabs);

  function arrow(direction, label, symbol) {
    const button = document.createElement("button");
    button.type = "button";
    button.className = "hub-tab-arrow";
    button.setAttribute("aria-label", label);
    button.textContent = symbol;
    button.addEventListener("click", function () {
      tabs.scrollBy({ left: direction * tabs.clientWidth * 0.8, behavior: "smooth" });
    });
    return button;
  }
  const back = arrow(-1, "Scroll tabs left", "‹");
  const forward = arrow(1, "Scroll tabs right", "›");
  strip.append(back, tabs, forward);

  // Show the arrows only when the tabs overflow, and hide each one at its
  // end of the line.
  function update() {
    strip.classList.toggle("overflowing", tabs.scrollWidth > tabs.clientWidth);
    back.disabled = tabs.scrollLeft <= 0;
    forward.disabled = tabs.scrollLeft + tabs.clientWidth >= tabs.scrollWidth - 1;
  }
  tabs.addEventListener("scroll", update);
  window.addEventListener("resize", update);
  // The server adds the tabs after the page loads.
  new MutationObserver(update).observe(tabs, { childList: true });
  update();

  // An ordinary mouse wheel only scrolls vertically; turn that into
  // sideways scrolling while the pointer is over the tabs.
  tabs.addEventListener(
    "wheel",
    function (event) {
      if (strip.classList.contains("overflowing") && Math.abs(event.deltaY) > Math.abs(event.deltaX)) {
        tabs.scrollLeft += event.deltaY;
        event.preventDefault();
      }
    },
    { passive: false }
  );

  // Bring a newly selected tab fully into view.
  $(tabs).on("shown.bs.tab", function (event) {
    event.target.scrollIntoView({ block: "nearest", inline: "nearest", behavior: "smooth" });
  });
});
