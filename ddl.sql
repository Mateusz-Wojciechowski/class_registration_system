
-- Enums

CREATE TYPE stopien_studiow AS ENUM (
    'I - Inżynierskie',
    'I - Licencjackie',
    'II - Magisterskie',
    'III - Doktoranckie'
);

CREATE TYPE rodzaj_zajec AS ENUM (
    'Wykład',
    'Ćwiczenia',
    'Laboratorium',
    'Projekt',
    'Seminarium',
    'Lektorat',
    'WF',
    'Inne'
);

CREATE TYPE parzystosc AS ENUM (
    'TP',         -- Tydzień Parzysty
    'TN',         -- Tydzień Nieparzysty
    'Co tydzień'
);

CREATE TYPE dzien_tygodnia AS ENUM (
    'PN', 'WT', 'ŚR', 'CZ', 'PT', 'SB', 'ND'
);

CREATE TYPE forma_zaliczenia AS ENUM (
    'Egzamin',
    'Ocena z kursu',
    'Zaliczenie'
);


-- Tabels


CREATE TABLE prowadzacy (
    id              SERIAL          PRIMARY KEY,
    tytul_naukowy   VARCHAR(128),
    imie            VARCHAR(256)    NOT NULL,
    nazwisko        VARCHAR(256)    NOT NULL,
    email           VARCHAR(256)    NOT NULL UNIQUE
);

CREATE TABLE studenci (
    id          SERIAL          PRIMARY KEY,
    album       INTEGER         NOT NULL UNIQUE,
    pesel       CHAR(11)        UNIQUE,            -- opcjonalny
    imie        VARCHAR(256)    NOT NULL,
    nazwisko    VARCHAR(256)    NOT NULL,
    email_pwr   VARCHAR(256)    NOT NULL UNIQUE
    CHECK (pesel ~ '^\d{11}$')
);

CREATE TABLE budynki (
    id      SERIAL          PRIMARY KEY,
    kod     VARCHAR(16)     NOT NULL UNIQUE,
    nazwa   VARCHAR(256)    NOT NULL
);

CREATE TABLE sale (
    id          SERIAL          PRIMARY KEY,
    budynek_id  INTEGER         NOT NULL REFERENCES budynki(id),
    nazwa       VARCHAR(256)     NOT NULL,
    pojemnosc   SMALLINT        CHECK (pojemnosc > 0)
);

CREATE TABLE kierunki (
    id      SERIAL              PRIMARY KEY,
    nazwa   VARCHAR(256)        NOT NULL,
    skrot   VARCHAR(16)         NOT NULL,
    stopien stopien_studiow     NOT NULL
);

CREATE TABLE tury (
    id          SERIAL      PRIMARY KEY,
    nazwa       VARCHAR(512) NOT NULL,
    rozpoczecie TIMESTAMP   NOT NULL,
    zakonczenie TIMESTAMP   NOT NULL,
    CHECK (zakonczenie > rozpoczecie)
);

CREATE TABLE bloki (
    id      SERIAL          PRIMARY KEY,
    nazwa   VARCHAR(512)    NOT NULL
);

CREATE TABLE przedmioty (
    id          SERIAL          PRIMARY KEY,
    blok_id     INTEGER         NOT NULL REFERENCES bloki(id) ON DELETE RESTRICT,
    kod_kursu   VARCHAR(32)     NOT NULL UNIQUE,
    nazwa       VARCHAR(512)    NOT NULL,
    punkty_ects SMALLINT        NOT NULL CHECK (punkty_ects > 0)
);

CREATE TABLE zajecia (
    id                      SERIAL              PRIMARY KEY,
    przedmiot_id            INTEGER             NOT NULL REFERENCES przedmioty(id) ON DELETE RESTRICT,
    rodzaj                  rodzaj_zajec        NOT NULL,
    forma_zaliczenia        forma_zaliczenia    NOT NULL,
    liczba_godzin_tygodniowo SMALLINT           NOT NULL CHECK (liczba_godzin_tygodniowo > 0)
);

