import math
import random
import unicodedata
from collections import defaultdict
from datetime import datetime, time, timedelta

import psycopg2
from psycopg2.extras import execute_values
from faker import Faker

# ============================================================================
# KONFIGURACJA
# ============================================================================

RANDOM_SEED = 42

DB_CONFIG = {
    'dbname': 'ursus',
    'user': 'postgres',
    'password': 'root',
    'host': 'localhost',
    'port': '5432',
}

CURRENT_YEAR = 2026

# --- infrastruktura ---
TOTAL_BUILDINGS = 20
TOTAL_ROOMS = 500
ROOM_CAPACITY_SMALL_MIN = 20
ROOM_CAPACITY_SMALL_MAX = 60
ROOM_CAPACITY_BIG_MIN = 180
ROOM_CAPACITY_BIG_MAX = 300
BIG_ROOM_RATIO = 0.25  # tyle sal to aule na wykłady

# --- kadra ---
TOTAL_TEACHERS = 2000
TYTULY_NAUKOWE = ['mgr inż.', 'mgr', 'dr inż.', 'dr', 'dr hab. inż.', 'dr hab.', 'prof. dr hab. inż.']

# --- studenci / kierunki ---
STUDENTS_PER_ROCZNIK_MIN = 50
STUDENTS_PER_ROCZNIK_MAX = 150
DOUBLE_KIERUNEK_RATIO = 0.01

I_STOPIEN_ACTIVE_ROCZNIKI = 4     # 7 sem -> bierzemy 4 ostatnie roczniki
II_STOPIEN_ACTIVE_ROCZNIKI = 2    # 3-4 sem -> 2 roczniki

ALBUM_RANGE_START = 200_000
ALBUM_RANGE_END = 500_000

# --- program nauczania ---
BLOCKS_OBLIG_PER_KIERUNEK = 8
BLOCKS_ELECTIVE_PER_KIERUNEK = 2
PRZEDMIOTY_PER_ELECTIVE_BLOCK_MIN = 2
PRZEDMIOTY_PER_ELECTIVE_BLOCK_MAX = 3
ECTS_PER_PRZEDMIOT = 3  # 8*3 + 2*3 = 30 ECTS / semestr (student realizuje 1 przedmiot z bloku wybieralnego)
ECTS_WF = 1
ECTS_LEKTORAT = 2

# --- zajęcia / grupy ---
LECTURE_HOURS_PER_WEEK = 2
LAB_HOURS_PER_WEEK = 2
CLASS_DURATION_MINUTES = 90

LAB_GROUP_CAPACITY = 18
CAPACITY_SLACK_RATIO = 1.10

TIME_SLOTS_START = [(7, 30), (9, 15), (11, 15), (13, 15), (15, 15), (17, 5)]
DNI_DYDAKTYCZNE = ['PN', 'WT', 'ŚR', 'CZ', 'PT']

# --- WF + języki (ogólnouczelniane) ---
WF_BLOCKS_COUNT = 2
LANG_BLOCKS_COUNT = 2
OGOLNE_GROUPS_PER_ZAJECIA = 200
OGOLNE_GROUP_CAPACITY = 200

# --- tury ---
TURY_KIERUNKOWE_NAMES = ['Główna', 'Korekcyjna', 'Dogrywka']
TURA_DURATION_DAYS = 7
TURA_GAP_DAYS = 10
TURA_BASE_DATETIME = datetime(CURRENT_YEAR, 3, 15, 9, 0)

# --- wsad do bazy ---
BATCH_SIZE = 5000

# ============================================================================
# SŁOWNIKI DZIEDZINOWE
# ============================================================================

STOPIEN_CODE = {
    'I - Inżynierskie': 'INZ',
    'I - Licencjackie': 'LIC',
    'II - Magisterskie': 'MGR',
    'III - Doktoranckie': 'DOK',
}

