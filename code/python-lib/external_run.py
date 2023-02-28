# external_run.py

import os
# $ pip install psutil
import psutil
import sys

from jena.client_manager import ClientManager
from jena.jenaClient import JenaClient, ThriftConnectionException

try:
	from options import JAVA_PATH  # comment out this import if loading the script from a foreign directory
except ImportError:
	pass


_DIR_PATH = os.path.dirname(os.path.realpath(__file__))  # dir of current .py file


# Jena service daemon process
JENA_SERVICE_PORT = 20299
JENA_RULE_PATHS = "jena/alg_rules.ttl;jena/relink_acts.ttl;jena/unskip_acts.ttl;jena/trace_rules.ttl"
	# tip: jena/rdfs4core.rules;jena/loop_names.ttl; <- these shouldn't be used separately
_service_Process = None
_client_Manager = None


def invoke_jena_reasoning_service(rdfData: bytes, rules_path=JENA_RULE_PATHS):
	"""Start service process (`jena/Jena.jar`) if not running yet and
	perform `runReasoner` on it with given `rdfData`"""
	# java -jar Jena.jar jena "test_data/test_make_trace_output.rdf" "jena/all.rules" "test_data/jena_output.rdf"

	global _service_Process, _client_Manager
	need_create_process = False
	if not _service_Process or not _service_Process.is_running():
		need_create_process = True
	elif _service_Process.status() == psutil.STATUS_ZOMBIE:
		_service_Process.wait()
		need_create_process = True

	exception = None
	for _ in range(2):  # loop to retry
		cur_dir = ''

		if need_create_process:
			# invoke separate java process in non-blocking fasion, with shared stdout
			cmd = f'{JAVA_PATH} -jar {cur_dir}jena/Jena.jar service --port {JENA_SERVICE_PORT}'.split()
			print("Starting java background service ...")
			print("  command:  ", cmd)
			_service_Process = psutil.Popen(cmd, stdout=sys.stderr, cwd=_DIR_PATH)

		try:
			if not _client_Manager:
				_client_Manager = ClientManager(
					lambda: JenaClient(port=JENA_SERVICE_PORT)
				)
				_client_Manager.run(lambda jc: jc.ping())

			# do the work!
			return _client_Manager.run(lambda jc: jc.runReasoner(rdfData, rulePaths=rules_path))

		except ThriftConnectionException as ex:
			exception = ex
			# try recover service process
			stop_jena_reasoning_service()
			continue

	if exception:
		# if we reached here, there is still an error.
		raise exception


def stop_jena_reasoning_service():
	"""Stop service process (`jena/Jena.jar`) if it is running"""
	global _service_Process
	if _service_Process and _service_Process.is_running():
		if _client_Manager:
			print("Stopping java background service ...")
			_client_Manager.run(lambda jc: jc.stop())

		print("Killing java background service ...")
		_service_Process.kill()
		_service_Process.wait()
		_service_Process = None

