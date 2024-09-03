import os
import pytest
from utils import shell_cmd, git, docker, config, scripts, line_parser

CLIENT_CONFIG = {
	'loop_amount' : 500,
	'loop_period' : '150ms'
}

MESSAGES_BEFORE_STOP = 10

@pytest.fixture(autouse=True, scope='module')
def setup():
	os.chdir(os.environ['REPO_PATH'])
	git.reset_branch()
	git.switch_branch('ej4')
	docker.stop_all()
	docker.prune()
	#Build images only once
	docker.build()

@pytest.fixture(autouse=True)
def beforeEach():
	docker.down()
	git.reset_branch()
	scripts.generate_docker_compose(1)
	config.server(logging_level='DEBUG')
	config.client(**CLIENT_CONFIG)

def _test_config(target_container):
	docker.up()
	logs = docker.logs()
	msg_count = MESSAGES_BEFORE_STOP
	stop_sent = False

	for line in logs:
		print(line, end='')

		msg_count -= 1
		if msg_count == 0:
			stop_sent = True
			if target_container == 'all':
				docker.down(grace_period=10)
			else:
				print('Sent SIGTERM to ' + target_container)
				docker.stop(target_container, grace_period=20)

		msg = line_parser.parse(line)
		if not msg:
			continue

		if msg['action'] == 'exit':
			if target_container == 'all':
				#Expects only one of the services to exit with code 0, since
				#the other one could fail due to the socket being closed
				if msg['result'] == line_parser.Result.SUCCESS:
					break
			else:
				if msg['source'] != target_container:
					continue
				assert (msg['result'] == line_parser.Result.SUCCESS), f'{target_container} should exit successfully'
				break
		elif not stop_sent:
			assert (msg['result'] != line_parser.Result.FAIL), 'No operation should fail'

	assert (stop_sent), 'SIGTERM should have been sent'
	docker.down()

def test_client_down():
	_test_config('client1')

def test_server_down():
	_test_config('server')

def test_both_down():
	_test_config('all')
