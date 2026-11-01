// Small enhancements on top of plain Django pages. Everything still works
// without this file: popups open from links like ?modal=share, and every
// action is a normal form post.

// ---------- Popups ----------
const focusable = 'input:not([type=hidden]), select, textarea, button, a[href]'

function openModal(name) {
  const modal = document.querySelector(`[data-modal="${name}"]`)
  if (!modal) return false
  modal.hidden = false
  modal._opener = document.activeElement
  modal.querySelector('.modal-body ' + focusable)?.focus()
  return true
}

function closeModal(modal) {
  modal.hidden = true
  modal._opener?.focus()
  // Drop ?modal=, ?request= or ?accept= so a refresh doesn't reopen it.
  const url = new URL(window.location)
  ;['modal', 'request', 'accept'].forEach((key) => url.searchParams.delete(key))
  history.replaceState(null, '', url)
}

document.addEventListener('click', (e) => {
  const opener = e.target.closest('[data-open]')
  if (opener && openModal(opener.dataset.open)) {
    e.preventDefault()
    return
  }
  const closer = e.target.closest('[data-close]')
  if (closer) {
    e.preventDefault()
    closeModal(closer.closest('[data-modal]'))
  }
})

// Clicking the dark backdrop (not the popup itself) closes it.
document.addEventListener('mousedown', (e) => {
  if (e.target.matches('[data-modal]')) closeModal(e.target)
})

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const open = document.querySelector('[data-modal]:not([hidden])')
    if (open) closeModal(open)
    document.querySelectorAll('details.menu[open]').forEach((m) => m.removeAttribute('open'))
  }
  // Keep Tab inside an open popup.
  if (e.key === 'Tab') {
    const open = document.querySelector('[data-modal]:not([hidden]) .modal')
    if (!open) return
    const items = [...open.querySelectorAll(focusable)].filter((el) => !el.disabled && el.offsetParent)
    const first = items[0]
    const last = items[items.length - 1]
    if (e.shiftKey && document.activeElement === first) {
      last.focus()
      e.preventDefault()
    } else if (!e.shiftKey && document.activeElement === last) {
      first.focus()
      e.preventDefault()
    }
  }
})

// A popup the server opened (form errors, ?accept=...) gets focus on load.
const serverOpened = document.querySelector('[data-modal]:not([hidden])')
serverOpened?.querySelector('.modal-body ' + focusable)?.focus()

// ---------- "..." menus ----------
// Only one open at a time; clicking anywhere else closes it.
document.addEventListener('click', (e) => {
  document.querySelectorAll('details.menu[open]').forEach((menu) => {
    if (!menu.contains(e.target)) menu.removeAttribute('open')
  })
})

// ---------- Show more ----------
document.querySelectorAll('[data-show-more]').forEach((button) => {
  const list = document.getElementById(button.dataset.showMore)
  const label = button.querySelector('[data-label]')
  button.addEventListener('click', () => {
    const expanded = list.classList.toggle('is-expanded')
    button.setAttribute('aria-expanded', expanded)
    button.classList.toggle('is-flipped', expanded)
    label.textContent = expanded ? 'Show less' : button.dataset.moreLabel
  })
})

// ---------- Request form: condition hint and note counter ----------
document.querySelectorAll('[data-condition]').forEach((card) => {
  const select = card.querySelector('select')
  select.addEventListener('change', () => {
    card.querySelector('[data-condition-pill]').textContent = select.value
    card.querySelectorAll('[data-hint]').forEach((hint) => (hint.hidden = hint.dataset.hint !== select.value))
  })
})

document.querySelectorAll('[data-count-for]').forEach((counter) => {
  const field = document.getElementById(counter.dataset.countFor)
  field?.addEventListener('input', () => (counter.textContent = field.value.length))
})

// ---------- Password show / hide ----------
document.querySelectorAll('[data-toggle-password]').forEach((button) => {
  const input = button.parentElement.querySelector('[data-password]')
  button.addEventListener('click', () => {
    const show = input.type === 'password'
    input.type = show ? 'text' : 'password'
    button.setAttribute('aria-pressed', show)
    button.setAttribute('aria-label', show ? 'Hide password' : 'Show password')
    button.querySelector('[data-eye]').hidden = show
    button.querySelector('[data-eye-off]').hidden = !show
  })
})

// ---------- Sign-up password rules ----------
// The server checks the same rules; these chips just show progress while typing.
document.querySelectorAll('[data-password-rules]').forEach((rules) => {
  const form = rules.closest('form')
  const password = form.querySelector('[data-password-role="new"]')
  const confirm = form.querySelector('[data-password-role="confirm"]')
  const checks = {
    length: () => password.value.length >= 8,
    mix: () => /[A-Za-z]/.test(password.value) && /\d/.test(password.value),
    match: () => password.value !== '' && password.value === confirm.value,
  }
  const update = () =>
    rules.querySelectorAll('[data-rule]').forEach((rule) => rule.classList.toggle('is-good', checks[rule.dataset.rule]()))
  password.addEventListener('input', update)
  confirm.addEventListener('input', update)
  update()
})

// ---------- Toasts fade out ----------
document.querySelectorAll('[data-toast]').forEach((toast) => setTimeout(() => toast.remove(), 2600))
