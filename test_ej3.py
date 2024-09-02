import os
import pytest
from utils import shell_cmd, git, docker, config, scripts, line_parser
from utils.mocks import mocks

def _test_nc(result):
  nc_logs = scripts.validate_echo_server()
  
  for line in nc_logs:
    print(line, end='')
    
    if f'action: test_echo_server | result: {result}' in line:
      return
    
    if 'action: test_echo_server | result:' in line:
      assert False, 'Echo server health check failed'
      
  assert False, 'Echo server health check failed'

@pytest.fixture(autouse=True, scope="module")
def setup():
  docker.stop_all()
  docker.prune()

@pytest.fixture(autouse=True)
def beforeEach():
  os.chdir(os.environ['REPO_PATH'])
  git.reset_branch()
  git.switch_branch("ej3")
  docker.down()

def test_echo_server():
  scripts.generate_docker_compose(0)
  docker.build()
  docker.up()
  
  _test_nc("success")
  
  server_logs = docker.logs()
  
  for line in server_logs:
    print(line, end='')
    msg = line_parser.parse(line)
    if not msg:
      continue
    assert(msg["result"] != line_parser.Result.FAIL)
    
    if msg["source"] == "server" and \
      msg["action"] == "receive_message" and \
      msg["result"] == "success":
      break
  
  docker.down()
  
def test_healthy_server():
  mocks.chdir()
  mocks.healthy_server_up()
  
  os.chdir(os.environ['REPO_PATH'])
  _test_nc("success")
  
  mocks.chdir()
  mocks.healthy_server_down()
  
def test_unhealthy_server():
  mocks.chdir()
  mocks.unhealthy_server_up()
  
  os.chdir(os.environ['REPO_PATH'])
  _test_nc("fail")
  
  mocks.chdir()
  mocks.unhealthy_server_down()
