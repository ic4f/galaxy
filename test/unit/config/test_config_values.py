import os
from collections import namedtuple
from datetime import timedelta

import pytest

from galaxy import config
from galaxy.util import listify
from galaxy.web.formatting import expand_pretty_datetime_format

TestData = namedtuple('TestData', ('key', 'expected', 'loaded'))


@pytest.fixture
def mock_config_file(monkeypatch):
    # Set this to return None to force the creation of base config directories
    # in _set_config_directories(). Used to test the values of these directories only.
    monkeypatch.setattr(config, 'find_config_file', lambda x: None)


@pytest.fixture
def mock_config_running_from_source(monkeypatch, mock_config_file):
    # Simulated condition: running from source, config_file is None.
    monkeypatch.setattr(config, 'running_from_source', True)


@pytest.fixture
def mock_config_running_not_from_source(monkeypatch, mock_config_file):
    # Simulated condition: running not from source, config_file is None.
    monkeypatch.setattr(config, 'running_from_source', False)


@pytest.fixture
def appconfig():
    return config.GalaxyAppConfiguration()


def test_root(appconfig):
    assert appconfig.root == os.path.abspath('.')


def test_base_config_if_running_from_source(mock_config_running_from_source, appconfig):
    assert not appconfig.config_file
    assert appconfig.config_dir == os.path.join(appconfig.root, 'config')
    assert appconfig.data_dir == os.path.join(appconfig.root, 'database')
    assert appconfig.managed_config_dir == appconfig.config_dir


def test_base_config_if_running_not_from_source(mock_config_running_not_from_source, appconfig):
    assert not appconfig.config_file
    assert appconfig.config_dir == os.getcwd()
    assert appconfig.data_dir == os.path.join(appconfig.config_dir, 'data')
    assert appconfig.managed_config_dir == os.path.join(appconfig.data_dir, 'config')


def test_common_base_config(appconfig):
    assert appconfig.shed_tools_dir == os.path.join(appconfig.data_dir, 'shed_tools')
    assert appconfig.sample_config_dir == os.path.join(appconfig.root, 'lib', 'galaxy', 'config', 'sample')


def listify_strip(value):
    return listify(value, do_strip=True)


