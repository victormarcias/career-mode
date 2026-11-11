#!/usr/bin/env python3
"""Makes the demo's data: 50 invented companies (half with English names and notes, half Spanish) and their
events, as the two CSV files the app imports (calendar.csv and companies.csv).

    python demo/make_demo.py [DIR]      DIR defaults to demo/data

Everything is invented: the names, the people and the links (all under the reserved .example domain). The dates
are worked out from today, so every event falls in last week or this one, and this week has an event of every type.
Same day, same data: the random numbers are seeded, and the seed is the first one that gives every type this week.
"""
import csv
import datetime as dt
import os
import random
import re
import sys
import unicodedata

EVENT_TYPES = [
    'application', 'passive_message', 'note', 'tech_filter', 'hr_intro', 'tech_interview', 'culture_interview',
    'on_hold', 'offer', 'rejection', 'red_flag', 'archive', 'pending',
]
FUTURE_OK = {'hr_intro', 'tech_filter', 'tech_interview', 'culture_interview', 'pending'}  # the rest already happened

COMPANIES_PER_LANG = 25  # English + Spanish
AGENCIES = 18
CLIENTS = 32
WORKDAY_START_HOUR = 8
WORKDAY_END_HOUR = 19  # exclusive
SLOT_MINUTES = 30

# --- invented names -------------------------------------------------------------------------------------------

EN_FIRST = ['Brightwave', 'Northpine', 'Cobalt', 'Lumen', 'Harbor', 'Quill', 'Saffron', 'Tidal', 'Juniper', 'Granite',
            'Willow', 'Ember', 'Paper Moon', 'Foxglove', 'Atlas Fern', 'Blue Heron', 'Copperleaf', 'Driftwood',
            'Silverline', 'Maple Row', 'Starling', 'Oakridge', 'Pebble', 'Redwood Lane', 'Sunbeam', 'Thistle',
            'Wildflower', 'Zephyr', 'Marlow', 'Kestrel', 'Larkspur', 'Nimble', 'Orchard', 'Plover', 'Riverbend',
            'Skylark', 'Tamarind', 'Umber', 'Vesper', 'Yarrow', 'Anchor Point', 'Birchwood', 'Clearwater',
            'Dovetail', 'Elmstead', 'Fernhill', 'Goldfinch', 'Hollow Oak', 'Ironwood', 'Jasper Fields']
EN_LAST = ['Labs', 'Systems', 'Software', 'Digital', 'Works', 'Studio', 'Technologies', 'Cloud', 'Analytics',
           'Solutions', 'Interactive', 'Data', 'Robotics', 'Health', 'Logistics', 'Payments', 'Learning']
ES_FIRST = ['Cóndor', 'Pampa', 'Sol Naciente', 'Río Claro', 'Luna Nueva', 'Colibrí', 'Ceiba', 'Jacarandá', 'Quebracho',
            'Aguaribay', 'Tierra Firme', 'Estrella del Sur', 'Cerro Alto', 'Ombú', 'Lapacho', 'Andes Norte',
            'Mar Chiquita', 'Fogón', 'Mate Cocido', 'Tero', 'Zorzal', 'Algarrobo', 'Cuarzo', 'Horizonte Verde',
            'Brújula', 'Faro Azul', 'Molino', 'Naranjal', 'Olivar', 'Palo Santo', 'Raíces', 'Sendero', 'Tango Norte',
            'Valle Sereno', 'Yerba Viva', 'Aurora Boreal', 'Bosque Alto', 'Costa Dorada', 'Delta Sur', 'Espiga',
            'Glaciar', 'Huella', 'Isla Verde', 'Junco', 'Lomas', 'Mirador', 'Nube Blanca', 'Palmar', 'Quinua', 'Selva']
ES_LAST = ['Digital', 'Software', 'Tech', 'Sistemas', 'Soluciones', 'Labs', 'Consultores', 'Datos', 'Nube', 'Studio',
           'Innovación', 'Analítica', 'Salud', 'Logística', 'Pagos', 'Educación']

ROLES = ['Backend Developer', 'Full Stack Developer', 'Python Developer', 'Senior Software Engineer',
         'AI Engineer', 'Frontend Developer (React)', 'Platform Engineer', 'Data Engineer', 'Software Engineer',
         'Tech Lead', 'DevOps Engineer', 'Machine Learning Engineer']
FIRST_NAMES = ['Ana', 'Marcos', 'Julia', 'Tomás', 'Elena', 'Diego', 'Carla', 'Nicolás', 'Paula', 'Andrés', 'Marta',
               'Joaquín', 'Irene', 'Lucas', 'Sofía', 'Mateo', 'Clara', 'Bruno', 'Alicia', 'Hugo']
