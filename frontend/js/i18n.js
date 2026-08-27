/**
 * Minimal multilingual architecture (spec section 20). Loads a flat
 * key->string JSON for the selected language and applies it to any element
 * with `data-i18n="key"` (text content) or `data-i18n-placeholder="key"`.
 * English is complete; Hindi/Marathi are partial -- missing keys silently
 * fall back to the English string so the UI never shows a raw key.
 */
const NaviXI18n = (() => {
  const LANG_KEY = "navix_lang";
  const SUPPORTED = ["en", "hi", "mr"];
  let strings = {};
  let fallback = {};

  async function loadLang(lang) {
    if (!SUPPORTED.includes(lang)) lang = "en";
    fallback = await fetch("/i18n/en.json").then((r) => r.json());
    strings = lang === "en" ? fallback : await fetch(`/i18n/${lang}.json`).then((r) => r.json()).catch(() => ({}));
    localStorage.setItem(LANG_KEY, lang);
    apply();
  }

  function t(key) {
    return strings[key] || fallback[key] || key;
  }

  function apply() {
    document.querySelectorAll("[data-i18n]").forEach((el) => {
      el.textContent = t(el.getAttribute("data-i18n"));
    });
    document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
      el.setAttribute("placeholder", t(el.getAttribute("data-i18n-placeholder")));
    });
  }

  function getLang() {
    return localStorage.getItem(LANG_KEY) || "en";
  }

  function init() {
    loadLang(getLang());
    document.querySelectorAll("[data-lang-switch]").forEach((el) => {
      el.addEventListener("click", (e) => {
        e.preventDefault();
        loadLang(el.getAttribute("data-lang-switch"));
      });
    });
  }

  document.addEventListener("DOMContentLoaded", init);
  return { t, loadLang, getLang };
})();
