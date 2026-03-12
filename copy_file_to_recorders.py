#! /opt/python_envs/env_vlbi_obs/bin/python
from pssh.clients import ParallelSSHClient
from pssh.utils import enable_logger, logger
import os
from gevent import joinall

# Configuration
#hosts = ["recorder1","recorder2","recorder3","recorder4"]
hosts = ["recorder1"]
user = "oper"
pkey_path = os.path.expanduser("~/.ssh/id_rsa_tenzing_mk6")  # Your private key

# Local and Remote paths
local_file_path = "./session.xml"
remote_file_path = "/home/oper/session.xml"

# 1. Initialize the client
client = ParallelSSHClient(hosts, user=user, pkey=pkey_path)

# 2. Copy the file to all hosts in parallel
print("Copying file to all hosts...")
cmds = client.copy_file(local_file_path, remote_file_path)
#client.join(cmds) # Wait for all transfers to complete
joinall(cmds, raise_error=True) # Wait for all transfers to complete

# Command to launch
session_name = "parallel_app"
#launch_cmd = f"screen -d -m -S {session_name} python3 {remote_file_path}"
#launch_cmd = f"screen -d -m -S {session_name} ls -l {remote_file_path}"
launch_cmd = f"screen -d -m -S {session_name} top"

# 3. Launch the program in screen
print("Launching programs...")
output = client.run_command(launch_cmd)
client.join(output)

print("Done. Sessions are running on all hosts.")