PROGRAMS = [
    ("IST", "Informatyka Stosowana",     ['I - Inżynierskie', 'II - Magisterskie']),
    ("INA", "Informatyka Algorytmiczna", ['I - Licencjackie', 'II - Magisterskie']),
    ("SZI", "Sztuczna Inteligencja",     ['I - Inżynierskie', 'II - Magisterskie']),
    ("CBE", "Cyberbezpieczeństwo",       ['I - Inżynierskie', 'II - Magisterskie']),
    ("AIR", "Automatyka i Robotyka",     ['I - Inżynierskie', 'II - Magisterskie']),
    ("ELK", "Elektronika",               ['I - Inżynierskie']),
    ("TEL", "Telekomunikacja",           ['I - Inżynierskie']),
    ("MCH", "Mechatronika",              ['I - Inżynierskie', 'II - Magisterskie']),
    ("BUD", "Budownictwo",               ['I - Inżynierskie', 'II - Magisterskie']),
    ("ARC", "Architektura",              ['I - Inżynierskie', 'II - Magisterskie']),
    ("ZAR", "Zarządzanie",               ['I - Licencjackie', 'II - Magisterskie']),
    ("IBM", "Inżynieria Biomedyczna",    ['I - Inżynierskie']),
    ("MAT", "Matematyka Stosowana",      ['I - Licencjackie', 'II - Magisterskie']),
    ("FTE", "Fizyka Techniczna",         ['I - Inżynierskie']),
    ("CHE", "Chemia",                    ['I - Inżynierskie']),
    ("ISR", "Inżynieria Środowiska",     ['I - Inżynierskie']),
    ("ENE", "Energetyka",                ['I - Inżynierskie', 'II - Magisterskie']),
    ("MBM", "Mechanika i Budowa Maszyn", ['I - Inżynierskie', 'II - Magisterskie']),
    ("GEO", "Geodezja",                  ['I - Inżynierskie']),
    ("IMT", "Inżynieria Materiałowa",    ['I - Inżynierskie']),
]

BUILDING_CODES = [
    'A-1', 'B-1', 'B-4', 'C-1', 'C-3', 'C-4', 'C-6', 'C-7', 'C-11', 'C-13',
    'C-14', 'C-16', 'D-1', 'D-2', 'D-20', 'H-3', 'M-2', 'P-4', 'W-4', 'W-5',
]

BUILDING_NAMES = {
    'A-1': 'Gmach Główny',
    'C-13': 'Zintegrowane Centrum Studenckie',
    'D-1': 'Wydział Elektroniki',
    'D-2': 'Wydział Informatyki',
    'B-1': 'Budynek Matematyki',
    'B-4': 'Centrum Dydaktyczno-Badawcze',
    'W-4': 'Wydział Mechaniczny',
}

COURSE_NAME_POOL = [
    "Analiza Matematyczna", "Algebra Liniowa", "Matematyka Dyskretna",
    "Rachunek Prawdopodobieństwa", "Statystyka Matematyczna", "Metody Numeryczne",
    "Fizyka", "Fizyka Kwantowa", "Mechanika Techniczna", "Termodynamika",
    "Chemia Ogólna", "Chemia Organiczna", "Materiałoznawstwo",
    "Programowanie Strukturalne", "Programowanie Obiektowe",
    "Algorytmy i Struktury Danych", "Bazy Danych", "Systemy Operacyjne",
    "Sieci Komputerowe", "Architektura Komputerów", "Inżynieria Oprogramowania",
    "Teoria Obliczeń", "Kompilatory", "Logika dla Informatyków",
    "Podstawy Elektroniki", "Układy Cyfrowe", "Automatyka i Sterowanie",
    "Zarządzanie Projektami", "Mikroekonomia", "Prawo Gospodarcze",
    "Mechanika Płynów", "Wytrzymałość Materiałów", "Grafika Inżynierska",
    "Podstawy Konstrukcji Maszyn", "Metodologia Badań Naukowych",
    "Seminarium Dyplomowe", "Etyka Zawodowa",
]

ELECTIVE_COURSE_NAME_POOL = [
    "Uczenie Maszynowe", "Głębokie Sieci Neuronowe", "Wizja Komputerowa",
    "Przetwarzanie Języka Naturalnego", "Systemy Rekomendacyjne",
    "Programowanie Funkcyjne", "Programowanie Równoległe", "Programowanie Mobilne",
    "Grafika Komputerowa", "Tworzenie Gier Komputerowych",
    "DevOps i CI/CD", "Cloud Computing", "Bezpieczeństwo Systemów",
    "Kryptografia Stosowana", "Technologie Blockchain",
    "Internet Rzeczy", "Robotyka Mobilna", "Systemy Wbudowane",
    "Analiza Danych", "Wizualizacja Danych", "Hurtownie Danych",
    "Technologie Webowe", "Aplikacje Enterprise", "Testowanie Oprogramowania",
]

