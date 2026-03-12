# Python subs for script that uses a vex file and then controls the array to
# point to various sources, do tsys, turn phasing on/off etc. 
#
# Inspired by ------
# 1. Messages on ehtobs_main channel on EHT slack (Remo/Amy/Greg/Vincent)
# 2. Thanks very much to Jongho Park and Keeichi Asada for providing me with the
# script the GLT uses. It was very helpful. 
#
import datetime
import time
import subprocess
import logging


# make_blk_dicts takes a first pass at the vex file and parses
# it into various blocks such as $SOURCE, $SCHED etc.
def make_blk_dicts(file):
    idx = 0
    inited = False
    blk_names_list = []
    blk_contents_dict = {}
    blk_contents = []

    for line in file:
        #print(line.strip())
        if not inited:
            if line.strip()[0] == "$":
                inited = True
                blk_name = line.strip()[1:-1]
                blk_names_list.append(blk_name)
                blk_contents = []
            else:
                pass
        else:
            if line.strip()[0] == "$":
                blk_contents_dict[blk_name] = blk_contents
                blk_name = line.strip()[1:-1]
                blk_names_list.append(blk_name)
                blk_contents = []
            else:
                blk_contents.append(line.strip())

    blk_contents_dict[blk_name] = blk_contents
    return blk_names_list, blk_contents_dict

# This takes the SOURCE block and extracts the various sources
# values such as ra, dec etc.
def make_source_dicts(source):
    inited = False
    source_names_list = []
    source_contents_dict = {}
    for line in source:
        if not inited:
            if line[0] == "s":
                inited = True
                source_name = line.strip()[1:-1].split("=")[1].strip()
                source_names_list.append(source_name)
                source_contents = []
            else:
                pass
        else:
            if line[0] == "s":
                source_contents_dict[source_name] = source_contents
                source_name = line.strip()[1:-1].split("=")[1].strip()
                source_names_list.append(source_name)
                source_contents = []
            else:
                if line[0] == "r":
                    ra = line.strip().split(";")[0].split("=")[1].strip().replace('h',':').replace('m',':').replace('s','')
                    dec = line.strip().split(";")[1].split("=")[1].strip().replace('d',':').replace("\'",":").replace('"','')
                    md = {'ra':ra, 'dec':dec}
                    source_contents = md
    source_contents_dict[source_name] = source_contents
    return source_names_list, source_contents_dict

# This parses the SCHED block and makes a list of
# scans with the content of each scan being the scannumber, source, start time, duration
# Also whether it will be regular phasing or passive phasing
def make_scans_dicts(sched):
    inited = False
    scan_names_list = []
    scan_contents_dict = {}
    for line in sched:
        #print(line)
        if not inited:
            if line.split()[0].strip() == "scan":
                inited = True
                scan_name = line[0:-1].split()[1].strip()
                scan_names_list.append(scan_name)
                is_sma_scan = False
                phasing = True
                scan_contents = {}
            else:
                pass
        else:
            if line.split()[0].strip() == "scan":
                scan_name = line[0:-1].split()[1].strip()
                scan_names_list.append(scan_name)
                is_sma_scan = False
                phasing = True
                scan_contents = {}
            else:
                if line.split()[0].split("=")[0] == "start":
                    start = line.split(";")[0].split("=")[1].strip()
                    source = line.split(";")[2].split("=")[1].strip()
                    #print(start,source)
                elif "SMA:AUTOPHASE_DETERMINE" in line.strip():
                    phasing = True
                elif "SMA:AUTOPHASE_APPLY" in line.strip():
                    phasing = False
                elif line.split()[0].strip().split("=")[0] == "station":
                    station = line.split(":")[0].split("=")[1].strip()
                    duration = line.split(":")[2].split()[0].strip()
                    #print(station)
                    if station == "Sw":                        
                        is_sma_scan = True
                        #print(scan_name)
                elif line[0:-1] == "endscan":
                    scan_contents = {'scan_name':scan_name, 'start':start, 
                                 'source':source, 'duration':duration, 
                                 'is_sma_scan':is_sma_scan, 'phasing':phasing}
                    scan_contents_dict[scan_name] = scan_contents
                        
    return scan_names_list, scan_contents_dict

