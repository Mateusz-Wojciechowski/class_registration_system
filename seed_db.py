import psycopg2
from psycopg2.extras import execute_values
from faker import Faker
import random
from datetime import datetime, timedelta

fake = Faker('pl_PL')

DB_CONFIG = {
    'dbname': 'ursus',
    'user': 'postgres',
    'password': 'root',
    'host': 'localhost',
    'port': '5432'
}


def generate_logical_data():
    print("Generowanie logicznej struktury pod zapisy...")

    tytuly = ['mgr inż.', 'dr inż.', 'dr hab. inż.']
    dni_tygodnia = ['PN', 'WT', 'ŚR', 'CZ', 'PT']

    budynki = [('C-13', 'Zintegrowane Centrum Studenckie')]
    sale = [(1, '1.11', 30), (1, '1.12', 30), (1, '2.15', 60)]

    prowadzacy = []
    for _ in range(15):
        imie, nazwisko = fake.first_name(), fake.last_name()
        prowadzacy.append((random.choice(tytuly), imie, nazwisko, f"{imie.lower()}.{nazwisko.lower()}@pwr.edu.pl"))

    kierunki = [
        ("Informatyka Stosowana", "IST", 'I - Inżynierskie'),
        ("Informatyka Algorytmiczna", "INA", 'I - Licencjackie'),
        ("Sztuczna Inteligencja", "SZI", 'II - Magisterskie')
    ]

    studenci = []
    albumy = random.sample(range(260000, 269999), 100)
    for album in albumy:
        imie, nazwisko = fake.first_name(), fake.last_name()
        studenci.append((album, None, imie, nazwisko, f"{album}@student.pwr.edu.pl"))  # PESEL omijamy dla uproszczenia

    teraz = datetime.now()
    tury = [
        ("Zapisy Główne - Semestr Zimowy", teraz - timedelta(days=2), teraz + timedelta(days=7)),
        ("Zapisy Korekcyjne - Semestr Zimowy", teraz + timedelta(days=14), teraz + timedelta(days=16))
    ]

    bloki = [
        ("Blok Obowiązkowy - Programowanie",),
        ("Blok Wybieralny - Technologie Mobilne",),
        ("Blok Wybieralny - Bazy Danych",)
    ]

    przedmioty = [
        (1, "INZ1001", "Programowanie Obiektowe", 5),
        (2, "INZ2001", "Programowanie Android", 4),
        (2, "INZ2002", "Programowanie iOS", 4),
        (3, "INZ3001", "Relacyjne Bazy Danych", 3)
    ]


    zajecia = [
        (1, 'Wykład', 'Egzamin', 2),
        (1, 'Laboratorium', 'Zaliczenie', 2),
        (2, 'Wykład', 'Ocena z kursu', 2),
        (2, 'Laboratorium', 'Zaliczenie', 2),
        (3, 'Projekt', 'Zaliczenie', 2)
    ]

    grupy = []
    for z_id in range(1, len(zajecia) + 1):
        for wariant in ['A', 'B', 'C']:
            dzien = random.choice(dni_tygodnia)
            godz_rozp = random.choice([8, 11, 13, 15])
            czas_rozp = datetime.strptime(f"{godz_rozp}:15", "%H:%M").time()
            czas_zak = (datetime.strptime(f"{godz_rozp}:15", "%H:%M") + timedelta(minutes=90)).time()

            grupy.append((
                random.randint(1, len(sale)),
                z_id,
                f"Z0{z_id}-{wariant}",
                30,
                'Co tydzień',
                dzien,
                czas_rozp,
                czas_zak,
                None
            ))

    return {
        'budynki': budynki, 'sale': sale, 'prowadzacy': prowadzacy, 'kierunki': kierunki,
        'studenci': studenci, 'tury': tury, 'bloki': bloki, 'przedmioty': przedmioty,
        'zajecia': zajecia, 'grupy': grupy
    }