class ExpectedValues:

    """TODO: add docstring here."""

    def __init__(self, appconfig):
        self._config_root = appconfig.root
        self._config_dir = appconfig.config_dir
        self._data_dir = appconfig.data_dir
        self._managed_config_dir = appconfig.managed_config_dir
        self._sample_config_dir = appconfig.sample_config_dir
        self._load_resolvers()
        self._load_paths()

    def get_value(self, key, value):
        """Return expected config value based on key and initial value. Initial value
        is transformed in the same way it would be transformed by GalaxyAppConfiguration.
        """
        # 1. If this is a path, resolve it
        if key in self._expected_paths:
            value = self._expected_paths[key]
        # 2. AFTER resolving paths, apply resolver, if one exists
        if key in self._resolvers:
            resolver = self._resolvers[key]
            if callable(resolver):
                value = resolver(value)
            else:
                value = resolver
        return value

    def _load_resolvers(self):
        self._resolvers = {
            'amqp_internal_connection': self.get_expected_amqp_internal_connection,
            'database_connection': self.get_expected_database_connection,
            'disable_library_comptypes': [''],  # TODO: we can do better
            'ftp_upload_dir_template': self.get_expected_ftp_upload_dir_template,
            'mulled_channels': listify_strip,
            'object_store_store_by': 'uuid',
            'password_expiration_period': timedelta,
            'persistent_communication_rooms': listify_strip,
            'pretty_datetime_format': expand_pretty_datetime_format,
            'statsd_host': '',  # TODO: do we need '' as the default?
            'tool_config_file': listify_strip,
            'tool_data_table_config_path': listify_strip,
            'tool_filters': listify_strip,
            'tool_label_filters': listify_strip,
            'tool_section_filters': listify_strip,
            'toolbox_filter_base_modules': listify_strip,
            'use_remote_user': None,  # TODO: should be False (config logic incorrect)
            'user_library_import_symlink_allowlist': listify_strip,
            'user_tool_filters': listify_strip,
            'user_tool_label_filters': listify_strip,
            'user_tool_section_filters': listify_strip,
        }
        # _resolvers provides expected values for config options.
        # - key: config option
        # - value: expected value or a callable. The callable will be called with a
        #   single argument, which is the default value of the config option.

    def _load_paths(self):
        self._expected_paths = {
            'admin_tool_recommendations_path': self._in_config_dir('tool_recommendations_overwrite.yml'),
            'auth_config_file': self._in_config_dir('auth_conf.xml'),
            'build_sites_config_file': self._in_sample_dir('build_sites.yml.sample'),
            'builds_file_path': self._in_root_dir('tool-data/shared/ucsc/builds.txt'),
            'citation_cache_data_dir': self._in_data_dir('citations/data'),
            'citation_cache_lock_dir': self._in_data_dir('citations/locks'),
            'cluster_files_directory': self._in_data_dir('pbs'),
            'config_dir': self._in_config_dir(),
            'data_dir': self._in_data_dir(),
            'data_manager_config_file': self._in_config_dir('data_manager_conf.xml'),
            'datatypes_config_file': self._in_sample_dir('datatypes_conf.xml.sample'),
            'dependency_resolvers_config_file': self._in_config_dir('dependency_resolvers_conf.xml'),
            'dynamic_proxy_session_map': self._in_data_dir('session_map.sqlite'),
            'file_path': self._in_data_dir('objects'),
            'galaxy_data_manager_data_path': self._in_root_dir('tool-data'),
            'integrated_tool_panel_config': self._in_managed_config_dir('integrated_tool_panel.xml'),
            'interactivetools_map': self._in_data_dir('interactivetools_map.sqlite'),
            'involucro_path': self._in_root_dir('involucro'),
            'job_config_file': self._in_config_dir('job_conf.xml'),
            'job_metrics_config_file': self._in_sample_dir('job_metrics_conf.xml.sample'),
            'job_resource_params_file': self._in_config_dir('job_resource_params_conf.xml'),
            'len_file_path': self._in_root_dir('tool-data/shared/ucsc/chrom'),
            'managed_config_dir': self._in_managed_config_dir(),
            'markdown_export_css': self._in_config_dir('markdown_export.css'),
            'markdown_export_css_invocation_reports': self._in_config_dir('markdown_export_invocation_reports.css'),
            'markdown_export_css_pages': self._in_config_dir('markdown_export_pages.css'),
            'migrated_tools_config': self._in_managed_config_dir('migrated_tools_conf.xml'),
            'mulled_resolution_cache_data_dir': self._in_data_dir('mulled/data'),
            'mulled_resolution_cache_lock_dir': self._in_data_dir('mulled/locks'),
            'new_file_path': self._in_data_dir('tmp'),
            'object_store_config_file': self._in_config_dir('object_store_conf.xml'),
            'oidc_backends_config_file': self._in_config_dir('oidc_backends_config.xml'),
            'oidc_config_file': self._in_config_dir('oidc_config.xml'),
            'openid_consumer_cache_path': self._in_data_dir('openid_consumer_cache'),
            'sanitize_allowlist_file': self._in_managed_config_dir('sanitize_allowlist.txt'),
            'shed_data_manager_config_file': self._in_managed_config_dir('shed_data_manager_conf.xml'),
            'shed_tool_config_file': self._in_managed_config_dir('shed_tool_conf.xml'),
            'shed_tool_data_path': self._in_root_dir('tool-data'),
            'shed_tool_data_table_config': self._in_managed_config_dir('shed_tool_data_table_conf.xml'),
            'template_cache_path': self._in_data_dir('compiled_templates'),
            'tool_cache_data_dir': self._in_data_dir('tool_cache'),
            'tool_config_file': self._in_sample_dir('tool_conf.xml.sample'),
            'tool_data_path': self._in_root_dir('tool-data'),
            'tool_data_table_config_path': self._in_sample_dir('tool_data_table_conf.xml.sample'),
            'tool_path': self._in_root_dir('tools'),
            'tool_search_index_dir': self._in_data_dir('tool_search_index'),
            'tool_sheds_config_file': self._in_config_dir('tool_sheds_conf.xml'),
            'tool_test_data_directories': self._in_root_dir('test-data'),
            'user_preferences_extra_conf_path': self._in_config_dir('user_preferences_extra_conf.yml'),
            'workflow_resource_params_file': self._in_config_dir('workflow_resource_params_conf.xml'),
            'workflow_schedulers_config_file': self._in_config_dir('workflow_schedulers_conf.xml'),
        }
        # _expected_paths provides expected values for config options that are paths. Each value is
        # wrapped in a function that ensures that the path (a) is resolved w.r.t. its parent as per
        # schema and/or config module; and (b) is an absolute path. The base config paths used by
        # each function are tested separately (see tests of base config properties in this module).
        # The values are hardcoded intentionally for the sake of keeping the test readable and
        # simple. They correspond to schema defaults, and should be adjusted if the schema is
        # modified.

    def _in_root_dir(self, path=None):
        return self._in_dir(self._config_root, path)

    def _in_config_dir(self, path=None):
        return self._in_dir(self._config_dir, path)

    def _in_data_dir(self, path=None):
        return self._in_dir(self._data_dir, path)

    def _in_managed_config_dir(self, path=None):
        return self._in_dir(self._managed_config_dir, path)

    def _in_sample_dir(self, path=None):
        return self._in_dir(self._sample_config_dir, path)

    def _in_dir(self, _dir, path):
        return os.path.join(_dir, path) if path else _dir

    def get_expected_database_connection(self, value):
        return 'sqlite:///{}/universe.sqlite?isolation_level=IMMEDIATE'.format(self._data_dir)

    def get_expected_ftp_upload_dir_template(self, value):
        return '${ftp_upload_dir}%s${ftp_upload_dir_identifier}' % os.path.sep

    def get_expected_amqp_internal_connection(self, value):
        return 'sqlalchemy+sqlite:///{}/control.sqlite?isolation_level=IMMEDIATE'.format(self._data_dir)