LANG_NAMES = ['Język Angielski - B2', 'Język Niemiecki - B2', 'Język Hiszpański - B2']


# ============================================================================
# GENEROWANIE
# ============================================================================

def slugify(text: str) -> str:
    s = unicodedata.normalize('NFKD', text)
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return s.lower().replace(' ', '').replace("'", '')


def generate_budynki():
    codes = BUILDING_CODES[:TOTAL_BUILDINGS]
    return [(code, BUILDING_NAMES.get(code, f"Budynek {code}")) for code in codes]


def generate_sale(n_budynki: int):
    sale = []
    per_building = TOTAL_ROOMS // n_budynki
    for b_id in range(1, n_budynki + 1):
        for idx in range(per_building):
            pietro = idx // 6
            numer = (idx % 6) + 1
            nazwa = f"{pietro}.{numer:02d}"
            if random.random() < BIG_ROOM_RATIO:
                pojemnosc = random.randint(ROOM_CAPACITY_BIG_MIN, ROOM_CAPACITY_BIG_MAX)
            else:
                pojemnosc = random.randint(ROOM_CAPACITY_SMALL_MIN, ROOM_CAPACITY_SMALL_MAX)
            sale.append((b_id, nazwa, pojemnosc))
    return sale


def generate_prowadzacy(fake: Faker):
    out = []
    for i in range(TOTAL_TEACHERS):
        imie = fake.first_name()
        nazwisko = fake.last_name()
        email = f"{slugify(imie)}.{slugify(nazwisko)}.{i + 1}@pwr.edu.pl"
        out.append((random.choice(TYTULY_NAUKOWE), imie, nazwisko, email))
    return out


def generate_kierunki():
    kierunki = []
    meta = []
    for skrot, nazwa, stopnie in PROGRAMS:
        for stop in stopnie:
            n_rocz = I_STOPIEN_ACTIVE_ROCZNIKI if stop.startswith('I -') else II_STOPIEN_ACTIVE_ROCZNIKI
            for offset in range(n_rocz):
                start_year = CURRENT_YEAR - offset
                sk = f"{skrot}-{STOPIEN_CODE[stop]}-{start_year % 100:02d}"
                kierunki.append((nazwa, sk, stop))
                meta.append({
                    'program_skrot': skrot,
                    'program_nazwa': nazwa,
                    'stopien': stop,
                    'start_year': start_year,
                    'offset': offset,
                    'sem_label': offset * 2 + 1,
                })
    return kierunki, meta


def generate_studenci(fake: Faker, n_kierunki: int):
    students = []
    kierunek_students = {}
    student_kierunki = {}

    # sporo zapasu na unikalne numery albumów
    max_needed = n_kierunki * STUDENTS_PER_ROCZNIK_MAX + 100
    albums = random.sample(range(ALBUM_RANGE_START, ALBUM_RANGE_END), max_needed)
    s_id = 0

    for k_idx in range(n_kierunki):
        count = random.randint(STUDENTS_PER_ROCZNIK_MIN, STUDENTS_PER_ROCZNIK_MAX)
        kierunek_students[k_idx] = []
        for _ in range(count):
            album = albums[s_id]
            s_id += 1
            imie = fake.first_name()
            nazwisko = fake.last_name()
            email = f"{album}@student.pwr.edu.pl"
            students.append((album, None, imie, nazwisko, email))
            kierunek_students[k_idx].append(s_id)
            student_kierunki[s_id] = [k_idx]

    return students, kierunek_students, student_kierunki


def add_double_kierunki(student_kierunki, kierunek_students, kierunek_meta):
    total = len(student_kierunki)
    num_double = int(total * DOUBLE_KIERUNEK_RATIO)

    by_stopien = defaultdict(list)
    for k_idx, m in enumerate(kierunek_meta):
        by_stopien[m['stopien']].append(k_idx)

    chosen = random.sample(range(1, total + 1), num_double)
    for s_id in chosen:
        cur = student_kierunki[s_id]
        stopien = kierunek_meta[cur[0]]['stopien']
        candidates = [k for k in by_stopien[stopien] if k not in cur]
        if candidates:
            k2 = random.choice(candidates)
            student_kierunki[s_id].append(k2)
            kierunek_students[k2].append(s_id)


