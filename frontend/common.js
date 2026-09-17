/*
 * Bloc partagé par toutes les pages protégées (tout sauf login.html) :
 * URL de l'API, session courante, garde de connexion, affichage du badge
 * utilisateur et masquage des liens réservés aux admins.
 */

const API_BASE_URL = window.location.hostname === "localhost" || window.location.hostname === "127.0.0.1"
  ? "http://localhost:8000"
  : "/cartographie/api";

const currentUser = sessionStorage.getItem("currentUser");
const currentRole = sessionStorage.getItem("currentRole");

if (!currentUser) {
  window.location.href = "login.html";
}

const userBadge = document.getElementById("user-badge");
if (userBadge) {
  userBadge.textContent = `👤 ${currentUser} (${currentRole})`;
}

if (currentRole !== "ADMIN") {
  document.querySelectorAll(".admin-only").forEach(el => {
    el.style.display = "none";
  });
}

/* =========================================================
   Dialogues stylisés — remplacent alert() / confirm() / prompt()
   natifs par des boîtes de dialogue cohérentes avec l'UI (mêmes
   tokens que style.css). Chacune renvoie une Promise, avec la
   même sémantique que son équivalent natif :
     showAlert(message)              -> Promise<void>
     showConfirm(message)            -> Promise<boolean>
     showPrompt(message, default)    -> Promise<string|null>
========================================================= */

let _dialogBackdrop = null;
let _dialogCancelActive = null; // ferme le dialogue en cours s'il y en a un

function _ensureDialogBackdrop() {
  if (_dialogBackdrop) return _dialogBackdrop;

  const backdrop = document.createElement("div");
  backdrop.className = "modal-backdrop";
  backdrop.innerHTML = `
    <div class="dialog-box" role="alertdialog" aria-modal="true">
      <h3 class="dialog-title"></h3>
      <p class="dialog-message"></p>
      <input type="text" style="display:none;" />
      <div class="dialog-actions"></div>
    </div>
  `;
  document.body.appendChild(backdrop);
  _dialogBackdrop = backdrop;
  return backdrop;
}

function _openDialog({ type, title, message, defaultValue, okText, cancelText, danger }) {
  if (_dialogCancelActive) _dialogCancelActive();

  return new Promise(resolve => {
    const backdrop = _ensureDialogBackdrop();
    const box = backdrop.querySelector(".dialog-box");
    const titleEl = box.querySelector(".dialog-title");
    const messageEl = box.querySelector(".dialog-message");
    const inputEl = box.querySelector("input");
    const actionsEl = box.querySelector(".dialog-actions");

    titleEl.textContent = title || "";
    titleEl.style.display = title ? "block" : "none";
    messageEl.textContent = message || "";

    const isPrompt = type === "prompt";
    inputEl.style.display = isPrompt ? "block" : "none";
    inputEl.value = isPrompt ? (defaultValue ?? "") : "";

    actionsEl.innerHTML = "";

    const previouslyFocused = document.activeElement;
    const cancelValue = type === "prompt" ? null : (type === "confirm" ? false : undefined);

    function close(result) {
      backdrop.style.display = "none";
      document.removeEventListener("keydown", onKeydown);
      backdrop.removeEventListener("mousedown", onBackdropClick);
      if (previouslyFocused && previouslyFocused.focus) previouslyFocused.focus();
      _dialogCancelActive = null;
      resolve(result);
    }

    function confirmAction() {
      close(isPrompt ? inputEl.value : (type === "confirm" ? true : undefined));
    }

    function onKeydown(e) {
      if (e.key === "Escape") {
        e.preventDefault();
        close(cancelValue);
      } else if (e.key === "Enter" && (!isPrompt || document.activeElement === inputEl)) {
        e.preventDefault();
        confirmAction();
      }
    }

    function onBackdropClick(e) {
      if (e.target === backdrop) close(cancelValue);
    }

    if (type !== "alert") {
      const cancelBtn = document.createElement("button");
      cancelBtn.type = "button";
      cancelBtn.className = "btn btn-ghost";
      cancelBtn.textContent = cancelText || "Annuler";
      cancelBtn.onclick = () => close(cancelValue);
      actionsEl.appendChild(cancelBtn);
    }

    const okBtn = document.createElement("button");
    okBtn.type = "button";
    okBtn.className = danger ? "btn btn-danger" : "btn btn-primary";
    okBtn.textContent = okText || (isPrompt ? "Valider" : type === "confirm" ? "Confirmer" : "OK");
    okBtn.onclick = confirmAction;
    actionsEl.appendChild(okBtn);

    _dialogCancelActive = () => close(cancelValue);

    document.addEventListener("keydown", onKeydown);
    backdrop.addEventListener("mousedown", onBackdropClick);

    backdrop.style.display = "flex";

    setTimeout(() => {
      if (isPrompt) { inputEl.focus(); inputEl.select(); }
      else okBtn.focus();
    }, 0);
  });
}

function showAlert(message, options = {}) {
  return _openDialog({ type: "alert", message, title: options.title, okText: options.okText, danger: options.danger });
}

function showConfirm(message, options = {}) {
  return _openDialog({
    type: "confirm",
    message,
    title: options.title,
    okText: options.okText,
    cancelText: options.cancelText,
    danger: options.danger
  });
}

function showPrompt(message, defaultValue = "", options = {}) {
  return _openDialog({
    type: "prompt",
    message,
    defaultValue,
    title: options.title,
    okText: options.okText,
    cancelText: options.cancelText
  });
}
