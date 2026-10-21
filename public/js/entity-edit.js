import { api } from './api.js'
import { escapeHtml, resolveCompany, setNotice } from './dom-utils.js'
import { toISODate } from './dates.js'
import { t } from './i18n.js'

const COLLECTION = { agency: 'agencies', client: 'clients' }

const FIELD_SPECS = {
  agency: [
    { key: 'name', label: 'edit.name', type: 'text', required: true },
    { key: 'type', label: 'edit.type', type: 'text' },
    { key: 'website', label: 'companies.website', type: 'url' },
    { key: 'linkedin', label: 'edit.linkedin', type: 'url' },
    { key: 'applicationLink', label: 'edit.applicationLink', type: 'text' },
    { key: 'recruiters', label: 'form.recruiters', type: 'lines' },
  ],
  client: [
    { key: 'name', label: 'edit.name', type: 'text', required: true },
    { key: 'website', label: 'companies.website', type: 'url' },
    { key: 'linkedin', label: 'edit.linkedin', type: 'url' },
    { key: 'notes', label: 'form.notes', type: 'textarea' },
  ],
}

// The labels are keys of the locale files (see i18n.js).
// Archives an agency or a client by logging an `archive` event (a closing event).
// The server archives the agency when it sees one; a client's Archived state is
// derived from that event being its latest, so logging it is the whole write.
export async function archiveCompany(kind, id, notes) {
  await api.create('events', {
    date: toISODate(new Date()),
    event: 'archive',
    agencyId: kind === 'agency' ? id : null,
    clientId: kind === 'client' ? id : null,
    notes,
  })
}

let currentKind = null
let currentId = null // the company being edited
let currentName = ''