LAST_NAMES = ['Ferrer', 'Quiroga', 'Bellido', 'Montes', 'Sandoval', 'Ibarra', 'Roldán', 'Cabrera', 'Salvatierra',
              'Duarte', 'Lemos', 'Aranda', 'Peralta', 'Villar', 'Ledesma', 'Oyarzún', 'Barrera', 'Nogueira']
TITLES_EN = ['Talent Acquisition Partner', 'Technical Recruiter', 'Engineering Manager', 'HR Business Partner', 'Recruiting Lead']
TITLES_ES = ['Analista de Talento', 'Reclutadora IT', 'Gerente de Ingeniería', 'Responsable de RRHH', 'Líder de Selección']

NOTES = {
    'agency': {
        'en': ['Software consultancy that places engineers with U.S. and European product teams.',
               'Staffing agency for remote tech roles, with a focus on Latin America.',
               'Boutique recruiting firm for startups hiring backend and AI engineers.',
               'Nearshore development company: dedicated teams for companies abroad.',
               'IT recruiting agency with long-term contractor placements.'],
        'es': ['Consultora de software que ubica ingenieros en equipos de producto de EE. UU. y Europa.',
               'Agencia de selección para roles tecnológicos remotos, con foco en Latinoamérica.',
               'Consultora boutique de reclutamiento para startups que buscan perfiles backend y de IA.',
               'Empresa de desarrollo nearshore: equipos dedicados para compañías del exterior.',
               'Agencia de reclutamiento IT con ubicaciones de largo plazo como contractor.'],
    },
    'client': {
        'en': ['Fintech that offers payments and invoicing to small businesses.',
               'Healthcare startup building scheduling and billing tools for clinics.',
               'E-learning platform with live classes and AI tutors.',
               'Logistics software for last-mile delivery fleets.',
               'B2B marketplace for industrial supplies, remote-first.',
               'Climate-data company: satellite imagery and forecasting APIs.',
               'Developer-tools company, open-core, fully distributed team.'],
        'es': ['Fintech que ofrece pagos y facturación a pequeños comercios.',
               'Startup de salud que desarrolla herramientas de turnos y facturación para clínicas.',
               'Plataforma de educación online con clases en vivo y tutores con IA.',
               'Software de logística para flotas de entrega de última milla.',
               'Marketplace B2B de insumos industriales, remoto.',
               'Empresa de datos climáticos: imágenes satelitales y APIs de pronóstico.',
               'Empresa de herramientas para desarrolladores, equipo distribuido.'],
    },
}
PASSIVE = {
    'en': 'Passive contact on a platform from {who} ({title}). They saw the profile and propose a role as {role}. Replied that it is of interest, with the expected salary range.',
    'es': 'Contacto pasivo en una plataforma de {who} ({title}). Vio el perfil y propone un puesto de {role}. Se respondió que interesa, con el rango salarial esperado.',
}
INTERVIEW = {
    'hr_intro': {'en': 'Intro call with {who} ({title}) about the {role} role: the team, the process and the salary expectations.',
                 'es': 'Llamada inicial con {who} ({title}) por el puesto de {role}: el equipo, el proceso y las expectativas salariales.'},
    'tech_filter': {'en': 'Technical screening for {role}: a short coding exercise and questions about past projects.',
                    'es': 'Filtro técnico para {role}: un ejercicio corto de código y preguntas sobre proyectos anteriores.'},
    'tech_interview': {'en': 'Technical interview for {role} with two engineers: system design and a live coding session.',
                       'es': 'Entrevista técnica para {role} con dos ingenieros: diseño de sistemas y una sesión de código en vivo.'},
    'culture_interview': {'en': 'Culture interview for {role} with {who} ({title}): how the team works and what the first months look like.',
                          'es': 'Entrevista cultural para {role} con {who} ({title}): cómo trabaja el equipo y cómo son los primeros meses.'},
}
OUTCOME = {
    'rejection': {'en': ['Other candidates.', 'Other candidates.', 'They went with a profile closer to the stack.', 'The position was filled internally.'],
                  'es': ['Other candidates.', 'Other candidates.', 'Siguieron con un perfil más cercano al stack.', 'El puesto se cubrió internamente.']},
    'red_flag': {'en': ['The role is on-site five days a week, not remote.', 'Asks for a one-week unpaid take-home project.', 'Pays far below the expected range.'],
                 'es': ['El puesto es presencial cinco días por semana, no remoto.', 'Piden un proyecto de una semana sin paga.', 'Pagan muy por debajo del rango esperado.']},
    'on_hold': {'en': ['The company froze hiring until next quarter.', 'The team is reorganizing; they will write back.'],
                'es': ['La empresa congeló las contrataciones hasta el próximo trimestre.', 'El equipo se está reorganizando; avisarán.']},
    'offer': {'en': ['Offer received: contractor in USD, remote. Reviewing the terms.', 'Verbal offer, written one expected this week.'],
              'es': ['Oferta recibida: contractor en USD, remoto. Revisando las condiciones.', 'Oferta verbal; la escrita llega esta semana.']},
    'archive': {'en': ['No answer after the application; archived.', 'The posting was taken down.'],
                'es': ['Sin respuesta tras la postulación; archivada.', 'La publicación fue dada de baja.']},
    'note': {'en': ['Follow-up sent to the recruiter, waiting for news.', 'Asked for feedback on the last step.', 'Replied to the recruiter with the availability for next week.'],
             'es': ['Seguimiento enviado a la reclutadora, a la espera de novedades.', 'Se pidió feedback del último paso.', 'Se respondió al reclutador con la disponibilidad de la semana próxima.']},
}

