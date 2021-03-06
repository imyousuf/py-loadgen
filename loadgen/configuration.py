__author__ = 'imyousuf'

import ConfigParser
from abc import ABCMeta
import random

class AbstractBaseLoadGeneratorConfiguration(object):
    __metaclass__ = ABCMeta
    def __init__(self):
        self._concurrent_requests = 10
        self._runs_per_thread = 10

    @property
    def concurrent_requests(self):
        return int(self._concurrent_requests)
    @concurrent_requests.setter
    def concurrent_requests(self, creq):
        self._concurrent_requests = creq
    @property
    def runs_per_thread(self):
        return int(self._runs_per_thread)
    @runs_per_thread.setter
    def runs_per_thread(self, rpt):
        self._runs_per_thread = rpt

class Enum(set):
    def __getattr__(self, name):
        if name in self:
            return name
        raise AttributeError
ScriptType = Enum(['SHELL', 'PYTHON', 'RUBY', 'BASH'])

class ScriptConfiguration(AbstractBaseLoadGeneratorConfiguration):
    def __init__(self):
        super(ScriptConfiguration, self).__init__()
        self._scripts = dict()
        self._type = ScriptType.SHELL
        self._executable = ""

    @property
    def executable(self):
        return self._executable
    @executable.setter
    def executable(self, executable):
        self._executable = executable
    @property
    def script_type(self):
        return self._type
    @script_type.setter
    def script_type(self,script_type):
        self._type = script_type
    @property
    def scripts(self):
        return self._scripts
    def put_script(self, group_name, script_path):
        self._scripts[group_name] = script_path
    def remove_script(self, group_name):
        del self._scripts[group_name]
    def get_random_script(self):
        k = random.choice(self._scripts.keys())
        return (k, self._scripts.get(k))

class MongoDBConfiguration(AbstractBaseLoadGeneratorConfiguration):
    def __init__(self):
        super(MongoDBConfiguration, self).__init__()
        self._connection_string = ''
        self._queries = dict()
        self._explain_each_query = False

    @property
    def connection_string(self):
        return self._connection_string
    @connection_string.setter
    def connection_string(self, connxn_str):
        self._connection_string = connxn_str
    @property
    def queries(self):
        return self._queries
    def add_query(self, name, query_string):
        self._queries[name] = query_string
    def remove_query(self, name):
        del self._queries[name]
    def get_random_query(self):
        k = random.choice(self._queries.keys())
        return (k, self._queries.get(k))
    @property
    def explain_each_query(self):
        return self._explain_each_query
    @explain_each_query.setter
    def explain_each_query(self, eeq):
        self._explain_each_query = eeq
    def __str__(self):
        return str("Generate load with %d conncurrent threads and execute one random query at a time for %d times \
against the %s DB Connection and at the end dump the explanation of the queries - %s"
                       % (int(self._concurrent_requests), int(self._runs_per_thread), self._connection_string, self._explain_each_query))
    def __unicode__(self):
        return unicode("Generate load with %d conncurrent threads and execute one random query at a time for %d times \
against the %s DB Connection and at the end dump the explanation of the queries - %s"
                       % (self._concurrent_requests, self._runs_per_thread, self._connection_string, self._explain_each_query))

def _populate_script_details(conf, configuration):
    if configuration.has_option('base', 'executable'):
        conf.executable = configuration.get('base', 'executable')
    for script_conf in configuration.items('scripts'):
        conf.put_script(script_conf[0], script_conf[1])

def parse_configuration(configuration):
    if isinstance(configuration, ConfigParser.RawConfigParser):
        target_type = configuration.get('base', 'target_type')
        conf = None
        if target_type == 'mongo':
            conf = MongoDBConfiguration()
            if not configuration.has_section('queries'):
                raise IOError('No use executing the script without queries')
            conf.connection_string = configuration.get('mongo', 'connection_string')
            if configuration.has_option('mongo', 'explain_each_query'):
                conf.explain_each_query = configuration.get('mongo', 'explain_each_query') == 'true'
            else:
                conf.explain_each_query = False
            for query_conf in configuration.items('queries'):
                conf.add_query(query_conf[0], query_conf[1])
        elif target_type == 'shell_script':
            conf = ScriptConfiguration()
            _populate_script_details(conf, configuration)
        elif target_type == 'bash_script':
            conf = ScriptConfiguration()
            conf.script_type = ScriptType.BASH
            _populate_script_details(conf, configuration)
        elif target_type == 'python_script':
            conf = ScriptConfiguration()
            conf.script_type = ScriptType.PYTHON
            _populate_script_details(conf, configuration)
        elif target_type == 'ruby_script':
            conf = ScriptConfiguration()
            conf.script_type = ScriptType.RUBY
            _populate_script_details(conf, configuration)
        if configuration.has_section('load'):
            if configuration.has_option('load', 'concurrent'):
                conf.concurrent_requests = configuration.get('load', 'concurrent')
            else:
                conf.concurrent_requests = 10
            if configuration.has_option('load', 'runs_per_thread'):
                conf.runs_per_thread = configuration.get('load', 'runs_per_thread')
            else:
                conf.runs_per_thread = 10
        else:
            conf.concurrent_requests = 10
            conf.runs_per_thread = 10
        return conf
    return None