def generate_bloki(kierunek_meta):
    bloki = []
    kierunek_bloki = {}

    for k_idx, m in enumerate(kierunek_meta):
        kierunek_bloki[k_idx] = []
        label = f"{m['program_skrot']}-{STOPIEN_CODE[m['stopien']]}-{m['start_year'] % 100:02d} sem{m['sem_label']}"
        for i in range(BLOCKS_OBLIG_PER_KIERUNEK):
            bloki.append((f"{label} - Blok Obowiązkowy {i + 1}",))
            kierunek_bloki[k_idx].append(len(bloki))
        for i in range(BLOCKS_ELECTIVE_PER_KIERUNEK):
            bloki.append((f"{label} - Blok Wybieralny {i + 1}",))
            kierunek_bloki[k_idx].append(len(bloki))

    wf_blok_ids = []
    for i in range(WF_BLOCKS_COUNT):
        bloki.append((f"WF - Blok Ogólnouczelniany {i + 1}",))
        wf_blok_ids.append(len(bloki))

    lang_blok_ids = []
    for i in range(LANG_BLOCKS_COUNT):
        bloki.append((f"Język Obcy - Blok Ogólnouczelniany {i + 1}",))
        lang_blok_ids.append(len(bloki))

    return bloki, kierunek_bloki, wf_blok_ids, lang_blok_ids


def generate_przedmioty(kierunek_bloki, kierunek_meta, wf_blok_ids, lang_blok_ids):
    przedmioty = []
    blok_przedmioty = defaultdict(list)
    kod_seq = 0

    for k_idx, blok_ids in kierunek_bloki.items():
        prog = kierunek_meta[k_idx]['program_skrot']
        oblig = blok_ids[:BLOCKS_OBLIG_PER_KIERUNEK]
        elect = blok_ids[BLOCKS_OBLIG_PER_KIERUNEK:]

        for b_id in oblig:
            kod_seq += 1
            nazwa = f"{random.choice(COURSE_NAME_POOL)} [{prog}]"
            przedmioty.append((b_id, f"K{kod_seq:06d}", nazwa, ECTS_PER_PRZEDMIOT))
            blok_przedmioty[b_id].append(len(przedmioty))

        for b_id in elect:
            n = random.randint(PRZEDMIOTY_PER_ELECTIVE_BLOCK_MIN, PRZEDMIOTY_PER_ELECTIVE_BLOCK_MAX)
            for _ in range(n):
                kod_seq += 1
                nazwa = f"{random.choice(ELECTIVE_COURSE_NAME_POOL)} [{prog}]"
                przedmioty.append((b_id, f"K{kod_seq:06d}", nazwa, ECTS_PER_PRZEDMIOT))
                blok_przedmioty[b_id].append(len(przedmioty))

    wf_przedmiot_ids = set()
    for b_id in wf_blok_ids:
        kod_seq += 1
        przedmioty.append((b_id, f"K{kod_seq:06d}", f"Wychowanie Fizyczne {b_id}", ECTS_WF))
        wf_przedmiot_ids.add(len(przedmioty))
        blok_przedmioty[b_id].append(len(przedmioty))

    lang_przedmiot_ids = set()
    for b_id in lang_blok_ids:
        kod_seq += 1
        przedmioty.append((b_id, f"K{kod_seq:06d}", f"{random.choice(LANG_NAMES)} [{b_id}]", ECTS_LEKTORAT))
        lang_przedmiot_ids.add(len(przedmioty))
        blok_przedmioty[b_id].append(len(przedmioty))

    return przedmioty, dict(blok_przedmioty), wf_przedmiot_ids, lang_przedmiot_ids


def generate_zajecia(n_przedmioty, wf_przedmiot_ids, lang_przedmiot_ids):
    zajecia = []
    przedmiot_zajecia = defaultdict(list)

    for p_id in range(1, n_przedmioty + 1):
        if p_id in wf_przedmiot_ids:
            zajecia.append((p_id, 'WF', 'Zaliczenie', LAB_HOURS_PER_WEEK))
            przedmiot_zajecia[p_id].append(len(zajecia))
        elif p_id in lang_przedmiot_ids:
            zajecia.append((p_id, 'Lektorat', 'Zaliczenie', LAB_HOURS_PER_WEEK))
            przedmiot_zajecia[p_id].append(len(zajecia))
        else:
            zajecia.append((p_id, 'Wykład', 'Egzamin', LECTURE_HOURS_PER_WEEK))
            przedmiot_zajecia[p_id].append(len(zajecia))
            rodzaj = random.choice(['Laboratorium', 'Projekt', 'Ćwiczenia'])
            forma = 'Ocena z kursu' if rodzaj == 'Ćwiczenia' else 'Zaliczenie'
            zajecia.append((p_id, rodzaj, forma, LAB_HOURS_PER_WEEK))
            przedmiot_zajecia[p_id].append(len(zajecia))

    return zajecia, dict(przedmiot_zajecia)


