import pytest

from galaxy.config import GalaxyAppConfiguration
from galaxy.config.schema import AppSchema


MOCK_DEPRECATED_DIRS = {
    'my_config_dir': 'old-config',
    'my_data_dir': 'old-database',
}

# Mock properties loaded from schema (all options represent paths)
MOCK_SCHEMA = {
    'my_config_dir': {
        'type': 'str',
        'default': 'my-config',
    },
    'my_data_dir': {
        'type': 'str',
        'default': 'my-data',
    },
    'path1': {
        'type': 'str',
        'default': 'my-config-files',
        'path_resolves_to': 'my_config_dir',
    },
    'path2': {
        'type': 'str',
        'default': 'my-data-files',
        'path_resolves_to': 'my_data_dir',
    },
    'path3': {
        'type': 'str',
        'default': 'my-other-files',
    },
    'path4': {
        'type': 'str',
        'default': 'conf1, conf2, conf3',
        'path_resolves_to': 'my_config_dir',
    },
}

MOCK_LISTIFY_OPTIONS = {'path4'}


def get_schema(app_mapping):
    return {'mapping': {'galaxy': {'mapping': app_mapping}}}


def test_deprecated_prefixes_set_correctly(monkeypatch):
    # Before we mock them, check that correct values are assigned
    monkeypatch.setattr(AppSchema, '_read_schema', lambda a, b: get_schema(MOCK_SCHEMA))
    monkeypatch.setattr(GalaxyAppConfiguration, '_process_config', lambda a, b: None)
    monkeypatch.setattr(GalaxyAppConfiguration, '_override_tempdir', lambda a, b: None)
    monkeypatch.setattr(GalaxyAppConfiguration, 'add_sample_file_to_defaults', [])

    config = GalaxyAppConfiguration()
    assert config.deprecated_dirs == {'config_dir': 'config', 'data_dir': 'database'}


@pytest.fixture
def mock_init(monkeypatch):
    monkeypatch.setattr(AppSchema, '_read_schema', lambda a, b: get_schema(MOCK_SCHEMA))
    monkeypatch.setattr(GalaxyAppConfiguration, '_process_config', lambda a, b: None)
    monkeypatch.setattr(GalaxyAppConfiguration, '_override_tempdir', lambda a, b: None)
    monkeypatch.setattr(GalaxyAppConfiguration, 'deprecated_dirs', MOCK_DEPRECATED_DIRS)
    monkeypatch.setattr(GalaxyAppConfiguration, 'add_sample_file_to_defaults', set())
    monkeypatch.setattr(GalaxyAppConfiguration, 'listify_options', MOCK_LISTIFY_OPTIONS)


def test_mock_schema_is_loaded(mock_init):
    # Check that mock is loaded as expected
    config = GalaxyAppConfiguration()
    assert len(config._raw_config) == 6
    assert config._raw_config['my_config_dir'] == 'my-config'
    assert config._raw_config['my_data_dir'] == 'my-data'
    assert config._raw_config['path1'] == 'my-config-files'
    assert config._raw_config['path2'] == 'my-data-files'
    assert config._raw_config['path3'] == 'my-other-files'
    assert config._raw_config['path4'] == 'conf1, conf2, conf3'


def test_no_kwargs(mock_init):
    # Expected: use default from schema, then resolve
    config = GalaxyAppConfiguration()
    assert config.path1 == 'my-config/my-config-files'  # resolved
    assert config.path2 == 'my-data/my-data-files'  # resolved
    assert config.path3 == 'my-other-files'  # no change
    assert config.path4 == ['my-config/conf1', 'my-config/conf2', 'my-config/conf3']  # each resolved and listified


def test_kwargs_relative_path(mock_init):
    # Expected: use value from kwargs, then resolve
    new_path1 = 'foo1/bar'
    new_path2 = 'foo2/bar'
    config = GalaxyAppConfiguration(path1=new_path1, path2=new_path2)

    assert config.path1 == 'my-config/' + new_path1  # resolved
    assert config.path2 == 'my-data/' + new_path2  # resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_ablsolute_path(mock_init):
    # Expected: use value from kwargs, do NOT resolve
    new_path1 = '/foo1/bar'
    new_path2 = '/foo2/bar'
    config = GalaxyAppConfiguration(path1=new_path1, path2=new_path2)

    assert config.path1 == new_path1  # NOT resolved
    assert config.path2 == new_path2  # NOT resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_relative_path_old_prefix(mock_init):
    # Expect: use value from kwargs, strip old prefix, then resolve
    new_path1 = 'old-config/foo1/bar'
    new_path2 = 'old-database/foo2/bar'
    config = GalaxyAppConfiguration(path1=new_path1, path2=new_path2)

    assert config.path1 == 'my-config/foo1/bar'  # stripped of old prefix, resolved
    assert config.path2 == 'my-data/foo2/bar'  # stripped of old prefix, resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_relative_path_old_prefix_for_other_option(mock_init):
    # Expect: use value from kwargs, do NOT strip old prefix, then resolve
    # Reason: deprecated dirs are option-specific: we don't want to strip 'old-config'
    # (deprecated for the config_dir option) if it's used for another option
    new_path1 = 'old-database/foo1/bar'
    new_path2 = 'old-config/foo2/bar'
    config = GalaxyAppConfiguration(path1=new_path1, path2=new_path2)

    assert config.path1 == 'my-config/' + new_path1  # resolved
    assert config.path2 == 'my-data/' + new_path2  # resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_relative_path_old_prefix_empty_after_strip(mock_init):
    # Expect: use value from kwargs, strip old prefix, then resolve
    new_path1 = 'old-config'
    config = GalaxyAppConfiguration(path1=new_path1)

    assert config.path1 == 'my-config/'  # stripped of old prefix, then resolved
    assert config.path2 == 'my-data/my-data-files'  # stripped of old prefix, then resolved
    assert config.path3 == 'my-other-files'  # no change


