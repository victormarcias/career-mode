import { api } from './api.js'
import { escapeHtml, findCompany, setNotice, typeConflictText } from './dom-utils.js'
import { toISODate } from './dates.js'
import { t } from './i18n.js'

const FIELD_SPECS = [
  { key: 'name', label: 'edit.name', type: 'text', required: true },
  { key: 'notes', label: 'form.notes', type: 'textarea' },
  { key: 'website', label: 'companies.website', type: 'url' },
  { key: 'linkedin', label: 'edit.linkedin', type: 'url' },
  { key: 'applicationLink', label: 'edit.applicationLink', type: 'text' },
  { key: 'recruiters', label: 'form.recruiters', type: 'lines' },
]

// The labels are keys of the locale files (see i18n.js).
// Archives a company by logging an `archive` event (a closing event): a company is archived when its latest event
// closes the process, so logging it is the whole write.
export async function archiveCompany(id, notes) {
  await api.create('events', {
    date: toISODate(new Date()),
    event: 'archive',
    companyId: id,
    notes,
  })
}

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

// The type of the company, an Agency or a Client: it can change (an agency that is really an employer becomes a client).
function typeFieldHtml(companyType) {
  const option = (value, label) => `<option value="${value}"${companyType === value ? ' selected' : ''}>${t(label)}</option>`
  return `
    <div>
      <label for="edit-f-companyType" class="mb-1 block text-xs text-gray-500">${t('edit.companyType')}</label>
      <select id="edit-f-companyType" class="select-chevron w-full appearance-none rounded-lg border border-gray-700 bg-gray-800 py-2 pl-3 pr-9 text-sm text-gray-100">${option('agency', 'form.agency')}${option('client', 'form.client')}</select>
    </div>
  `
}

// Only for a client: the agency it came through, shown by its name and left empty for a direct client.
// `agency-list` is the same shared <datalist> the "+ Update" form uses.
function viaFieldHtml(viaName, companyType) {
  return `
    <div id="edit-f-via-wrap"${companyType === 'client' ? '' : ' class="hidden"'}>
      <label for="edit-f-via" class="mb-1 block text-xs text-gray-500">🤝 ${t('form.via')} <span class="text-gray-600">${t('edit.viaHint')}</span></label>
      <input type="text" id="edit-f-via" list="agency-list" autocomplete="off" value="${attr(viaName || '')}" class="w-full rounded-lg border border-gray-700 bg-gray-800 px-3 py-2 text-sm text-gray-100" />
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

function openForm(company, viaName, archived = false) {
  currentId = company.id
  currentName = company.name ?? ''
  document.getElementById('edit-form-title').textContent = t('edit.title')

  const parts = FIELD_SPECS.map((spec) => fieldHtml(spec, company[spec.key]))
  // The type and, for a client, its agency go right after the name.
  parts.splice(1, 0, typeFieldHtml(company.companyType), viaFieldHtml(viaName, company.companyType))
  document.getElementById('edit-form-fields').innerHTML = parts.join('')
  document.getElementById('edit-f-companyType').addEventListener('change', (e) => {
    document.getElementById('edit-f-via-wrap').classList.toggle('hidden', e.target.value !== 'client')
  })

  setNotice(document.getElementById('edit-form-error'), '')
  // Archive makes no sense on something that's already archived.
  document.getElementById('edit-form-archive').classList.toggle('hidden', archived)

  const overlay = document.getElementById('edit-overlay')
  const form = document.getElementById('edit-form')
  overlay.classList.remove('hidden')
  overlay.classList.add('flex')
  requestAnimationFrame(() => form.classList.add('is-open'))
}

export function openEntityEdit(company, viaName, archived = false) {
  openForm(company, viaName, archived)
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
      await archiveCompany(currentId, t('edit.archiveNote'))
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
      await api.remove('companies', currentId)
      closeEditForm()
    } catch (err) {
      showError(err)
    } finally {
      deleteBtn.disabled = false
    }
  })

  form.addEventListener('submit', async (e) => {
    e.preventDefault()
    const data = {}
    for (const spec of FIELD_SPECS) data[spec.key] = readField(spec)
    data.companyType = document.getElementById('edit-f-companyType').value

    setNotice(errorEl, '')
    submitBtn.disabled = true
    submitBtn.textContent = t('form.saving')

    try {
      // Only a client has an agency; left empty it is direct. The agency is found by name (ignoring case) and reused;
      // only one that doesn't exist is created, so a client never points at a missing agency.
      data.viaCompanyId = null
      const viaName = document.getElementById('edit-f-via').value.trim()
      if (data.companyType === 'client' && viaName) {
        const companies = await api.list('companies')
        const found = findCompany(companies, viaName)
        if (found && found.companyType !== 'agency') throw new Error(typeConflictText(viaName, found.companyType))
        data.viaCompanyId = found ? found.id : (await api.create('companies', { name: viaName, companyType: 'agency' })).id
      }

      // The server refuses a name that's already taken (ignoring case, agency or client) with a message to show.
      await api.patch('companies', currentId, data)
      closeEditForm()
    } catch (err) {
      showError(err)
    } finally {
      submitBtn.disabled = false
      submitBtn.textContent = t('common.save')
    }
  })
}