function attr(value) {
  return escapeHtml(value).replace(/"/g, '&quot;')
}

function fieldHtml(spec, value) {
  const id = `edit-f-${spec.key}`
  if (spec.type === 'checkbox') {
    return `
      <label class="flex items-center gap-2 text-sm text-gray-300">
        <input type="checkbox" id="${id}" ${value ? 'checked' : ''} class="h-4 w-4 rounded border-gray-700 bg-gray-800" />
        ${t(spec.label)}
      </label>
    `
  }
  if (spec.type === 'textarea' || spec.type === 'lines') {
    const text = spec.type === 'lines' ? (value || []).join('\n') : value || ''
    const rows = spec.type === 'lines' ? 3 : 6
    return `
      <div>
        <label class="mb-1 block text-xs text-gray-500">${t(spec.label)}</label>
        <textarea id="${id}" rows="${rows}" class="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100">${escapeHtml(text)}</textarea>
      </div>
    `
  }
  return `
    <div>
      <label class="mb-1 block text-xs text-gray-500">${t(spec.label)}${spec.required ? ' <span class="req">*</span>' : ''}</label>
      <input type="${spec.type}" id="${id}" value="${attr(value || '')}" class="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100"${spec.required ? ' required' : ''} />
    </div>
  `
}

// Only for clients — agencies can never be "via" another agency. Rendered
// separately from FIELD_SPECS since it is the viaAgencyId field, shown as
// an agency name: left empty, the client is direct (no agency).
// `agency-list` is the same shared <datalist> the "+ Update" form uses.
function viaAgencyFieldHtml(viaAgencyName) {
  return `
    <div>
      <label for="edit-f-via-agency" class="mb-1 block text-xs text-gray-500">🤝 ${t('form.agency')} <span class="text-gray-600">${t('edit.viaAgencyHint')}</span></label>
      <input type="text" id="edit-f-via-agency" list="agency-list" autocomplete="off" value="${attr(viaAgencyName || '')}" class="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100" />
    </div>
  `
}

function readField(spec) {
  const el = document.getElementById(`edit-f-${spec.key}`)
  if (spec.type === 'checkbox') return el.checked
  if (spec.type === 'lines') {
    return el.value
      .split('\n')
      .map((s) => s.trim())
      .filter(Boolean)
  }
  return el.value.trim()
}

function closeEditForm() {
  const overlay = document.getElementById('edit-overlay')
  const form = document.getElementById('edit-form')
  form.classList.remove('is-open')
  setTimeout(() => {
    overlay.classList.add('hidden')
    overlay.classList.remove('flex')
  }, 150)
}

function openForm(kind, id, entity, title, viaAgencyName, archived = false) {
  currentKind = kind
  currentId = id
  currentName = entity.name ?? ''
  document.getElementById('edit-form-title').textContent = title

  const parts = FIELD_SPECS[kind].map((spec) => fieldHtml(spec, entity[spec.key]))
  // A client's agency goes right after its name.
  if (kind === 'client') parts.splice(1, 0, viaAgencyFieldHtml(viaAgencyName))
  document.getElementById('edit-form-fields').innerHTML = parts.join('')

  setNotice(document.getElementById('edit-form-error'), '')
  // Archive makes no sense on something that's already archived.
  document.getElementById('edit-form-archive').classList.toggle('hidden', archived)

  const overlay = document.getElementById('edit-overlay')
  const form = document.getElementById('edit-form')
  overlay.classList.remove('hidden')
  overlay.classList.add('flex')
  requestAnimationFrame(() => form.classList.add('is-open'))
}

export function openEntityEdit(kind, id, entity, viaAgencyName, archived = false) {
  openForm(kind, id, entity, t(kind === 'agency' ? 'edit.titleAgency' : 'edit.titleClient'), viaAgencyName, archived)
}

export function initEntityEditForm() {
  const overlay = document.getElementById('edit-overlay')
  const form = document.getElementById('edit-form')
  const cancelBtn = document.getElementById('edit-form-cancel')
  const deleteBtn = document.getElementById('edit-form-delete')
  const archiveBtn = document.getElementById('edit-form-archive')
  const submitBtn = document.getElementById('edit-form-submit')
  const errorEl = document.getElementById('edit-form-error')

  cancelBtn.addEventListener('click', closeEditForm)
  overlay.addEventListener('click', (e) => {
    if (e.target === overlay) closeEditForm()
  })

  const showError = (err) => {
    setNotice(errorEl, err.message)
  }

  archiveBtn.addEventListener('click', async () => {
    if (!confirm(t('edit.confirmArchive', { name: currentName }))) return

    setNotice(errorEl, '')
    archiveBtn.disabled = true
    try {
      await archiveCompany(currentKind, currentId, t('edit.archiveNote'))
      closeEditForm()
    } catch (err) {
      showError(err)
    } finally {
      archiveBtn.disabled = false
    }
  })

  deleteBtn.addEventListener('click', async () => {
    const ok = confirm(t('edit.confirmDelete', { name: currentName }))
    if (!ok) return

    setNotice(errorEl, '')
    deleteBtn.disabled = true
    try {
      // The server refuses while the company still has events, and says how many.
      await api.remove(COLLECTION[currentKind], currentId)
      closeEditForm()
    } catch (err) {
      showError(err)
    } finally {
      deleteBtn.disabled = false
    }
  })

  form.addEventListener('submit', async (e) => {
    e.preventDefault()
    const specs = FIELD_SPECS[currentKind]
    const data = {}
    for (const spec of specs) data[spec.key] = readField(spec)

    setNotice(errorEl, '')
    submitBtn.disabled = true
    submitBtn.textContent = t('form.saving')

    try {
      if (currentKind === 'client') {
        const agencyName = document.getElementById('edit-f-via-agency').value.trim()
        if (!agencyName) {
          data.viaAgencyId = null
        } else {
          // Find the agency by name (ignoring case) and reuse it; only create one
          // that doesn't exist, so a client never points at a missing agency.
          const agency = resolveCompany(await api.list('agencies'), agencyName)
          data.viaAgencyId = agency.isNew ? (await api.create('agencies', { name: agency.name })).id : agency.id
        }
      }

      // The server refuses a name that's already taken (ignoring case) with a message to show.
      await api.patch(COLLECTION[currentKind], currentId, data)
      closeEditForm()
    } catch (err) {
      showError(err)
    } finally {
      submitBtn.disabled = false
      submitBtn.textContent = t('common.save')
    }
  })
}
