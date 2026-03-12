#! /opt/python_envs/env_vlbi_obs/bin/python
from pssh.clients import ParallelSSHClient
import os
import argparse



hosts = ['recorder1', 'recorder2', 'recorder3', 'recorder4']
user = "oper"
pkey_path = os.path.expanduser("~/.ssh/id_rsa_tenzing_mk6")  # Your private key

# Specify your private key path here
client = ParallelSSHClient(hosts, pkey=pkey_path, user=user)

def get_args():
    parser = argparse.ArgumentParser(description="Example of mutually exclusive true/false arguments.")
    group = parser.add_mutually_exclusive_group(required=True)

    group.add_argument("--status", action="store_true", help="Enable the feature (sets feature_status to True)")
    group.add_argument("--packets", action="store_true", help="Enable the feature (sets feature_status to True)")
    group.add_argument("--hammer", action="store_true", help="Disable the feature (sets feature_status to False)")
    group.add_argument("--M6log", action="store_true", help="Disable the feature (sets feature_status to False)")
    args = parser.parse_args()
    return args

def get_recorder_status():
    output = client.run_command('cat ~/obs/Oct2018/Mk6-status.cmd | da-client')
    loop_output(output)

def get_recorder_packets_status():
    output = client.run_command('for ii in 2 3 4 5 ; do echo eth${ii}; timeout 1s tcpdump -c 1 -i eth${ii}; done')
    loop_output(output)

def get_recorder_hammer_logs():
    output = client.run_command('grep hammer nohup.out | grep oper | grep logs | tail -4')
    loop_hammer_output(output)

def get_recorder_M6log_filename():
    output = client.run_command('ls -tr obs/logs | tail -1')
    loop_M6log_output(output)

def loop_output(output):
    # Iterate through results as they complete
    for host_out in output:
        for line in host_out.stdout:
            print(f"{host_out.host}: {line}")

def loop_hammer_output(output):
    # Iterate through results as they complete
    for host_out in output:
        for line in host_out.stdout:
            client2 = ParallelSSHClient([host_out.host], pkey=pkey_path, user=user)
            log_file_name = line.split()[3]
            output2 = client2.run_command('tail -2 '+log_file_name)
            for host_out2 in output2:
                for line2 in host_out2.stdout:
                    print(f"{host_out2.host}: {log_file_name} {line2}")

def loop_M6log_output(output):
    # Iterate through results as they complete
    for host_out in output:
        for line in host_out.stdout:
            client2 = ParallelSSHClient([host_out.host], pkey=pkey_path, user=user)
            log_file_name = line.split()[0]
            output2 = client2.run_command('tail -2 '+log_file_name)
            for host_out2 in output2:
                for line2 in host_out2.stdout:
                    print(f"{host_out2.host}: {log_file_name} {line2}")

args = get_args()

if args.status:
    get_recorder_status()
if args.packets:
    get_recorder_packets_status()
if args.hammer:
    get_recorder_hammer_logs()