def get_test_data_with_default_values():
    """GalaxyAppConfiguration loaded with schema defaults."""
    appconfig = config.GalaxyAppConfiguration()
    ev = ExpectedValues(appconfig)
    for key, data in appconfig.schema.app_schema.items():
        default_value = data.get('default')
        expected_value = ev.get_value(key, default_value)
        loaded_value = getattr(appconfig, key)
        test_data = TestData(key, expected_value, loaded_value)
        yield pytest.param(test_data)


def get_test_data_with_set_values():
    """GalaxyAppConfiguration loaded with user-set values."""
    appconfig = config.GalaxyAppConfiguration(**SET_CONFIG)
    ev = ExpectedValues(appconfig)
    for key, data in appconfig.schema.app_schema.items():
        default_value = data.get('default')
        if key not in SET_CONFIG:
            value = default_value
        else:
            value = SET_CONFIG.get(key)
            if value == default_value:
                raise Exception('New value for %s set to schema default: use a different value' % key)
        expected_value = ev.get_value(key, value)
        loaded_value = getattr(appconfig, key)
        test_data = TestData(key, expected_value, loaded_value)
        yield pytest.param(test_data)


def get_key(test_data):
    return test_data.key


@pytest.mark.parametrize('test_data', get_test_data_with_default_values(), ids=get_key)
def test_default_config(test_data):
    assert test_data.expected == test_data.loaded


@pytest.mark.parametrize('test_data', get_test_data_with_set_values(), ids=get_key)
def test_set_config(test_data):
    assert test_data.expected == test_data.loaded