CREATE TABLE grupy (
    id                  SERIAL          PRIMARY KEY,
    sala_id             INTEGER         REFERENCES sale(id) ON DELETE SET NULL,  -- grupa może nie mieć przypisanej sali
    zajecia_id          INTEGER         NOT NULL REFERENCES zajecia(id) ON DELETE RESTRICT,
    kod_grupy           VARCHAR(32)     NOT NULL UNIQUE,
    liczba_miejsc       SMALLINT        NOT NULL CHECK (liczba_miejsc > 0),
    parzystosc          parzystosc      NOT NULL DEFAULT 'Co tydzień',
    dzien               dzien_tygodnia,             -- opcjonalny
    czas_rozpoczecia    TIME,                        -- opcjonalny
    czas_zakonczenia    TIME,                        -- opcjonalny
    uwagi_czas          TEXT,
    CHECK (
        (czas_rozpoczecia IS NULL AND czas_zakonczenia IS NULL AND dzien IS NULL) OR 
        (czas_rozpoczecia IS NOT NULL AND czas_zakonczenia IS NOT NULL AND czas_zakonczenia > czas_rozpoczecia)
    )
);

-- Asocjacje

CREATE TABLE grupy_prowadzacy (
    grupa_id        INTEGER     NOT NULL REFERENCES grupy(id)       ON DELETE CASCADE,
    prowadzacy_id   INTEGER     NOT NULL REFERENCES prowadzacy(id)  ON DELETE CASCADE,
    PRIMARY KEY (grupa_id, prowadzacy_id)
);

CREATE TABLE studenci_kierunki (
    student_id  INTEGER NOT NULL REFERENCES studenci(id)  ON DELETE CASCADE,
    kierunek_id INTEGER NOT NULL REFERENCES kierunki(id)  ON DELETE CASCADE,
    PRIMARY KEY (student_id, kierunek_id)
);

CREATE TABLE studenci_grupy (
    student_id  INTEGER NOT NULL REFERENCES studenci(id)  ON DELETE CASCADE,
    grupa_id    INTEGER NOT NULL REFERENCES grupy(id)     ON DELETE CASCADE,
    PRIMARY KEY (student_id, grupa_id)
);

CREATE TABLE tury_bloki (
    tura_id     INTEGER NOT NULL REFERENCES tury(id)   ON DELETE CASCADE,
    blok_id     INTEGER NOT NULL REFERENCES bloki(id)  ON DELETE CASCADE,
    PRIMARY KEY (tura_id, blok_id)
);

CREATE TABLE studenci_tury (
    student_id  INTEGER NOT NULL REFERENCES studenci(id)  ON DELETE CASCADE,
    tura_id     INTEGER NOT NULL REFERENCES tury(id)      ON DELETE CASCADE,
    PRIMARY KEY (student_id, tura_id)
);

CREATE TABLE studenci_bloki (
    student_id  INTEGER NOT NULL REFERENCES studenci(id)  ON DELETE CASCADE,
    blok_id     INTEGER NOT NULL REFERENCES bloki(id)     ON DELETE CASCADE,
    PRIMARY KEY (student_id, blok_id)
);




CREATE INDEX idx_sale_budynek          ON sale(budynek_id);
CREATE INDEX idx_przedmioty_blok       ON przedmioty(blok_id);
CREATE INDEX idx_zajecia_przedmiot     ON zajecia(przedmiot_id);
CREATE INDEX idx_grupy_zajecia         ON grupy(zajecia_id);
CREATE INDEX idx_grupy_sala            ON grupy(sala_id);
CREATE INDEX idx_studenci_grupy_grupa  ON studenci_grupy(grupa_id);
CREATE INDEX idx_studenci_tury_tura    ON studenci_tury(tura_id);
CREATE INDEX idx_studenci_bloki_blok   ON studenci_bloki(blok_id);
CREATE INDEX idx_tury_bloki_blok       ON tury_bloki(blok_id);
CREATE INDEX idx_grupy_prowadzacy_prowadzacy ON grupy_prowadzacy(prowadzacy_id);
CREATE INDEX idx_studenci_kierunki_kierunek  ON studenci_kierunki(kierunek_id);