# stages of one process: a list of event types, in order
TEMPLATES = [
    (22, ['application']),
    (14, ['application', 'rejection']),
    (8, ['application', 'hr_intro']),
    (7, ['application', 'hr_intro', 'tech_filter']),
    (6, ['application', 'hr_intro', 'tech_interview']),
    (5, ['application', 'hr_intro', 'tech_interview', 'culture_interview']),
    (4, ['application', 'hr_intro', 'tech_interview', 'culture_interview', 'offer']),
    (6, ['passive_message', 'note', 'hr_intro']),
    (4, ['passive_message', 'note']),
    (4, ['application', 'red_flag']),
    (4, ['application', 'on_hold']),
    (5, ['application', 'hr_intro', 'rejection']),
    (5, ['application', 'note']),
    (4, ['application', 'archive']),
    (5, ['pending']),
]


def slugify(text):
    text = unicodedata.normalize('NFD', text.lower().strip())
    text = ''.join(c for c in text if not unicodedata.combining(c))
    return re.sub(r'(^-|-$)', '', re.sub(r'[^a-z0-9]+', '-', text))


def person(rng, lang):
    return '%s %s' % (rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)), rng.choice(TITLES_ES if lang == 'es' else TITLES_EN)


def pick_time(rng, day_times, date_str, after=None):
    """Minutes-of-day for date_str, unused that day (slots are 30 minutes apart) and, if given, after `after`:
    so two stages of the same process sharing a date still show in the order they happened."""
    used = day_times.setdefault(date_str, [])
    slots = [h * 60 + m for h in range(WORKDAY_START_HOUR, WORKDAY_END_HOUR) for m in range(0, 60, SLOT_MINUTES)]
    if after is not None:
        slots = [s for s in slots if s > after]
    rng.shuffle(slots)
    chosen = next((s for s in slots if s not in used), None)
    if chosen is None:  # the day is full, or nothing is free after `after`: double up rather than fail
        chosen = slots[0] if slots else after + SLOT_MINUTES
    used.append(chosen)
    return chosen