def _slot_times(h: int, m: int):
    start = time(h, m)
    end_dt = datetime(2000, 1, 1, h, m) + timedelta(minutes=CLASS_DURATION_MINUTES)
    return start, end_dt.time()


def generate_grupy(kierunek_bloki, kierunek_student_count,
                   blok_przedmioty, przedmiot_zajecia, zajecia,
                   big_sala_ids, all_sala_ids,
                   wf_przedmiot_ids, lang_przedmiot_ids):
    grupy = []
    kod_seq = 0

    for k_idx, blok_ids in kierunek_bloki.items():
        roc_size = kierunek_student_count[k_idx]
        cap_wyk = max(1, int(math.ceil(roc_size * CAPACITY_SLACK_RATIO)))

        # sloty na wykłady w obrębie rocznika - unikalne, bez kolizji
        all_slots = [(d, s) for d in DNI_DYDAKTYCZNE for s in TIME_SLOTS_START]
        random.shuffle(all_slots)
        lec_idx = 0

        for b_id in blok_ids:
            for p_id in blok_przedmioty[b_id]:
                for z_id in przedmiot_zajecia[p_id]:
                    rodzaj = zajecia[z_id - 1][1]
                    kod_seq += 1
                    if rodzaj == 'Wykład':
                        d, (h, m) = all_slots[lec_idx % len(all_slots)]
                        lec_idx += 1
                        start, end = _slot_times(h, m)
                        grupy.append((
                            random.choice(big_sala_ids), z_id, f"G{kod_seq:07d}",
                            cap_wyk, 'Co tydzień', d, start, end, None,
                        ))
                    else:
                        n_groups = max(1, math.ceil(roc_size * CAPACITY_SLACK_RATIO / LAB_GROUP_CAPACITY))
                        grupy.append((
                            random.choice(all_sala_ids), z_id, f"G{kod_seq:07d}",
                            LAB_GROUP_CAPACITY, 'Co tydzień',
                            random.choice(DNI_DYDAKTYCZNE),
                            *_slot_times(*random.choice(TIME_SLOTS_START)), None,
                        ))
                        for _ in range(n_groups - 1):
                            kod_seq += 1
                            grupy.append((
                                random.choice(all_sala_ids), z_id, f"G{kod_seq:07d}",
                                LAB_GROUP_CAPACITY, 'Co tydzień',
                                random.choice(DNI_DYDAKTYCZNE),
                                *_slot_times(*random.choice(TIME_SLOTS_START)), None,
                            ))

    # grupy ogólnouczelniane dla WF i języków
    ogolne_zajecia = []
    for p_id in wf_przedmiot_ids | lang_przedmiot_ids:
        ogolne_zajecia.extend(przedmiot_zajecia[p_id])

    for z_id in ogolne_zajecia:
        for _ in range(OGOLNE_GROUPS_PER_ZAJECIA):
            kod_seq += 1
            grupy.append((
                random.choice(all_sala_ids), z_id, f"G{kod_seq:07d}",
                OGOLNE_GROUP_CAPACITY, 'Co tydzień',
                random.choice(DNI_DYDAKTYCZNE),
                *_slot_times(*random.choice(TIME_SLOTS_START)), None,
            ))

    return grupy


