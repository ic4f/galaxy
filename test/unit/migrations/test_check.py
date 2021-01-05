import os
import tempfile

import pytest
from sqlalchemy import (
    create_engine, 
    MetaData, 
    Table,
)
from sqlalchemy_utils import (
    create_database, 
    database_exists,
)
from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory

from galaxy.model.migrations.check import (
    DBOutdatedError, 
    NoAlembicVersioningError,
    NoMigrateVersioningError,
    run, 
)
from galaxy.model.migrations.utils import (
    ALEMBIC_CONFIG_FILE,
    ALEMBIC_TABLE,
    COLUMN_ATTRIBUTES_TO_VERIFY,
    TYPE_ATTRIBUTES_TO_VERIFY,
    MetaDataComparator,
    get_metadata_tables,
)
from states import state1, state2, state3, state5 as state_current


"""
DATABASE STATES:
1. dataset
2. state1 + history, hda, migrate_version
3. state2 + foo1
4. alembic added here
5. state4 + foo2

CASES: 
1. no db >> create, initialize, add alembic
2. empty db >> initialize, add alembic
3. nonempty db, alembic, up-to-date, w/data >> do nothing
4. nonempty db, no migrate, no alembic >> fail, error message: manual upgrade
4a. same + automigrate >> same: fail, error message: manual upgrade
5. nonempty db, has migrate, no alembic >> fail, error message: run migrate+alembic upgrade script
5a. same + automigrate >> ? (use migrate to upgrade to alembic-0, add alembic, upgrade)
6. nonempty db, has alembic >> fail, error message: run alembic upgrade script
6a. same + automigrate >> upgrade
"""


@pytest.fixture
def db_url():
    with tempfile.NamedTemporaryFile() as f:
        yield 'sqlite:///%s' % f.name


@pytest.fixture
def metadata():
    return state_current.metadata


def test_case_1(db_url, metadata):
    """No database."""
    assert not database_exists(db_url)

    run(db_url, metadata)
    assert database_exists(db_url)
    with create_engine(db_url).connect() as conn:
        assert_metadata(conn)
        assert_alembic(conn)
    

def test_case_2(db_url, metadata):
    """Empty database."""
    assert not database_exists(db_url)
    create_database(db_url)

    run(db_url, metadata)
    with create_engine(db_url).connect() as conn:
        assert_metadata(conn)
        assert_alembic(conn)


def test_case_3(db_url, metadata):
    """Everything is up-to-date."""
    assert not database_exists(db_url)
    create_database(db_url)
    with tempfile.TemporaryDirectory() as tmpdir:
        alembic_cfg = init_alembic(db_url, tmpdir)
        command.stamp(alembic_cfg, 'head')

        with create_engine(db_url).connect() as conn:
            load_metadata(conn, metadata)
            load_data(conn, state_current)

            run(db_url, metadata, tmpdir)
            assert_metadata(conn)
            assert_alembic(conn)
            assert_data(conn, state_current)


def test_case_4(db_url, metadata):
    """Nonempty database, no migrate, no alembic."""
    state_to_load = state1  # what we're loading into the db
    create_database(db_url)
    with create_engine(db_url).connect() as conn:
        load_metadata(conn, state_to_load.metadata)
        load_data(conn, state_to_load)

    with pytest.raises(NoMigrateVersioningError):
        run(db_url, metadata)


def test_case_4_automigrate(db_url, metadata):
    """Same as 4 + auto-migrate."""
    state_to_load = state1  # what we're loading into the db
    create_database(db_url)
    with create_engine(db_url).connect() as conn:
        load_metadata(conn, state_to_load.metadata)
        load_data(conn, state_to_load)

    with pytest.raises(NoMigrateVersioningError):
        run(db_url, metadata, auto_migrate=True)


