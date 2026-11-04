const focusable = 'input:not([type=hidden]), select, textarea, button, a[href]'

function openModal(name) {
  const modal = document.querySelector(`[data-modal="${name}"]`)
  if (!modal) return false
  modal.hidden = false
  modal._opener = document.activeElement
  document.querySelectorAll('details.menu[open]').forEach((menu) => menu.removeAttribute('open'))
  ;(modal.querySelector('[data-autofocus]') || modal.querySelector('.modal-body ' + focusable))?.focus()
  return true
}

function closeModal(modal) {
  modal.hidden = true
  modal.querySelector('[data-profile-form]')?.reset()
  modal._opener?.focus()
  const url = new URL(window.location)
  ;['modal', 'request', 'accept'].forEach((key) => url.searchParams.delete(key))
  history.replaceState(null, '', url)
}

document.addEventListener('click', (e) => {
  const opener = e.target.closest('[data-open]')
  if (opener) {
    const current = opener.closest('[data-modal]')
    const returnTo = current?._opener
    if (document.querySelector(`[data-modal="${opener.dataset.open}"]`)) {
      if (current) current.hidden = true
      openModal(opener.dataset.open)
      if (current) document.querySelector(`[data-modal="${opener.dataset.open}"]`)._opener = returnTo
      e.preventDefault()
      return
    }
  }
  const closer = e.target.closest('[data-close]')
  if (closer) {
    e.preventDefault()
    closeModal(closer.closest('[data-modal]'))
  }
})

document.addEventListener('mousedown', (e) => {
  if (e.target.matches('[data-modal]')) closeModal(e.target)
})

document.addEventListener('keydown', (e) => {
  if (e.key === 'Escape') {
    const open = document.querySelector('[data-modal]:not([hidden])')
    if (open) closeModal(open)
    document.querySelectorAll('details.menu[open]').forEach((m) => m.removeAttribute('open'))
  }
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

const serverOpened = document.querySelector('[data-modal]:not([hidden])')
;(serverOpened?.querySelector('[data-autofocus]') || serverOpened?.querySelector('.modal-body ' + focusable))?.focus()

document.addEventListener('click', (e) => {
  document.querySelectorAll('details.menu[open]').forEach((menu) => {
    if (!menu.contains(e.target)) menu.removeAttribute('open')
  })
})

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

document.querySelectorAll('[data-share-form]').forEach((form) => {
  const lendBox = form.querySelector('[data-lend-only]')
  const update = () => (lendBox.hidden = form.querySelector('[data-listing]:checked')?.value !== 'lend')
  form.querySelectorAll('[data-listing]').forEach((radio) => radio.addEventListener('change', update))
  update()
})

document.querySelectorAll('[data-qty-input]').forEach((box) => {
  const input = box.querySelector('input')
  box.querySelectorAll('[data-step]').forEach((button) =>
    button.addEventListener('click', () => {
      const next = (Number(input.value) || 1) + Number(button.dataset.step)
      input.value = Math.min(Number(input.max), Math.max(Number(input.min), next))
    }),
  )
})

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

const MAX_AVATAR_BYTES = 2 * 1024 * 1024

document.querySelectorAll('[data-avatar-picker]').forEach((picker) => {
  const form = picker.closest('form')
  const input = picker.querySelector('[data-avatar-input]')
  const preview = picker.querySelector('[data-avatar-preview]')
  const removeLabel = picker.querySelector('[data-avatar-remove]')
  const clear = removeLabel.querySelector('input')
  const error = picker.querySelector('[data-avatar-error]')
  const initials = picker.querySelector('[data-avatar-initials]').innerHTML.trim()
  const saved = { html: preview.innerHTML, canRemove: !removeLabel.hidden }
  let objectUrl = null

  const showImage = (url) => {
    preview.replaceChildren()
    if (url) {
      const img = document.createElement('img')
      img.src = url
      img.alt = ''
      preview.append(img)
    } else {
      preview.textContent = initials
    }
  }
  const forgetUpload = () => {
    if (objectUrl) URL.revokeObjectURL(objectUrl)
    objectUrl = null
  }
  const fail = (message) => {
    input.value = ''
    error.textContent = message
    error.hidden = false
  }

  input.addEventListener('change', () => {
    const file = input.files[0]
    error.hidden = true
    if (!file) return
    if (!['image/jpeg', 'image/png'].includes(file.type)) return fail('Please choose a JPG or PNG image.')
    if (file.size > MAX_AVATAR_BYTES) return fail('That photo is over 2MB. Please choose a smaller one.')
    forgetUpload()
    objectUrl = URL.createObjectURL(file)
    showImage(objectUrl)
    clear.checked = false
    removeLabel.hidden = false
  })

  clear.addEventListener('change', () => {
    if (!clear.checked) return
    input.value = ''
    forgetUpload()
    showImage(null)
    error.hidden = true
    removeLabel.hidden = true
  })

  form.addEventListener('reset', () =>
    setTimeout(() => {
      forgetUpload()
      preview.innerHTML = saved.html
      removeLabel.hidden = !saved.canRemove
      error.hidden = true
      form.querySelectorAll('textarea, input').forEach((field) => field.dispatchEvent(new Event('input')))
    }),
  )
})

document.querySelectorAll('[data-toast]').forEach((toast) => setTimeout(() => toast.remove(), 2600))
