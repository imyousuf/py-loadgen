__author__ = 'imyousuf'

from multiprocessing import Pool
from abc import ABCMeta, abstractmethod
from pymongo import MongoClient
from stat import ExecutionStat
from configuration import MongoDBConfiguration, ScriptConfiguration
from . import collector
# For pymongo's string evaluation
import datetime, bson

job_queue = []

class JobGenerator(object):
    """
    An API allowing the generator to use in order to generate jobs so that they can be queued and executed
    parallelly.
    """
    __metaclass__ = ABCMeta
    @abstractmethod
    def populate_shared_state(self, configuration, manager):
        """
        Populate shared stateful objects to be shared across the processes that will execute the jobs
        :param configuration: The load generation configuration
        :param manager: The manager containing the shared objects
        :return: Nothing is returned
        """
        raise NotImplementedError
    @abstractmethod
    def next_job(self, configuration):
        """
        Retrieve the next job from this generator so that we can queue and parallelly execute them.
        :param configuration: The configuration to use to generate the next job to queue
        :return: An instance of the job to queue
        """
        raise NotImplementedError()

class Job(object):
    """
    An unit of work that we want to measure when we execute it.
    """
    __metaclass__ = ABCMeta

    @abstractmethod
    def get_group_name(self):
        """
        Retrieve group name being executed in the job so that we can later group the execution statistics by.
        :return: The execution group name
        """
        raise NotImplementedError()

    @abstractmethod
    def init_job(self):
        """
        Initialize the job and time taken for it should not be reflected upon the job execution
        :return: Nothing
        """
        raise NotImplementedError()

    @abstractmethod
    def finalize_job(self):
        """
        Finalize the job to release any resource that you want to for the resource
        :return: Nothing
        """
        raise NotImplementedError()

    @abstractmethod
    def execute_job(self):
        raise NotImplementedError()

    def run(self):
        self.init_job()
        stat = ExecutionStat(self.get_group_name())
        stat.start()
        self.execute_job()
        stat.stop()
        self.finalize_job()
        collector.add(stat)
        return stat

class MongoQueryExecutor(Job):
    def __init__(self, connection_string, query_name, query_string):
        self._connection_string = connection_string
        self._query_name = query_name
        self._query_string = query_string
        self._connection = None

    def init_job(self):
        self._connection = MongoClient(self._connection_string)

    def finalize_job(self):
        self._connection.close()

    def get_group_name(self):
        return self._query_name

    def execute_job(self):
        exe_c = 'self._connection.' + self._query_string
        print 'Executing ', exe_c
        eval(exe_c)

class MongoDBQueryJobGenerator(JobGenerator):

    def populate_shared_state(self, configuration, manager):
        pass

    def next_job(self, configuration):
        (qn, qs) = configuration.get_random_query()
        return MongoQueryExecutor(configuration.connection_string, qn, qs)

def run_job(item):
    stat = None
    try:
        stat = item.run()
    except Exception as e:
        print e
        pass
    return stat

def _get_generator_type(configurator):
    if isinstance(configurator, ScriptConfiguration):
        return None
    elif isinstance(configurator, MongoDBConfiguration):
        return MongoDBQueryJobGenerator

def generate_load(configuration):
    job_generator = _get_generator_type(configuration)
    total = configuration.concurrent_requests * configuration.runs_per_thread
    print "Jobs to be generated are ", total
    job_gen = job_generator()
    job_gen.populate_shared_state(configuration, None)
    for j in range(total):
        job_queue.append(job_gen.next_job(configuration))
    print "Create a pool"
    print "Pending jobs ", len(job_queue)
    pool = Pool(processes=configuration.concurrent_requests)
    stats = pool.map(run_job, job_queue)
    pool.close()
    for each_stat in stats:
        collector.add(each_stat)
    pool.join()
    return collector