def test_kwargs_set_to_null(mock_init):
    # Expected: allow overriding with null, then resolve
    # This is not a common scenario, but it does happen: one example is
    # `job_config` set to `None` when testing
    config = GalaxyAppConfiguration(path1=None)

    assert config.path1 == 'my-config'  # resolved
    assert config.path2 == 'my-data/my-data-files'  # resolved
    assert config.path3 == 'my-other-files'  # no change


def mock_process_config(config_instance, _):
    config_instance._select_one_path_from_list()
    config_instance._select_one_or_all_paths_from_list()


def test_no_kwargs_listify(mock_init, monkeypatch):
    # Expected: last value resolved and listified; others dropped as files do not exist
    monkeypatch.setattr(GalaxyAppConfiguration, '_process_config', mock_process_config)
    config = GalaxyAppConfiguration()

    assert config._raw_config['path4'] == 'conf1, conf2, conf3'
    assert config.path4 == ['my-config/conf3']


def test_no_kwargs_listify_all_files_exist(mock_init, monkeypatch):
    # Expected: each value resolved and listified (mock: all files exist)
    monkeypatch.setattr(GalaxyAppConfiguration, '_process_config', mock_process_config)
    monkeypatch.setattr(GalaxyAppConfiguration, '_path_exists', lambda a, b: True)
    config = GalaxyAppConfiguration()

    assert config._raw_config['path4'] == 'conf1, conf2, conf3'
    assert config.path4 == ['my-config/conf1', 'my-config/conf2', 'my-config/conf3']


def test_kwargs_listify(mock_init, monkeypatch):
    # Expected: use values from kwargs; each value resolved and listified
    new_path4 = 'new1, new2'
    monkeypatch.setattr(GalaxyAppConfiguration, '_process_config', mock_process_config)
    config = GalaxyAppConfiguration(path4=new_path4)

    assert config._raw_config['path4'] == 'new1, new2'
    assert config.path4 == ['my-config/new1', 'my-config/new2']


def test_add_sample_file(mock_init, monkeypatch):
    # Expected: sample file appended to list of defaults:
    # - resolved w.r.t sample-dir (_in_sample_dir mocked)
    # - has ".sample" suffix
    # - if defaults was one value, it's listified
    # - if defaults was a list, then the last item is used as template for sample: foo >> foo.sample
    monkeypatch.setattr(GalaxyAppConfiguration, 'add_sample_file_to_defaults', {'path1', 'path4'})
    monkeypatch.setattr(GalaxyAppConfiguration, '_in_sample_dir', lambda a, path: '/sample-dir/%s' % path)
    config = GalaxyAppConfiguration()

    assert config._raw_config['path1'] == 'my-config-files'
    assert config.path1 == ['my-config/my-config-files', '/sample-dir/my-config-files.sample']
    assert config._raw_config['path4'] == 'conf1, conf2, conf3'
    assert config.path4 == ['my-config/conf1', 'my-config/conf2', 'my-config/conf3', '/sample-dir/conf3.sample']


def test_select_one_path_from_list(mock_init, monkeypatch):
    # Expected: files do not exist, so use last file in list (would be sample file); value is not a list
    monkeypatch.setattr(GalaxyAppConfiguration, 'add_sample_file_to_defaults', {'path1'})
    monkeypatch.setattr(GalaxyAppConfiguration, '_in_sample_dir', lambda a, path: '/sample-dir/%s' % path)
    monkeypatch.setattr(GalaxyAppConfiguration, '_process_config', mock_process_config)
    config = GalaxyAppConfiguration()

    assert config._raw_config['path1'] == 'my-config-files'
    assert config.path1 == '/sample-dir/my-config-files.sample'


def test_select_one_path_from_list_all_files_exist(mock_init, monkeypatch):
    # Expected: all files exist, so use first file in list; value is not a list
    monkeypatch.setattr(GalaxyAppConfiguration, 'add_sample_file_to_defaults', {'path1'})
    monkeypatch.setattr(GalaxyAppConfiguration, '_path_exists', lambda a, b: True)
    monkeypatch.setattr(GalaxyAppConfiguration, '_process_config', mock_process_config)
    config = GalaxyAppConfiguration()

    assert config._raw_config['path1'] == 'my-config-files'
    assert config.path1 == 'my-config/my-config-files'