def build(today, seed):
    rng = random.Random(seed)
    # --- companies: COMPANIES_PER_LANG English, COMPANIES_PER_LANG Spanish; AGENCIES agencies, CLIENTS clients,
    # a third of the clients through an agency
    names = []
    for first, last, lang in ((EN_FIRST, EN_LAST, 'en'), (ES_FIRST, ES_LAST, 'es')):
        picks = rng.sample(first, COMPANIES_PER_LANG)
        names += [('%s %s' % (picks[i], rng.choice(last)), lang) for i in range(COMPANIES_PER_LANG)]
    rng.shuffle(names)
    kinds = ['agency'] * AGENCIES + ['client'] * CLIENTS
    rng.shuffle(kinds)
    companies = []
    for (name, lang), kind in zip(names, kinds):
        slug = slugify(name)
        recruiters = []
        for _ in range(rng.choice([0, 0, 1, 1, 2])):
            who, _title = person(rng, lang)
            recruiters.append('https://linkedin.example/in/%s' % slugify(who) + '-' + str(rng.randint(100, 999)))
        companies.append({
            'id': slug, 'name': name, 'lang': lang, 'type': kind, 'via': '',
            'website': 'https://www.%s.example' % slug, 'linkedin': 'https://linkedin.example/company/%s' % slug,
            'recruiters': recruiters, 'application_link': 'https://jobs.%s.example' % slug if rng.random() < 0.5 else '',
            'notes': rng.choice(NOTES[kind][lang]),
        })
    agencies = [c for c in companies if c['type'] == 'agency']
    for c in companies:
        if c['type'] == 'client' and rng.random() < 0.35:
            c['via'] = rng.choice(agencies)['id']

    # --- events: every company has one process, started last week or this one
    week_start = today - dt.timedelta(days=today.weekday() + 7)  # last Monday
    t = (today - week_start).days  # today, counted from last Monday (7 to 13)
    weights = [w for w, _ in TEMPLATES]
    events = []
    day_times = {}
    for c in companies:
        stages = rng.choices([s for _, s in TEMPLATES], weights)[0]
        lang = c['lang']
        who, title = person(rng, lang)
        role = rng.choice(ROLES)
        day = rng.randint(t - 2, t) if stages == ['pending'] else rng.randint(0, max(0, t - len(stages)))
        prev_date, prev_minutes = None, None
        for i, kind in enumerate(stages):
            if i:
                day += rng.randint(1, 3)
            is_last = i == len(stages) - 1
            d = day if (kind in FUTURE_OK and is_last) else min(day, t)
            d = min(d, 13)
            date_str = (week_start + dt.timedelta(days=d)).isoformat()
            if kind == 'pending':
                at = None
            else:
                # if this stage clamped onto the same day as the previous one, keep it later than it
                after = prev_minutes if date_str == prev_date else None
                minutes = pick_time(rng, day_times, date_str, after)
                at = '%02d:%02d' % divmod(minutes, 60)
                prev_date, prev_minutes = date_str, minutes
            link, apply_type, notes = '', '', ''
            if kind in ('application', 'pending'):
                if rng.random() < 0.25 and kind == 'application':
                    link, apply_type = 'careers@%s.example' % c['id'], 'email_apply'
                else:
                    link = 'https://jobs.%s.example/%s' % (c['id'], rng.randint(1000, 9999))
                    apply_type = 'web_form' if kind == 'application' else ''
                notes = ('Recruiter: %s (%s). Position: %s.' % (who, title, role)) if lang == 'en' else \
                        ('Reclutador/a: %s (%s). Puesto: %s.' % (who, title, role))
                if kind == 'pending':
                    notes = ('Queued link. Position: %s.' if lang == 'en' else 'Enlace en cola. Puesto: %s.') % role
            elif kind == 'passive_message':
                notes = PASSIVE[lang].format(who=who, title=title, role=role)
            elif kind in INTERVIEW:
                notes = INTERVIEW[kind][lang].format(who=who, title=title, role=role)
            else:
                notes = rng.choice(OUTCOME[kind][lang])
            events.append({
                'id': '%020x' % rng.getrandbits(80), 'date': date_str, 'time': at or '',
                'type': kind, 'company': c, 'apply_type': apply_type, 'jd_url': link, 'notes': notes,
            })
    return companies, events


def this_week_types(today, events):
    monday = today - dt.timedelta(days=today.weekday())
    sunday = monday + dt.timedelta(days=6)
    return {e['type'] for e in events if monday.isoformat() <= e['date'] <= sunday.isoformat()}


def well_spaced(events):
    """Whether every same-day pair of timed events is at least 30 minutes apart."""
    by_day = {}
    for e in events:
        if e['time']:
            by_day.setdefault(e['date'], []).append(int(e['time'][:2]) * 60 + int(e['time'][3:]))
    return all(b - a >= 30 for times in by_day.values() for a, b in zip(sorted(times), sorted(times)[1:]))


def write(directory, companies, events):
    os.makedirs(directory, exist_ok=True)
    with open(os.path.join(directory, 'companies.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['company_type', 'id', 'name', 'status', 'via_company_id', 'website', 'linkedin', 'recruiters', 'application_link', 'notes'])
        for c in sorted(companies, key=lambda c: c['name'].lower()):
            w.writerow([c['type'], c['id'], c['name'], '', c['via'], c['website'], c['linkedin'], ' | '.join(c['recruiters']), c['application_link'], c['notes']])
    with open(os.path.join(directory, 'calendar.csv'), 'w', encoding='utf-8', newline='') as f:
        w = csv.writer(f, lineterminator='\n')
        w.writerow(['id', 'date', 'time', 'event', 'company', 'apply_type', 'calendar_event_id', 'company_id', 'via_company_id', 'jd_url', 'notes'])
        for e in sorted(events, key=lambda e: (e['date'], e['time'])):
            c = e['company']
            w.writerow([e['id'], e['date'], e['time'], e['type'], c['name'], e['apply_type'], '', c['id'], c['via'], e['jd_url'], e['notes']])


def main():
    directory = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(os.path.abspath(__file__)), 'data')
    today = dt.date.today()
    for seed in range(1, 500):  # the first seed that puts every event type in this week
        companies, events = build(today, seed)
        if this_week_types(today, events) >= set(EVENT_TYPES) and well_spaced(events):
            break
    else:
        sys.exit('No seed put every event type in this week, 30 minutes apart.')
    write(directory, companies, events)
    print('Demo data for %s (seed %d): %d companies, %d events, in %s' % (today, seed, len(companies), len(events), directory))


if __name__ == '__main__':
    main()