# Runs the lookup command
def lookup_source(source,ra,dec):
    result = subprocess.run(["lookup","-s",source,"-r",ra,"-d",dec,"-e","2000"],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    az, el, sundistance = [float(x) for x  in result.stdout.decode().strip().split()]
    return az, el, sundistance

# Runs the lookup command in simulate mode
def lookup_source_simulate(source,ra,dec,time_simulate):
    date_time = datetime.datetime.fromtimestamp(time_simulate)
    time_simulate_str = date_time.strftime("%d %b %Y %H:%M:%S")
    result = subprocess.run(["lookup","-s",source,"-r",ra,"-d",dec,"-e","2000","-t",time_simulate_str],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    az, el, sundistance = [float(x) for x  in result.stdout.decode().strip().split()]
    return az, el, sundistance

# This checks source elevation
def check_source_el(source,ra,dec,simulate,time_simulate):
    print("Checking if source is up via lookup")
    if simulate:
        az, el, sundistance = lookup_source_simulate(source,ra,dec,time_simulate)
    else:
        az, el, sundistance = lookup_source(source,ra,dec)
    if sundistance < 25.01:
        print("#### DANGER: SOURCE IS TOO CLOSE TO THE SUN ####")
        sys.exit(0)

    print("Source is at elevation ",el)

    # Check if within el limits
    if (el < 15.0 or el > 87.0):
        if el < 15.0:
            print("Source is below elevation limits")
            elwait = (15.0-el)*245.0
        else:
            elwait = (el-87.0)*480.0
            print("Source is above elevation limits")
        print("Sleeping for ",elwait," seconds")
        if simulate:
            time_simulate = time_simulate + elwait
        else:
            time.sleep(elwait)

    if (el < 15.0 or el > 87.0):
        while (el < 15.0) or (el > 87.0):
            print("Sleeping 10 seconds")
            if simulate:
                time_simulate = time_simulate + 10
                az, el, sundistance = lookup_source_simulate(source,ra,dec, time_simulate)
            else:
                time.sleep(10)
                az, el, sundistance = lookup_source(source,ra,dec)
        print("Source is now observable")

    if simulate:
        az, el, sundistance = lookup_source_simulate(source,ra,dec,time_simulate)
    else:
        az, el, sundistance = lookup_source(source,ra,dec)
    print("Source az, el, sundistance = ",az, el, sundistance)
    if simulate:
        return az, el, sundistance, time_simulate
    else:
        return az, el, sundistance
        
        
# This is the function that actually moves it to the specified source
def move_to_source(source,ra,dec,dotsys,simulate,time_simulate,phasing):

    if simulate:
        az, el, sundistance, time_simulate = check_source_el(source,ra,dec,simulate,time_simulate)
        time_simulate = time_simulate + 60
        print("Simulate setcorrelator + observe + tsys")
        currtime = time_simulate
    else:
        az, el, sundistance = check_source_el(source,ra,dec,simulate,time_simulate)
        # Pause phasing
        print("Pausing phasing during slew")
        subprocess.run(["setCorrelator","-d"]) 
        # Send observe command
        print("Moving to source ",source)
        subprocess.run(["observe","-s",source,"-r",ra,"-d",dec,"-e","2000"]) 
        # Do a tsys
        if dotsys:
            print("Doing a tsys")
            subprocess.run(["tsys"])
        # Wait for antennas to reach
        subprocess.run(["antennaWait"])
        # Resume phasing
        if phasing:
            print("Resuming phasing")
            subprocess.run(["setCorrelator","-e"])
        else:
            print("No phasing")
            subprocess.run(["setCorrelator","-d"])
        currtime = datetime.datetime.now().timestamp()
    return currtime

