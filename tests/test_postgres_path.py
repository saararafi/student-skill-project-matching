"""
Exercises the PostgreSQL code path without needing a PostgreSQL server.

Render supplies a PostgreSQL database, and that path had never been run
against a live server. These tests drive the same code with a stub driver
so the Python-level behaviour is locked in:

- the PostgreSQL schema and seed are the ones that get executed
- the MySQL schema and the inline SQLite DDL are not
- an UPDATE does not try to read a sequence value (lastval() raises on
  PostgreSQL when no INSERT has happened in the session)
- an INSERT does return the new id
- rows come back as dictionaries on every engine
- a database that cannot be reached falls back instead of crashing
"""
import contextlib
import io
import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import backend.database as db  # noqa: E402


# =========================================================
# A stub that behaves like psycopg2
# =========================================================

class Row(dict):
    """A row that answers to both a column name and a column index."""

    def __init__(self, mapping, index=0):
        super().__init__(mapping)
        self._index = index

    def __getitem__(self, key):
        if isinstance(key, int):
            return list(self.values())[key]
        return dict.__getitem__(self, key)


class FakeCursor:
    """Records every statement and answers the queries the app makes."""

    def __init__(self, connection):
        self.connection = connection
        self._rows = []
        self._position = 0
        self.closed = False

    def execute(self, sql, params=None):
        self.connection.statements.append((sql, params))
        self._rows = self.connection.result_for(sql, params)
        self._position = 0
        return self

    def fetchone(self):
        if self._position >= len(self._rows):
            return None
        row = self._rows[self._position]
        self._position += 1
        return row

    def fetchall(self):
        rows = self._rows[self._position:]
        self._position = len(self._rows)
        return rows

    def close(self):
        self.closed = True

    def __enter__(self):
        return self

    def __exit__(self, *a):
        self.close()


class FakeConnection:
    def __init__(self):
        self.statements = []
        self.autocommit = False
        self.closed = False

    def cursor(self, cursor_factory=None):
        return FakeCursor(self)

    def commit(self):
        pass

    def close(self):
        self.closed = True

    def result_for(self, sql, params):
        """The canned answers for the handful of queries the app makes."""
        flat = ' '.join(sql.split()).lower()

        if 'lastval()' in flat:
            return [Row({'id': 42})]

        if 'information_schema.tables' in flat:
            # An empty database, so init_db has to create the schema.
            return []

        if 'information_schema.columns' in flat:
            # Every migrated column is already present.
            column = params[1] if params else 'column'
            return [Row({'column_name': column})]

        if 'from students where user_id' in flat:
            return [Row({'id': 1})]

        if 'from users' in flat and 'where id' in flat:
            # Only the user with id 1 exists.
            wanted = params[0] if params else 1
            if int(wanted) == 1:
                return [Row({'id': 1, 'name': 'Saara Rafi',
                             'email': 'saara@example.com', 'role': 'student'})]
            return []

        return []


class FakePsycopg2:
    """Stands in for the psycopg2 module."""

    def __init__(self):
        self.connections = []

    def connect(self, dsn, *a, **kw):
        conn = FakeConnection()
        self.connections.append(conn)
        return conn

    class extras:
        class RealDictCursor:
            pass


class PostgresPathTestCase(unittest.TestCase):

    def setUp(self):
        import tempfile
        self.fake = FakePsycopg2()
        self._tmpdir = tempfile.mkdtemp(prefix='postgres-test-')
        self._saved = {
            'psycopg2': db.psycopg2,
            'available': db.PSYCOPG2_AVAILABLE,
            'url': db.Config.DATABASE_URL,
            'engine': db.active_engine,
            'params': db._mysql_conn_params,
            'seed_demo': db.Config.SEED_DEMO_DATA,
            'sqlite_path': db.Config.SQLITE_DB_PATH,
        }

        db.psycopg2 = self.fake
        db.PSYCOPG2_AVAILABLE = True
        db.Config.DATABASE_URL = 'postgresql://user:pass@host:5432/skillmatch'
        db.active_engine = db.ENGINE_POSTGRES
        db._mysql_conn_params = None
        db.Config.SEED_DEMO_DATA = True
        db.Config.SQLITE_DB_PATH = os.path.join(self._tmpdir, 'test.db')

    def tearDown(self):
        import shutil
        db.psycopg2 = self._saved['psycopg2']
        db.PSYCOPG2_AVAILABLE = self._saved['available']
        db.Config.DATABASE_URL = self._saved['url']
        db.active_engine = self._saved['engine']
        db._mysql_conn_params = self._saved['params']
        db.Config.SEED_DEMO_DATA = self._saved['seed_demo']
        db.Config.SQLITE_DB_PATH = self._saved['sqlite_path']
        shutil.rmtree(self._tmpdir, ignore_errors=True)

    def statements(self):
        """Every statement across every connection the code opened."""
        out = []
        for conn in self.fake.connections:
            out.extend(sql for sql, _ in conn.statements)
        return out

    def statements_of_last(self):
        if not self.fake.connections:
            return []
        return [sql for sql, _ in self.fake.connections[-1].statements]