def generate_tury(kierunek_meta, kierunek_bloki, wf_blok_ids, lang_blok_ids):
    tury = []
    concept_tury = {}

    concepts = defaultdict(list)
    for k_idx, m in enumerate(kierunek_meta):
        concepts[(m['program_skrot'], m['stopien'])].append(k_idx)

    for (prog, stop), _ in concepts.items():
        ids = []
        for i, name in enumerate(TURY_KIERUNKOWE_NAMES):
            start = TURA_BASE_DATETIME + timedelta(days=i * TURA_GAP_DAYS)
            end = start + timedelta(days=TURA_DURATION_DAYS)
            tury.append((f"Zapisy {name} - {prog} [{STOPIEN_CODE[stop]}]", start, end))
            ids.append(len(tury))
        concept_tury[(prog, stop)] = ids

    tury.append((
        "Zapisy Ogólnouczelniane - WF i Języki Obce",
        TURA_BASE_DATETIME,
        TURA_BASE_DATETIME + timedelta(days=TURA_DURATION_DAYS * 4),
    ))
    ogolna_tura_id = len(tury)

    tury_bloki = []
    for (prog, stop), k_idxs in concepts.items():
        t_ids = concept_tury[(prog, stop)]
        blok_set = set()
        for k_idx in k_idxs:
            blok_set.update(kierunek_bloki[k_idx])
        for t_id in t_ids:
            for b_id in blok_set:
                tury_bloki.append((t_id, b_id))

    for b_id in wf_blok_ids + lang_blok_ids:
        tury_bloki.append((ogolna_tura_id, b_id))

    return tury, concept_tury, ogolna_tura_id, tury_bloki


def build_student_associations(student_kierunki, kierunek_meta, kierunek_bloki,
                               wf_blok_ids, lang_blok_ids,
                               concept_tury, ogolna_tura_id):
    studenci_kierunki = []
    studenci_bloki = set()
    studenci_tury = set()

    for s_id, k_list in student_kierunki.items():
        for k_idx in k_list:
            studenci_kierunki.append((s_id, k_idx + 1))
            for b_id in kierunek_bloki[k_idx]:
                studenci_bloki.add((s_id, b_id))
            concept = (kierunek_meta[k_idx]['program_skrot'], kierunek_meta[k_idx]['stopien'])
            for t_id in concept_tury[concept]:
                studenci_tury.add((s_id, t_id))

        # aktualny WF + język - stabilny wybór po offset-cie rocznika
        offset = kierunek_meta[k_list[0]]['offset']
        studenci_bloki.add((s_id, wf_blok_ids[offset % WF_BLOCKS_COUNT]))
        studenci_bloki.add((s_id, lang_blok_ids[offset % LANG_BLOCKS_COUNT]))
        studenci_tury.add((s_id, ogolna_tura_id))

    return studenci_kierunki, list(studenci_bloki), list(studenci_tury)


# ============================================================================
# ZAPIS DO BAZY
# ============================================================================