def seed_database():
    data = generate_logical_data()

    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        print("Czyszczenie starych danych...")
        cursor.execute(
            "TRUNCATE budynki, sale, prowadzacy, kierunki, studenci, tury, bloki, przedmioty, zajecia, grupy RESTART IDENTITY CASCADE;")

        print("Wrzucanie tabel głównych...")
        execute_values(cursor, "INSERT INTO budynki (kod, nazwa) VALUES %s", data['budynki'])
        execute_values(cursor, "INSERT INTO sale (budynek_id, nazwa, pojemnosc) VALUES %s", data['sale'])
        execute_values(cursor, "INSERT INTO prowadzacy (tytul_naukowy, imie, nazwisko, email) VALUES %s",
                       data['prowadzacy'])
        execute_values(cursor, "INSERT INTO kierunki (nazwa, skrot, stopien) VALUES %s", data['kierunki'])
        execute_values(cursor, "INSERT INTO studenci (album, pesel, imie, nazwisko, email_pwr) VALUES %s",
                       data['studenci'])
        execute_values(cursor, "INSERT INTO tury (nazwa, rozpoczecie, zakonczenie) VALUES %s", data['tury'])
        execute_values(cursor, "INSERT INTO bloki (nazwa) VALUES %s", data['bloki'])
        execute_values(cursor, "INSERT INTO przedmioty (blok_id, kod_kursu, nazwa, punkty_ects) VALUES %s",
                       data['przedmioty'])
        execute_values(cursor,
                       "INSERT INTO zajecia (przedmiot_id, rodzaj, forma_zaliczenia, liczba_godzin_tygodniowo) VALUES %s",
                       data['zajecia'])
        execute_values(cursor,
                       "INSERT INTO grupy (sala_id, zajecia_id, kod_grupy, liczba_miejsc, parzystosc, dzien, czas_rozpoczecia, czas_zakonczenia, uwagi_czas) VALUES %s",
                       data['grupy'])

        print("Wrzucanie relacji asocjacyjnych (M:N)...")

        grupy_prow = [(g_id, random.randint(1, len(data['prowadzacy']))) for g_id in range(1, len(data['grupy']) + 1)]
        execute_values(cursor, "INSERT INTO grupy_prowadzacy (grupa_id, prowadzacy_id) VALUES %s", grupy_prow)

        studenci_kier = [(s_id, random.randint(1, len(data['kierunki']))) for s_id in
                         range(1, len(data['studenci']) + 1)]
        execute_values(cursor, "INSERT INTO studenci_kierunki (student_id, kierunek_id) VALUES %s", studenci_kier)

        tury_bloki = [(1, 1), (1, 2), (2, 3)]
        execute_values(cursor, "INSERT INTO tury_bloki (tura_id, blok_id) VALUES %s", tury_bloki)

        studenci_tury = [(s_id, 1) for s_id in range(1, len(data['studenci']) + 1)]
        execute_values(cursor, "INSERT INTO studenci_tury (student_id, tura_id) VALUES %s", studenci_tury)

        studenci_bloki = []
        for s_id in range(1, len(data['studenci']) + 1):
            studenci_bloki.extend([(s_id, 1), (s_id, 2)])
        execute_values(cursor, "INSERT INTO studenci_bloki (student_id, blok_id) VALUES %s", studenci_bloki)

        studenci_grupy = set()
        for s_id in range(1, 30):
            wybrane_grupy = random.sample(range(1, len(data['grupy']) + 1), 2)
            for g_id in wybrane_grupy:
                studenci_grupy.add((s_id, g_id))
        execute_values(cursor, "INSERT INTO studenci_grupy (student_id, grupa_id) VALUES %s ON CONFLICT DO NOTHING",
                       list(studenci_grupy))

        conn.commit()
        print("Baza gotowa pod testowanie API zapisowego!")

    except Exception as e:
        print(f"Błąd: {e}")
        if conn: conn.rollback()
    finally:
        if conn:
            cursor.close()
            conn.close()


if __name__ == '__main__':
    seed_database()