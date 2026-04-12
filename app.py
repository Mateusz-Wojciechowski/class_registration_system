from flask import Flask, request, jsonify
import psycopg2
from psycopg2.extras import RealDictCursor

app = Flask(__name__)


DB_CONFIG = {
    'dbname': 'ursus',
    'user': 'postgres',
    'password': 'root',
    'host': 'localhost',
    'port': '5432'
}




def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


@app.route('/api/zapisy', methods=['POST'])
def zapisz_studenta():
    data = request.get_json()

    if not data or 'student_id' not in data or 'grupa_id' not in data:
        return jsonify({'error': 'Brakujące parametry. Wymagane: student_id, grupa_id'}), 400

    student_id = data['student_id']
    grupa_id = data['grupa_id']

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor(cursor_factory=RealDictCursor)

        cursor.execute("SELECT id FROM studenci WHERE id = %s;", (student_id,))
        if not cursor.fetchone():
            return jsonify({'error': 'Student o podanym ID nie istnieje.'}), 404

        cursor.execute("""
                       SELECT g.liczba_miejsc, COUNT(sg.student_id) as zajete_miejsca
                       FROM grupy g
                                LEFT JOIN studenci_grupy sg ON g.id = sg.grupa_id
                       WHERE g.id = %s
                       GROUP BY g.id;
                       """, (grupa_id,))

        grupa_info = cursor.fetchone()

        if not grupa_info:
            return jsonify({'error': 'Grupa o podanym ID nie istnieje.'}), 404

        if grupa_info['zajete_miejsca'] >= grupa_info['liczba_miejsc']:
            return jsonify({'error': 'Brak wolnych miejsc w tej grupie.'}), 409

        cursor.execute("""
                       SELECT 1
                       FROM studenci_grupy
                       WHERE student_id = %s
                         AND grupa_id = %s;
                       """, (student_id, grupa_id))

        if cursor.fetchone():
            return jsonify({'error': 'Student jest już zapisany do tej grupy.'}), 409

        cursor.execute("""
                       INSERT INTO studenci_grupy (student_id, grupa_id)
                       VALUES (%s, %s);
                       """, (student_id, grupa_id))

        conn.commit()
        return jsonify({
            'message': 'Pomyślnie zapisano na zajęcia!',
            'zajete_miejsca_po_zapisie': grupa_info['zajete_miejsca'] + 1,
            'limit_miejsc': grupa_info['liczba_miejsc']
        }), 201  # 201 Created

    except Exception as e:
        if conn:
            conn.rollback()
        return jsonify({'error': f'Błąd wewnętrzny serwera: {str(e)}'}), 500

    finally:
        if conn:
            cursor.close()
            conn.close()


if __name__ == '__main__':
    # http:/127.0.0.1:5000/api/zapisy
    app.run(debug=True, port=5000)