def main():
    random.seed(RANDOM_SEED)
    Faker.seed(RANDOM_SEED)
    fake = Faker('pl_PL')
    fake.seed_instance(RANDOM_SEED)

    print("Generowanie danych...")

    budynki = generate_budynki()
    sale = generate_sale(len(budynki))
    big_sala_ids = [i + 1 for i, s in enumerate(sale) if s[2] >= ROOM_CAPACITY_BIG_MIN]
    all_sala_ids = list(range(1, len(sale) + 1))
    print(f"  budynki: {len(budynki)} | sale: {len(sale)} (duże: {len(big_sala_ids)})")

    prowadzacy = generate_prowadzacy(fake)
    print(f"  prowadzący: {len(prowadzacy)}")

    kierunki, kierunek_meta = generate_kierunki()
    print(f"  kierunki (program × stopień × rocznik): {len(kierunki)}")

    studenci, kierunek_students, student_kierunki = generate_studenci(fake, len(kierunek_meta))
    add_double_kierunki(student_kierunki, kierunek_students, kierunek_meta)
    kierunek_student_count = {k: len(v) for k, v in kierunek_students.items()}
    print(f"  studenci: {len(studenci)}")

    bloki, kierunek_bloki, wf_blok_ids, lang_blok_ids = generate_bloki(kierunek_meta)
    print(f"  bloki: {len(bloki)}")

    przedmioty, blok_przedmioty, wf_przedmiot_ids, lang_przedmiot_ids = generate_przedmioty(
        kierunek_bloki, kierunek_meta, wf_blok_ids, lang_blok_ids)
    print(f"  przedmioty: {len(przedmioty)}")

    zajecia, przedmiot_zajecia = generate_zajecia(len(przedmioty), wf_przedmiot_ids, lang_przedmiot_ids)
    print(f"  zajęcia: {len(zajecia)}")

    grupy = generate_grupy(
        kierunek_bloki, kierunek_student_count,
        blok_przedmioty, przedmiot_zajecia, zajecia,
        big_sala_ids, all_sala_ids,
        wf_przedmiot_ids, lang_przedmiot_ids,
    )
    print(f"  grupy: {len(grupy)}")

    tury, concept_tury, ogolna_tura_id, tury_bloki = generate_tury(
        kierunek_meta, kierunek_bloki, wf_blok_ids, lang_blok_ids)
    print(f"  tury: {len(tury)} | tury_bloki: {len(tury_bloki)}")

    studenci_kierunki, studenci_bloki, studenci_tury = build_student_associations(
        student_kierunki, kierunek_meta, kierunek_bloki,
        wf_blok_ids, lang_blok_ids, concept_tury, ogolna_tura_id)
    print(f"  studenci_kierunki: {len(studenci_kierunki)} | "
          f"studenci_bloki: {len(studenci_bloki)} | studenci_tury: {len(studenci_tury)}")

    grupy_prowadzacy = [(g_id, random.randint(1, TOTAL_TEACHERS))
                        for g_id in range(1, len(grupy) + 1)]

    print("\nZapisywanie do bazy...")
    conn = None
    cur = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor()

        print("  TRUNCATE...")
        cur.execute("""
            TRUNCATE budynki, sale, prowadzacy, kierunki, studenci,
                     tury, bloki, przedmioty, zajecia, grupy,
                     grupy_prowadzacy, studenci_kierunki, studenci_grupy,
                     tury_bloki, studenci_tury, studenci_bloki
            RESTART IDENTITY CASCADE;
        """)

        def insert(sql, data):
            if data:
                execute_values(cur, sql, data, page_size=BATCH_SIZE)

        print("  budynki"); insert(
            "INSERT INTO budynki (kod, nazwa) VALUES %s", budynki)
        print("  sale"); insert(
            "INSERT INTO sale (budynek_id, nazwa, pojemnosc) VALUES %s", sale)
        print("  prowadzący"); insert(
            "INSERT INTO prowadzacy (tytul_naukowy, imie, nazwisko, email) VALUES %s", prowadzacy)
        print("  kierunki"); insert(
            "INSERT INTO kierunki (nazwa, skrot, stopien) VALUES %s", kierunki)
        print("  studenci"); insert(
            "INSERT INTO studenci (album, pesel, imie, nazwisko, email_pwr) VALUES %s", studenci)
        print("  bloki"); insert(
            "INSERT INTO bloki (nazwa) VALUES %s", bloki)
        print("  przedmioty"); insert(
            "INSERT INTO przedmioty (blok_id, kod_kursu, nazwa, punkty_ects) VALUES %s", przedmioty)
        print("  zajęcia"); insert(
            "INSERT INTO zajecia (przedmiot_id, rodzaj, forma_zaliczenia, liczba_godzin_tygodniowo) VALUES %s", zajecia)
        print("  grupy"); insert(
            "INSERT INTO grupy (sala_id, zajecia_id, kod_grupy, liczba_miejsc, parzystosc, dzien, "
            "czas_rozpoczecia, czas_zakonczenia, uwagi_czas) VALUES %s", grupy)
        print("  tury"); insert(
            "INSERT INTO tury (nazwa, rozpoczecie, zakonczenie) VALUES %s", tury)

        print("  grupy_prowadzacy"); insert(
            "INSERT INTO grupy_prowadzacy (grupa_id, prowadzacy_id) VALUES %s", grupy_prowadzacy)
        print("  studenci_kierunki"); insert(
            "INSERT INTO studenci_kierunki (student_id, kierunek_id) VALUES %s", studenci_kierunki)
        print("  tury_bloki"); insert(
            "INSERT INTO tury_bloki (tura_id, blok_id) VALUES %s", tury_bloki)
        print("  studenci_tury"); insert(
            "INSERT INTO studenci_tury (student_id, tura_id) VALUES %s", studenci_tury)
        print("  studenci_bloki"); insert(
            "INSERT INTO studenci_bloki (student_id, blok_id) VALUES %s", studenci_bloki)

        conn.commit()
        print("\nGotowe. studenci_grupy zostaje pusta - do wypełnienia przez API zapisowe.")

    except Exception as e:
        print(f"Błąd: {e}")
        if conn:
            conn.rollback()
        raise
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()


if __name__ == '__main__':
    main()