class TestPostgresSelection(PostgresPathTestCase):

    def test_database_url_selects_postgres(self):
        conn, engine = db.get_connection()
        self.assertEqual(engine, db.ENGINE_POSTGRES)
        conn.close()

    def test_postgres_is_preferred_over_mysql(self):
        db._mysql_conn_params = True
        conn, engine = db.get_connection()
        self.assertEqual(engine, db.ENGINE_POSTGRES)
        conn.close()

    def test_placeholders_are_left_alone_for_postgres(self):
        sql = 'SELECT id FROM students WHERE user_id = %s'
        self.assertEqual(db.adapt_sql(sql, db.ENGINE_POSTGRES), sql)

    def test_placeholders_become_question_marks_for_sqlite(self):
        sql = 'SELECT id FROM students WHERE user_id = %s'
        self.assertEqual(db.adapt_sql(sql, db.ENGINE_SQLITE),
                         'SELECT id FROM students WHERE user_id = ?')


class TestPostgresSchema(PostgresPathTestCase):

    def test_init_creates_the_postgres_schema_and_seed(self):
        db.init_db()

        joined = '\n'.join(self.statements())

        # The PostgreSQL schema was used.
        self.assertIn('CREATE TABLE IF NOT EXISTS users', joined)
        self.assertIn('SERIAL PRIMARY KEY', joined)
        self.assertIn('CREATE INDEX IF NOT EXISTS idx_applications_student', joined)

        # The MySQL schema was not.
        self.assertNotIn('AUTO_INCREMENT', joined)
        self.assertNotIn('ENGINE=InnoDB', joined)

        # The SQLite DDL was not.
        self.assertNotIn('AUTOINCREMENT', joined)

        # The seed was applied.
        self.assertIn('INSERT INTO users', joined)

        self.assertEqual(db.active_engine, db.ENGINE_POSTGRES)

    def test_the_schema_and_seed_files_are_found(self):
        """The lookup used a path that did not exist, so the schema never ran."""
        self.assertTrue(os.path.isdir(db.Config.BASE_DIR))
        self.assertTrue(os.path.isfile(
            os.path.join(db.Config.BASE_DIR, 'database', 'schema_postgres.sql')))
        self.assertTrue(os.path.isfile(
            os.path.join(db.Config.BASE_DIR, 'database', 'seed_data.sql')))

    def test_init_skips_the_use_statement(self):
        db.init_db()
        for sql in self.statements():
            self.assertFalse(
                sql.strip().upper().startswith('USE '),
                f'the MySQL USE statement leaked into PostgreSQL: {sql}'
            )

    def test_migrations_do_not_fail(self):
        db.init_db()

        # run_migrations() swallows its own errors, so the notice it prints
        # when something goes wrong is the signal to look for.
        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            db.run_migrations()

        output = buffer.getvalue()
        self.assertNotIn('Migration skipped', output,
                         f'the migration failed on PostgreSQL: {output}')

    def test_migrations_read_the_column_names_by_name(self):
        db.init_db()

        buffer = io.StringIO()
        with contextlib.redirect_stdout(buffer):
            db.run_migrations()

        checked = [sql for sql in self.statements()
                   if 'information_schema.columns' in sql.lower()]
        self.assertTrue(checked,
                        'the migration did not check the existing columns')


class TestPostgresWrites(PostgresPathTestCase):

    def test_an_update_does_not_ask_for_a_sequence_value(self):
        result = db.execute_query('UPDATE students SET bio = %s WHERE id = %s',
                                   ('hello', 1))
        self.assertIsNone(result)

        for sql in self.statements():
            self.assertNotIn('lastval', sql.lower(),
                             'an UPDATE must not read lastval()')

    def test_a_delete_does_not_ask_for_a_sequence_value(self):
        result = db.execute_query('DELETE FROM notifications WHERE id = %s', (3,))
        self.assertIsNone(result)

        for sql in self.statements():
            self.assertNotIn('lastval', sql.lower())

    def test_an_insert_returns_the_new_id(self):
        result = db.execute_query(
            'INSERT INTO students (user_id, department) VALUES (%s, %s)', (1, 'CSE'))
        self.assertEqual(result, 42)

        self.assertTrue(any('lastval' in s.lower() for s in self.statements()))

    def test_rows_come_back_as_dictionaries(self):
        user = db.fetch_one(
            'SELECT id, name, email, role FROM users WHERE id = %s', (1,))
        self.assertIsInstance(user, dict)
        self.assertEqual(user['name'], 'Saara Rafi')

    def test_a_missing_row_is_none(self):
        self.assertIsNone(db.fetch_one('SELECT id FROM users WHERE id = %s', (999,)))


class TestPostgresFallback(PostgresPathTestCase):

    def test_a_broken_database_url_falls_back_instead_of_crashing(self):
        class Broken(FakePsycopg2):
            def connect(self, dsn, *a, **kw):
                raise RuntimeError('could not connect to the server')

        db.psycopg2 = Broken()
        conn, engine = db.get_connection()
        # It fell through to SQLite rather than raising.
        self.assertEqual(engine, db.ENGINE_SQLITE)
        conn.close()

    def test_init_falls_back_to_sqlite_when_postgres_is_down(self):
        class Broken(FakePsycopg2):
            def connect(self, dsn, *a, **kw):
                raise RuntimeError('could not connect to the server')

        db.psycopg2 = Broken()
        db.init_db()
        self.assertEqual(db.active_engine, db.ENGINE_SQLITE)


if __name__ == '__main__':
    unittest.main()