# These are all configuration properties defined in the schema (main schema file only)
# with values that differ from schema defaults. The values are meaningless; the serve
# the purpose of testing whether a config property can be set.
#
# Commented values indicate failing tests and require fixing. In many cases it's a bug
# (i.e., a property is not correctly set). Ideally, none should be commented out.
SET_CONFIG = {
    # 'admin_tool_recommendations_path': 'tool_recommendations_overwrite.yml',
    # 'allowed_origin_hostnames': 'None',
    # 'amqp_internal_connection': 'sqlalchemy+sqlite:///./database/control.sqlite?isolation_level=IMMEDIATE',
    # 'auth_config_file': 'auth_conf.xml',
    # 'build_sites_config_file': 'build_sites.yml',
    # 'builds_file_path': 'shared/ucsc/builds.txt',
    # 'citation_cache_data_dir': 'citations/data',
    # 'citation_cache_lock_dir': 'citations/locks',
    # 'cluster_files_directory': 'pbs',
    # 'containers_resolvers_config_file': 'None',
    # 'data_dir': 'data',
    # 'data_manager_config_file': 'config/data_manager_conf.xml',
    # 'database_connection': 'database_connection',
    # 'datatypes_config_file': 'config/datatypes_conf.xml',
    # 'dependency_resolvers_config_file': 'dependency_resolvers_conf.xml',
    # 'disable_library_comptypes': 'None',
    # 'dynamic_proxy_session_map': 'session_map.sqlite',
    # 'email_domain_allowlist_file': 'None',
    # 'email_domain_blocklist_file': 'None',
    # 'enable_beta_gdpr': True,
    # 'file_path': 'objects',
    # 'ftp_upload_dir_template': 'None',
    # 'galaxy_data_manager_data_path': 'None',
    # 'integrated_tool_panel_config': 'integrated_tool_panel.xml',
    # 'interactive_environment_plugins_directory': 'None',
    # 'interactivetools_map': 'interactivetools_map.sqlite',
    # 'interactivetools_proxy_host': 'None',
    # 'involucro_path': 'involucro',
    # 'job_config_file': 'config/job_conf.xml',
    # 'job_metrics_config_file': 'job_metrics_conf.xml',
    # 'job_resource_params_file': 'job_resource_params_conf.xml',
    # 'len_file_path': 'shared/ucsc/chrom',
    # 'markdown_export_css': 'markdown_export.css',
    # 'markdown_export_css_invocation_reports': 'markdown_export_invocation_reports.css',
    # 'markdown_export_css_pages': 'markdown_export_pages.css',
    # 'migrated_tools_config': 'migrated_tools_conf.xml',
    # 'mulled_resolution_cache_data_dir': 'mulled/data',
    # 'mulled_resolution_cache_lock_dir': 'mulled/locks',
    # 'new_file_path': 'tmp',
    # 'nginx_upload_store': 'None',
    # 'object_store_config_file': 'object_store_conf.xml',
    # 'object_store_store_by': 'None',
    # 'oidc_backends_config_file': 'oidc_backends_config.xml',
    # 'oidc_config_file': 'oidc_config.xml',
    # 'openid_consumer_cache_path': 'openid_consumer_cache',
    # 'sanitize_allowlist_file': 'sanitize_allowlist.txt',
    # 'shed_data_manager_config_file': 'shed_data_manager_conf.xml',
    # 'shed_tool_config_file': 'shed_tool_conf.xml',
    # 'shed_tool_data_path': 'None',
    # 'shed_tool_data_table_config': 'shed_tool_data_table_conf.xml',
    # 'single_user': 'single_user_new',
    # 'statsd_host': 'None',
    # 'template_cache_path': 'compiled_templates',
    # 'tool_cache_data_dir': 'tool_cache',
    # 'tool_config_file': config/tool_conf.xml,
    # 'tool_data_path': 'tool-data',
    # 'tool_data_table_config_path': 'config/tool_data_table_conf.xml',
    # 'tool_path': 'tools',
    # 'tool_search_index_dir': 'tool_search_index',
    # 'tool_sheds_config_file': 'tool_sheds_conf.xml',
    # 'tool_test_data_directories': 'test-data',
    # 'use_remote_user': True,
    # 'user_library_import_dir_auto_creation': True,
    # 'user_preferences_extra_conf_path': 'user_preferences_extra_conf.yml',
    # 'workflow_resource_params_file': 'workflow_resource_params_conf.xml',
    # 'workflow_resource_params_mapper': 'None',
    # 'workflow_schedulers_config_file': 'workflow_schedulers_conf.xml',
    'activation_grace_period': 2,
    'admin_users': 'admin_users_new',
    'allow_path_paste': True,
    'allow_user_creation': False,
    'allow_user_dataset_purge': False,
    'allow_user_deletion': True,
    'allow_user_impersonation': True,
    'apache_xsendfile': True,
    'api_allow_run_as': 'api_allow_run_as_new',
    'auto_configure_logging': False,
    'aws_estimate': True,
    'brand': 'brand_new',
    'cache_user_job_count': True,
    'check_job_script_integrity': False,
    'check_job_script_integrity_count': 34,
    'check_job_script_integrity_sleep': 0.24,
    'check_migrate_tools': True,
    'chunk_upload_size': 104857601,
    'citation_cache_type': 'file_new',
    'citation_url': 'https://galaxyproject.org/citing-galaxy/new',
    'cleanup_job': 'never',
    'communication_server_host': 'http://localhost_new',
    'communication_server_port': 7071,
    'conda_auto_init': False,
    'conda_auto_install': True,
    'conda_copy_dependencies': True,
    'conda_debug': True,
    'conda_ensure_channels': 'conda_ensure_channels_new',
    'conda_exec': 'conda_exec_new',
    'conda_prefix': 'conda_prefix_new',
    'conda_use_local': True,
    'config_dir': 'config_new',
    'cookie_domain': 'cookie_domain_new',
    'database_auto_migrate': True,
    'database_engine_option_echo': True,
    'database_engine_option_echo_pool': True,
    'database_engine_option_max_overflow': 9,
    'database_engine_option_pool_recycle': 0,
    'database_engine_option_pool_size': 4,
    'database_engine_option_server_side_cursors': True,
    'database_log_query_counts': True,
    'database_query_profiling_proxy': True,
    'database_template': 'database_template_new',
    'database_wait': True,
    'database_wait_attempts': 61,
    'database_wait_sleep': 1.1,
    'datatypes_disable_auto': True,
    'debug': True,
    'default_job_resubmission_condition': 'default_job_resubmission_condition_new',
    'default_job_shell': '/bin/bash_new',
    'default_locale': 'auto_new',
    'default_workflow_export_format': 'ga_new',
    'delay_tool_initialization': True,
    'dependency_resolution': 'dependency_resolution_new',
    'dependency_resolvers': 'dependency_resolvers_new',
    'display_chunk_size': 65537,
    'display_galaxy_brand': False,
    'display_servers': 'display_servers_new',
    'drmaa_external_killjob_script': 'drmaa_external_killjob_script_new',
    'drmaa_external_runjob_script': 'drmaa_external_runjob_script_new',
    'dynamic_proxy': 'node_new',
    'dynamic_proxy_bind_ip': '0.0.0.1',
    'dynamic_proxy_bind_port': 8801,
    'dynamic_proxy_debug': True,
    'dynamic_proxy_external_proxy': True,
    'dynamic_proxy_golang_api_key': 'dynamic_proxy_golang_api_key_new',
    'dynamic_proxy_golang_clean_interval': 11,
    'dynamic_proxy_golang_docker_address': 'unix:///var/run/docker.sock_new',
    'dynamic_proxy_golang_noaccess': 61,
    'dynamic_proxy_manage': False,
    'dynamic_proxy_prefix': 'gie_proxy_new',
    'email_from': 'email_from_new',
    'enable_beta_containers_interface': True,
    'enable_beta_markdown_export': True,
    'enable_beta_workflow_modules': True,
    'enable_communication_server': True,
    'enable_data_manager_user_view': True,
    'enable_job_recovery': False,
    'enable_legacy_sample_tracking_api': True,
    'enable_mulled_containers': False,
    'enable_oidc': True,
    'enable_old_display_applications': False,
    'enable_openid': True,
    'enable_per_request_sql_debugging': True,
    'enable_quotas': True,
    'enable_tool_recommendations': True,
    'enable_tool_shed_check': True,
    'enable_tool_tags': True,
    'enable_unique_workflow_defaults': True,
    'environment_setup_file': 'environment_setup_file_new',
    'error_email_to': 'error_email_to_new',
    'expose_dataset_path': True,
    'expose_potentially_sensitive_job_metrics': True,
    'expose_user_name': True,
    'external_chown_script': 'external_chown_script_new',
    'fetch_url_allowlist': '10.10.10.10',
    'fluent_host': 'localhost_new',
    'fluent_log': True,
    'fluent_port': 24225,
    'force_beta_workflow_scheduled_for_collections': True,
    'force_beta_workflow_scheduled_min_steps': 251,
    'ftp_upload_dir': 'ftp_upload_dir_new',
    'ftp_upload_dir_identifier': 'ftp_upload_dir_identifier_new',
    'ftp_upload_purge': False,
    'ftp_upload_site': 'ftp_upload_site_new',
    'ga_code': 'ga_code_new',
    'galaxy_infrastructure_url': 'http://localhost:8081',
    'galaxy_infrastructure_web_port': 8082,
    'heartbeat_interval': 21,
    'heartbeat_log': 'heartbeat_{server_name}.log_new',
    'helpsite_url': 'helpsite_url_new',
    'history_local_serial_workflow_scheduling': True,
    'hours_between_check': 11,
    'id_secret': 'id_secret_new',
    'inactivity_box_content': 'inactivity_box_content_new',
    'install_database_connection': 'install_database_connection_new',
    'instance_resource_url': 'instance_resource_url_new',
    'interactivetools_enable': True,
    'involucro_auto_init': False,
    'job_config': 'job_config_new',
    'job_working_directory': 'jobs_directory_new',
    'legacy_eager_objectstore_initialization': True,
    'library_import_dir': 'library_import_dir_new',
    'local_task_queue_workers': 3,
    'log_actions': True,
    'log_events': True,
    'log_level': 'INFO',
    'logging': 'loggin_new',
    'logo_url': '/new',
    'mailing_join_addr': 'mailing_join_addr_new',
    'mailing_lists_url': 'https://galaxyproject.org/mailing-lists/new',
    'managed_config_dir': 'managed_config_new',
    'markdown_export_epilogue': 'markdown_export_epilogue_new',
    'markdown_export_epilogue_invocation_reports': 'markdown_export_epilogue_invocation_reports_new',
    'markdown_export_epilogue_pages': 'markdown_export_epilogue_pages_new',
    'markdown_export_prologue': 'markdown_export_prologue_new',
    'markdown_export_prologue_invocation_reports': 'markdown_export_prologue_invocation_reports_new',
    'markdown_export_prologue_pages': 'markdown_export_prologue_pages_new',
    'master_api_key': 'master_api_key_new',
    'max_metadata_value_size': 5242881,
    'maximum_workflow_invocation_duration': 2678401,
    'maximum_workflow_jobs_per_scheduling_iteration': 0,
    'message_box_class': 'message_box_class_new',
    'message_box_content': 'message_box_content_new',
    'message_box_visible': True,
    'monitor_thread_join_timeout': 31,
    'mulled_channels': 'conda-forge,bioconda_new',
    'mulled_resolution_cache_type': 'file_new',
    'myexperiment_target_url': 'www.myexperiment.org:81',
    'new_user_dataset_access_role_default_private': True,
    'nginx_upload_job_files_path': 'nginx_upload_job_files_path_new',
    'nginx_upload_job_files_store': 'nginx_upload_job_files_store_new',
    'nginx_upload_path': 'nginx_upload_path_new',
    'nginx_x_accel_redirect_base': 'nginx_x_accel_redirect_base_new',
    'normalize_remote_user_email': True,
    'outputs_to_working_directory': True,
    'overwrite_model_recommendations': True,
    'parallelize_workflow_scheduling_within_histories': True,
    'password_expiration_period': 1,
    'persistent_communication_rooms': 'persistent_communication_rooms_new',
    'precache_dependencies': False,
    'preserve_python_environment': 'always',
    'pretty_datetime_format': '$locale (UTC)_new',
    'qa_url': 'qa_url_new',
    'real_system_username': 'user_email_new',
    'refgenie_config_file': 'refgenie_config_file_new',
    'registration_warning_message': 'registration_warning_message_new',
    'remote_user_header': 'HTTP_REMOTE_USER_new',
    'remote_user_logout_href': 'remote_user_logout_href_new',
    'remote_user_maildomain': 'remote_user_maildomain_new',
    'remote_user_secret': 'remote_user_secret_new',
    'require_login': True,
    'retry_job_output_collection': 1,
    'retry_metadata_internally': False,
    'sanitize_all_html': False,
    'screencasts_url': 'https://vimeo.com/galaxyproject/new',
    'search_url': 'https://galaxyproject.org/search/new',
    'select_type_workflow_threshold': 0,
    'sentry_dsn': 'sentry_dsn_new',
    'sentry_sloreq_threshold': 0.1,
    'serve_xss_vulnerable_mimetypes': True,
    'session_duration': 1,
    'show_user_prepopulate_form': True,
    'show_welcome_with_login': True,
    'slow_query_log_threshold': 0.1,
    'smtp_password': 'smtp_password_new',
    'smtp_server': 'smtp_server_new',
    'smtp_ssl': True,
    'smtp_username': 'smtp_username_new',
    'sniff_compressed_dynamic_datatypes_default': False,
    'static_cache_time': 361,
    'static_dir': 'static/_new',
    'static_enabled': False,
    'static_favicon_dir': 'static/favicon.ico_new',
    'static_images_dir': 'static/images_new',
    'static_robots_txt': 'static/robots.txt_new',
    'static_scripts_dir': 'static/scripts/_new',
    'static_style_dir': 'static/style_new',
    'statsd_influxdb': True,
    'statsd_port': 8126,
    'statsd_prefix': 'galaxy_new',
    'support_url': 'https://galaxyproject.org/support/new',
    'terms_url': 'terms_url_new',
    'tool_dependency_cache_dir': 'tool_dependency_cache_dir_new',
    'tool_dependency_dir': 'dependencies_new',
    'tool_description_boost': 2.1,
    'tool_enable_ngram_search': True,
    'tool_filters': 'tool_filters_new',
    'tool_help_boost': 0.6,
    'tool_label_boost': 1.1,
    'tool_label_filters': 'tool_label_filters_new',
    'tool_name_boost': 9.1,
    'tool_ngram_maxsize': 5,
    'tool_ngram_minsize': 4,
    'tool_recommendation_model_path': 'tool_recommendation_model_path_new',
    'tool_search_limit': 21,
    'tool_section_boost': 3.1,
    'tool_section_filters': 'tool_section_filters_new',
    'tool_stub_boost': 5.1,
    'toolbox_filter_base_modules': 'galaxy.tools.filters,galaxy.tools.toolbox.filters_new',
    'topk_recommendations': 11,
    'tour_config_dir': 'config/plugins/tours_new',
    'track_jobs_in_database': False,
    'transfer_manager_port': 8164,
    'trust_jupyter_notebook_conversion': True,
    'upstream_gzip': True,
    'use_cached_dependency_manager': True,
    'use_heartbeat': True,
    'use_lint': True,
    'use_pbkdf2': False,
    'use_printdebug': False,
    'use_profile': True,
    'use_tasked_jobs': True,
    'user_activation_on': True,
    'user_library_import_check_permissions': True,
    'user_library_import_dir': 'user_library_import_dir_new',
    'user_library_import_symlink_allowlist': 'user_library_import_symlink_allowlist_new',
    'user_tool_filters': 'examples:restrict_upload_to_admins, examples:restrict_encode_new',
    'user_tool_label_filters': 'examples:restrict_upload_to_admins, examples:restrict_encode_new',
    'user_tool_section_filters': 'examples:restrict_text_new',
    'visualization_plugins_directory': 'config/plugins/visualizations_new',
    'visualizations_visible': False,
    'watch_core_config': 'auto',
    'watch_job_rules': 'auto',
    'watch_tool_data_dir': 'auto',
    'watch_tools': 'auto',
    'watch_tours': 'auto',
    'webhooks_dir': 'config/plugins/webhooks_new',
    'welcome_url': '/static/welcome_new.html',
    'wiki_url': 'https://galaxyproject.org/new',
    'x_frame_options': 'SAMEORIGIN_new',
}
