// The Recruiters field of the event form reads the leading `Recruiter:` lines of an event's notes: each holds one
// recruiter, as a LinkedIn profile, an email or just a name. A line with more than that (a name and notes) stays
// in the notes, so it is never lost on save.
import { test } from 'node:test'
import assert from 'node:assert/strict'
import { buildNotes, isRecruiter, parseRecruiters, splitRecruiters } from '../../public/js/application-form.js'

test('a recruiter is a LinkedIn profile, an email or a name', () => {
  for (const ok of ['https://www.linkedin.com/in/ana-example/', 'linkedin.com/in/ana-example', 'ana@example.com', 'Ana Example', "María O'Example-Pérez"]) {
    assert.ok(isRecruiter(ok), ok)
  }
  for (const bad of ['Ana Example (author of the post). Position: Python Developer.', 'https://www.linkedin.com/company/example']) {
    assert.ok(!isRecruiter(bad), bad)
  }
})

test('a Recruiter: line with a profile, an email or a name goes to the Recruiters field', () => {
  const { recruiters, rest } = splitRecruiters('Recruiter: https://www.linkedin.com/in/ana-example/\nRecruiter: bob@example.com\nRecruiter: Carla Example\nApplied by email.')
  assert.deepEqual(recruiters, ['https://www.linkedin.com/in/ana-example/', 'bob@example.com', 'Carla Example'])
  assert.equal(rest, 'Applied by email.')
})

test('a Recruiter: line with a name and notes stays in the notes', () => {
  const notes = 'Recruiter: Ana Example (author of the post). Position: Python Developer.\nApplied by email.'
  const { recruiters, rest } = splitRecruiters(notes)
  assert.deepEqual(recruiters, [])
  assert.equal(rest, notes)
})

test('editing and saving keeps every Recruiter: line', () => {
  const notes = 'Recruiter: https://www.linkedin.com/in/ana-example/\nRecruiter: Bob Example\nRecruiter: Bob Example (author of the post).\nSent.'
  const { recruiters, rest } = splitRecruiters(notes)
  assert.equal(buildNotes(parseRecruiters(recruiters.join('\n')), rest), notes)
})