def test_case_5(db_url, metadata):
    """Nonempty database, has migrate, no alembic."""
    state_to_load = state2  # what we're loading into the db
    create_database(db_url)
    with create_engine(db_url).connect() as conn:
        load_metadata(conn, state_to_load.metadata)
        load_data(conn, state_to_load)

    with pytest.raises(NoAlembicVersioningError):
        run(db_url, metadata)


def test_case_5_automigrate(db_url, metadata):
    """Same as 5 + auto-migrate."""
    state_to_load = state2  # what we're loading into the db
    create_database(db_url)
    with create_engine(db_url).connect() as conn:
        load_metadata(conn, state_to_load.metadata)
        load_data(conn, state_to_load)
    #TODO


def test_case_6(db_url, metadata):
    """Nonempty database, alembic-versioned, out-of-date."""
    create_database(db_url)
    with tempfile.TemporaryDirectory() as tmpdir:
        alembic_cfg = init_alembic(db_url, tmpdir)
        command.stamp(alembic_cfg, 'head')
        command.revision(alembic_cfg)  # new revision makes db outdated

        with create_engine(db_url).connect() as conn:
            load_metadata(conn, metadata)
            load_data(conn, state_current)

            with pytest.raises(DBOutdatedError):
                run(db_url, metadata, tmpdir)


def test_case_6_automigrate(db_url, metadata):
    """Same as 6 + auto-migrate."""
    create_database(db_url)
    with tempfile.TemporaryDirectory() as tmpdir:
        alembic_cfg = init_alembic(db_url, tmpdir)
        command.stamp(alembic_cfg, 'head')
        command.revision(alembic_cfg)  # new revision makes db outdated

        with create_engine(db_url).connect() as conn:
            load_metadata(conn, metadata)
            load_data(conn, state_current)
        #TODO


################# test utilities #################

def init_alembic(url, alembic_dir):
    config_file = os.path.join(alembic_dir, ALEMBIC_CONFIG_FILE)
    config = Config(config_file)
    config.set_main_option('sqlalchemy.url', url)
    config.set_main_option('script_location', alembic_dir)
    command.init(config, alembic_dir)
    return config


def load_metadata(conn, metadata):
    metadata.bind = conn
    metadata.create_all()
    assert_metadata(conn, metadata)


def load_data(conn, state):
    db_metadata = MetaData(bind=conn)
    db_metadata.reflect()
    for table in get_metadata_tables(db_metadata):
        table_data = state.data[table.name]
        ins = table.insert().values(table_data)
        conn.execute(ins)
    assert_data(conn, state)


def assert_metadata(conn, metadata=state_current.metadata):
    """Metadata loaded from the database is the same as the `metadata` argument."""
    db_metadata = MetaData(bind=conn)
    db_metadata.reflect()

    MetaDataComparator().compare(
        db_metadata, metadata, COLUMN_ATTRIBUTES_TO_VERIFY, TYPE_ATTRIBUTES_TO_VERIFY)


def assert_alembic(conn):
    """Database is under alembic version control."""
    metadata = MetaData(bind=conn)
    metadata.reflect()
    assert ALEMBIC_TABLE in metadata.tables, 'Database is not under alembic version control'

def assert_data(conn, state):
    """Assert that data in db is the same as defined in state.data."""

    def assert_table_data(table_name):
        db_data = conn.execute('select * from %s' % table_name).fetchall()
        # Assert that data in database is the same as the data devined in mapping* module.
        assert db_data == state.data[table_name]

    if state in (state1, state_current):
        assert_table_data('dataset')
    #if mapping in (mapping_v1, mapping_v2, mapping_v3, mapping_current):
    #    assert_table_data('history')
    #    assert_table_data('hda')
    #if mapping in (mapping_v2, mapping_v3, mapping_current):
    #    assert_table_data('migrate_version')
    #if mapping in (mapping_v3, mapping_current):
    #    assert_table_data('foo2')
    ## we do not test mapping_v4 because that's just for adding alembic
    #if mapping == mapping_current:
    #    assert_table_data('foo3')

