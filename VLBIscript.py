#! /opt/python_envs/env_vlbi_obs/bin/python
#
# Python script that uses a vex file and then controls the array to
# point to various sources, do tsys, turn phasing on/off etc. 
# This also has a simulation mode.
#
# For Help see
# python3 ./VLBIscript.py -h 
# 
# Inspired by ------
# 1. Messages on ehtobs_main channel on EHT slack (Remo/Amy/Greg/Vincent)
# 2. Thanks very much to Jongho Park and Keeichi Asada for providing me with the
# script the GLT uses. It was very helpful. 
#
import datetime
import time
import sys
import subprocess
import argparse
import logging
from VLBIscriptsubs import make_blk_dicts, make_source_dicts, make_scans_dicts
from VLBIscriptsubs import lookup_source, lookup_source_simulate 
from VLBIscriptsubs import check_source_el, move_to_source

# Parse arguments
def get_args():
    desc_str = """VLBIscript for SMA
    Example: python3 ./VLBIscript.py -f e25f08.vex
    To Simulate: python3 ./VLBIscript.py -f e25e09.vex -s -t  20250408_043000"""
    parser = argparse.ArgumentParser(description=desc_str)

    # Required argument --vexfile
    parser.add_argument('--vexfile', '-f',type=str, help="Input file", required=True)

    # Conditional argument --time and --simulate; both needed
    parser.add_argument('--simulate', '-s', action='store_true', default=False, help='Simulate')
    parser.add_argument('--time', '-t', type=str, required=False, help='Simulate Time: 20250408_043000')

    args = parser.parse_args()

    # Check if --simulate is provided, and if so, ensure --time is also supplied
    if args.simulate and not args.time:
        print("Error: --time is required if --simulate is provided")
        sys.exit(1)
    if not args.time:
        args.time = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    return args.vexfile, args.simulate, args.time


# This loops over all scans 
def main_source_loop(scan_contents_dict, source_contents_dict,simulate, time_simulate):
    #dt_object = datetime.datetime.fromtimestamp(time_simulate)
    #print(dt_object.strftime("%Y-%m-%d %H:%M:%S"))
    #print(simulate, time_simulate)
    for key,val in scan_contents_dict.items():
        if val['is_sma_scan']:
            if simulate:
                currtime = time_simulate
            else:
                currtime = datetime.datetime.now().timestamp()
            scanstarttime=time.mktime(datetime.datetime.strptime(val['start'],"%Yy%jd%Hh%Mm%Ss").timetuple())
            if currtime > scanstarttime + float(val['duration']):
                print("Scan end time for ",val['scan_name']," is past")
                print("Moving to next scan")
            elif (currtime > scanstarttime) and (currtime < scanstarttime + float(val['duration'])):
                print("Inside a scan: ",val['scan_name'])
                source = val['source']
                ra = source_contents_dict[source]['ra']
                dec = source_contents_dict[source]['dec']
                phasing = source_contents_dict[source]['phasing']
                print("Source is ",source," At RA = ", ra, " And Decl. = ",dec)
                print("Inside a scan. Moving to source.")
                dotsys = False
                currtime = move_to_source(source, ra, dec, dotsys, simulate, time_simulate)
                # Wait till scan is done
                if simulate:
                    time_simulate = scanstarttime + float(val['duration'])
                    print("Scan is done at time ", datetime.datetime.fromtimestamp(time_simulate).strftime("%d %b %Y %H:%M:%S"))
                    currtime = time_simulate
                else:
                    currtime = datetime.datetime.now().timestamp()
                    #print("Current time is ",datetime.datetime.fromtimestamp(currtime).strftime("%d %b %Y %H:%M:%S"))
                    #print("Scan end time is ",datetime.datetime.fromtimestamp(scanstarttime + float(val['duration'])).strftime("%d %b %Y %H:%M:%S")) 
                    print("Waiting for scan to finish in ",str(scanstarttime + float(val['duration'])-currtime+2)," seconds")
                    subprocess.run(["sleep",str(scanstarttime + float(val['duration'])-currtime + 2)])
                    currtime = datetime.datetime.now().timestamp()
                    print("Scan is done at time ", datetime.datetime.fromtimestamp(currtime).strftime("%d %b %Y %H:%M:%S"))
            else:
                print("####################")
                print("Next scan ",val['scan_name']," starts in approx ", scanstarttime - currtime," seconds")
                source = val['source']
                ra = source_contents_dict[source]['ra']
                dec = source_contents_dict[source]['dec']
                phasing = val['phasing']
                print("Source is ",val['source']," At RA = ", ra, " And Decl. = ",dec," ; Phasing = ", phasing)
                dotsys = True
                move_to_source(source,ra,dec,dotsys,simulate, time_simulate,phasing)
                # Wait till scan is done
                if simulate:
                    time_simulate = time_simulate + scanstarttime + float(val['duration'])-currtime
                    print("Waiting for scan to finish in ",str(scanstarttime + float(val['duration'])-currtime)," seconds")
                    print("Scan is done at time ", datetime.datetime.fromtimestamp(time_simulate).strftime("%d %b %Y %H:%M:%S"))
                    currtime = time_simulate
                else:
                    currtime = datetime.datetime.now().timestamp()
                    print("Waiting for scan to finish in ",str(scanstarttime + float(val['duration'])-currtime)," seconds")
                    subprocess.run(["sleep",str(scanstarttime + float(val['duration'])-currtime)])
                    currtime = datetime.datetime.now().timestamp()
                    print("Scan is done at time ", datetime.datetime.fromtimestamp(currtime).strftime("%d %b %Y %H:%M:%S"))
        else:
            print("####################")
            print("SMA is not in this scan ",val['scan_name'])
            print("Moving to next scan")
        print("")
    print("####################")
    print("All scans finished in this vex file.")
    print("####################")

    

def main():
    filename, simulate, time_simulate = get_args()
    time_simulate_ts = time.mktime(datetime.datetime.strptime(time_simulate,"%Y%m%d_%H%M%S").timetuple())
    #print(time_simulate_ts)
    file = open(filename,"r").readlines()

    # Construct dictionaries
    blk_names_list, blk_contents_dict = make_blk_dicts(file)
    #print(blk_contents_dict['SCHED'])
    source_names_list, source_contents_dict = make_source_dicts(blk_contents_dict['SOURCE'])
    scan_names_list, scan_contents_dict = make_scans_dicts(blk_contents_dict['SCHED'])
    #print(scan_contents_dict)
    main_source_loop(scan_contents_dict, source_contents_dict,simulate, time_simulate_ts)


if __name__ == "__main__":
    main()

