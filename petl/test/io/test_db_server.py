# -*- coding: utf-8 -*-
from __future__ import absolute_import, print_function, division
import logging


import petl as etl
from petl.test.helpers import ieq


logger = logging.getLogger(__name__)
debug = logger.debug


def _test_dbo(write_dbo, read_dbo=None):
    if read_dbo is None:
        read_dbo = write_dbo

    expect_empty = (('foo', 'bar'),)
    expect = (('foo', 'bar'),
              ('a', 1),
              ('b', 2))
    expect_appended = (('foo', 'bar'),
                       ('a', 1),
                       ('b', 2),
                       ('a', 1),
                       ('b', 2))
    actual = etl.fromdb(read_dbo, 'SELECT * FROM test')

    debug('verify empty to start with...')
    ieq(expect_empty, actual)
    debug(etl.look(actual))

    debug('write some data and verify...')
    etl.todb(expect, write_dbo, 'test')
    ieq(expect, actual)
    debug(etl.look(actual))

    debug('append some data and verify...')
    etl.appenddb(expect, write_dbo, 'test')
    ieq(expect_appended, actual)
    debug(etl.look(actual))

    debug('overwrite and verify...')
    etl.todb(expect, write_dbo, 'test')
    ieq(expect, actual)
    debug(etl.look(actual))

    debug('cut, overwrite and verify')
    etl.todb(etl.cut(expect, 'bar', 'foo'), write_dbo, 'test')
    ieq(expect, actual)
    debug(etl.look(actual))

    debug('cut, append and verify')
    etl.appenddb(etl.cut(expect, 'bar', 'foo'), write_dbo, 'test')
    ieq(expect_appended, actual)
    debug(etl.look(actual))


def _test_with_schema(dbo, schema):

    expect = (('foo', 'bar'),
              ('a', 1),
              ('b', 2))
    expect_appended = (('foo', 'bar'),
                       ('a', 1),
                       ('b', 2),
                       ('a', 1),
                       ('b', 2))
    actual = etl.fromdb(dbo, 'SELECT * FROM test')

    print('write some data and verify...')
    etl.todb(expect, dbo, 'test', schema=schema)
    ieq(expect, actual)
    print(etl.look(actual))

    print('append some data and verify...')
    etl.appenddb(expect, dbo, 'test', schema=schema)
    ieq(expect_appended, actual)
    print(etl.look(actual))


def _test_unicode(dbo):
    expect = ((u'name', u'id'),
              (u'Արամ Խաչատրյան', 1),
              (u'Johann Strauß', 2),
              (u'Вагиф Сәмәдоғлу', 3),
              (u'章子怡', 4),
              )
    actual = etl.fromdb(dbo, 'SELECT * FROM test_unicode')

    print('write some data and verify...')
    etl.todb(expect, dbo, 'test_unicode')
    ieq(expect, actual)
    print(etl.look(actual))


def setup_mysql(dbapi_connection):
    # setup table
    cursor = dbapi_connection.cursor()
    # deal with quote compatibility
    cursor.execute('SET SQL_MODE=ANSI_QUOTES')
    cursor.execute('DROP TABLE IF EXISTS test')
    cursor.execute('CREATE TABLE test (foo TEXT, bar INT)')
    cursor.execute('DROP TABLE IF EXISTS test_unicode')
    cursor.execute('CREATE TABLE test_unicode (name TEXT, id INT) '
                   'CHARACTER SET utf8')
    cursor.close()
    dbapi_connection.commit()


def setup_postgresql(dbapi_connection):
    # setup table
    cursor = dbapi_connection.cursor()
    cursor.execute('DROP TABLE IF EXISTS test')
    cursor.execute('CREATE TABLE test (foo TEXT, bar INT)')
    cursor.execute('DROP TABLE IF EXISTS test_unicode')
    # assume character encoding UTF-8 already set at database level
    cursor.execute('CREATE TABLE test_unicode (name TEXT, id INT)')
    cursor.close()
    dbapi_connection.commit()


def dbtest_mysql():
    host, user, password, database = 'localhost', 'petl', 'test', 'petl'

    import pymysql
    connect = pymysql.connect

    # assume database already created
    dbapi_connection = connect(host=host,
                               user=user,
                               password=password,
                               database=database)

    # exercise using a dbapi_connection
    setup_mysql(dbapi_connection)
    _test_dbo(dbapi_connection)

    # exercise using a dbapi_cursor
    setup_mysql(dbapi_connection)
    dbapi_cursor = dbapi_connection.cursor()
    _test_dbo(dbapi_cursor)
    dbapi_cursor.close()

    # exercise sqlalchemy dbapi_connection
    setup_mysql(dbapi_connection)
    from sqlalchemy import create_engine
    sqlalchemy_engine = create_engine('mysql+pymysql://%s:%s@%s/%s' %
                                      (user, password, host, database))
    sqlalchemy_connection = sqlalchemy_engine.connect()
    sqlalchemy_connection.execute('SET SQL_MODE=ANSI_QUOTES')
    _test_dbo(sqlalchemy_connection)
    sqlalchemy_connection.close()

    # exercise sqlalchemy session
    setup_mysql(dbapi_connection)
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=sqlalchemy_engine)
    sqlalchemy_session = Session()
    _test_dbo(sqlalchemy_session)
    sqlalchemy_session.close()

    # other exercises
    _test_with_schema(dbapi_connection, database)
    utf8_connection = connect(host=host, user=user,
                              password=password,
                              database=database,
                              charset='utf8')
    utf8_connection.cursor().execute('SET SQL_MODE=ANSI_QUOTES')
    _test_unicode(utf8_connection)


def dbtest_postgresql():
    host, user, password, database = 'localhost', 'petl', 'test', 'petl'

    import psycopg2
    import psycopg2.extensions
    psycopg2.extensions.register_type(psycopg2.extensions.UNICODE)
    psycopg2.extensions.register_type(psycopg2.extensions.UNICODEARRAY)

    # assume database already created
    dbapi_connection = psycopg2.connect(
        'host=%s dbname=%s user=%s password=%s'
        % (host, database, user, password)
    )

    # exercise using a dbapi_connection
    setup_postgresql(dbapi_connection)
    _test_dbo(dbapi_connection)

    # exercise using a dbapi_cursor
    setup_postgresql(dbapi_connection)
    dbapi_cursor = dbapi_connection.cursor()
    _test_dbo(dbapi_cursor)
    dbapi_cursor.close()

    # exercise sqlalchemy dbapi_connection
    setup_postgresql(dbapi_connection)
    from sqlalchemy import create_engine
    sqlalchemy_engine = create_engine('postgresql+psycopg2://%s:%s@%s/%s' %
                                      (user, password, host, database))
    sqlalchemy_connection = sqlalchemy_engine.connect()
    _test_dbo(sqlalchemy_connection)
    sqlalchemy_connection.close()

    # exercise sqlalchemy session
    setup_postgresql(dbapi_connection)
    from sqlalchemy.orm import sessionmaker
    Session = sessionmaker(bind=sqlalchemy_engine)
    sqlalchemy_session = Session()
    _test_dbo(sqlalchemy_session)
    sqlalchemy_session.close()

    # other exercises
    _test_dbo(dbapi_connection,
              lambda: dbapi_connection.cursor(name='arbitrary'))
    _test_with_schema(dbapi_connection, 'public')
    _test_unicode(dbapi_connection)