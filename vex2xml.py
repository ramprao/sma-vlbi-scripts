#! /opt/python_envs/env_vlbi_obs/bin/python
# Copyright 2011 MIT Haystack Observatory
# 
# This file is part of Mark6 / 5C and converts a standard vex file
# into the appropriate xml file to be processed by the RDBE MarkX
# Command and control program.
# 
# Mark6 is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, version 2 of the License.
# 
# Mark6 is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with Mark6.  If not, see <http://www.gnu.org/licenses/>.

#Edited for Jan EHT run 2015 - Jay Blanchard. Edits line 83 and 389

import subprocess
import time
import datetime
import calendar
import readline
import getopt
import sys
import os
import string

class Station:
    station_dict = {
        #st    LCP/low    st    LCP/upper  st    RCP/lower  st    RCP/upper
        'Az': 'SMTO',
        'A1': 'SMTOLW',  'A2': 'SMTOLU',  'A3': 'SMTORW',  'A4': 'SMTORU',  
        'Ca': 'CARMA',   
        'K1': 'CARMAFLW','K2': 'CARMAFLU','K3': 'CARMAFRW','K4': 'CARMAFRU',
        'K5': 'CARMACMP',
        'Hi': 'JCMTSMA',   
        'H1': 'SMALW',   'H2': 'SMALU',   'H3': 'JCMTRW',  'H4': 'JCMTRU',
        # testing names for apr04b.vex
        'AZ': 'smto', 'Cm': 'karma', 'SC': 'smacomp', 'SP': 'smaphas'
    }
    equiv_map = {
        #st    equiv
        'A1': 'Az', 'A2': 'Az', 'A3': 'Az', 'A4': 'Az',
        'K1': 'Ca', 'K2': 'Ca', 'K3': 'Ca', 'K4': 'Ca', 'K5': 'Ca',
        'H1': 'Hi', 'H2': 'Hi', 'H3': 'Hi', 'H4': 'Hi'
    }

def parse_time(t):
        st = t[:t.find("y")] \
             + t[t.find("y")+1:t.find("d")] \
             + t[t.find("d")+1:t.find("h")] \
             + t[t.find("h")+1:t.find("m")] \
             + t[t.find("m")+1:t.find("s")]
        #print "starttime is ", st
        return(st)
        

class Scan:

        def __init__(self, experiment_name, source, station, start_time, duration, doy, name):
                self._experiment_name = experiment_name
                self._source = source
                self._station = station

                try:
                        self._station_code = Station.station_dict[station]
                except:
                        self._station_code = station

                self._start_time = int(start_time)
                self._duration = int(duration)
                self._end_time = int(start_time) + int(duration)

                #ddd = start_time[2:5]
                hh = int(start_time[7:9])
                mm = int(start_time[9:11])
                ss = int(start_time[11:13])
                #self._scan_name = '%s_%s_%3d-%02d%02d'%(experiment_name,
                #   self._station_code,ddd, hh,mm)
                #self._scan_name = '%s_%s_%03d-%02d%02d%02d'%(
                #self._scan_name = '%s_%s_%03d-%02d%02d'%(
                #        experiment_name, self._station, int(doy), hh, mm)
                #Edit for EHT run Jan 2015
                self._scan_name = '%03d-%02d%02d'%(int(doy),hh,mm)
                self._alt_name = '%s_%s_%s'%(
                        experiment_name, self._station, name)
                # experiment_name, self._station, int(doy), hh, mm, ss)
                #if (not self._scan_name == self._alt_name):
                #        print 'Warning: %s != %s'%(self._scan_name,
                #            self._alt_name)


        def __str__(self):
                return ''.join([
                        '<scan ',
                        'experiment="%s" '%self._experiment_name,
                        'source="%s" '%self._source,
                        'station_code="%s" '%self._station,
                        'start_time="%s" '%self._start_time,
                        'duration="%s" '%self._duration,
                        'scan_name="%s"'%self._scan_name,
                        '/>'
                        ])

        def args(self):
                return [ self._source, self._station,
                         str(self._start_time), str(self._duration) ]

        def late(self):
                if time.time() > self._end_time:
                        return True
                return False    


class ScheduleParser:

        def __init__(self,
            schedule_file, experiment_file_name, experiment_name, st):
                input_file = open(schedule_file, 'r')

                dlist = {}
                i = 0
                for line in input_file:
                        dlist[i] = line
                        #print "line ", line
                        i+=1
                input_file.close()

                state = 0
                exp_start_time=exp_end_time="0"
                scans = []
                station_dict = {}
                cnt = 0
                #print "len of dlist is %d" % len(dlist)
                
                while cnt < len(dlist):
                        #print "top cnt is %d" % (cnt)
                        l = dlist[cnt]
                        #print "line is %s" % l
                        l = l.strip()
                        f = l.split()

                        ###### FOR SKD FILE PROCESSING
                        if f[0] == '$SKED':
                                state = 1
                        elif f[0] == '$SOURCES':
                                state = 2
                        elif f[0] == '$STATIONS':
                                state = 3
                        ###### FOR VEX FILE PARSING
                        elif f[0] == '$SCHED;':
                                #print "SCHED and f[0] is ", f[0]                                
                                state = 4
                        elif f[0] == '$STATION;':
                                state = 5
                                #print "STATION and f[0] is ", f[0]                              
                        elif f[0] == '$EXPER;':
                                #print "EXPER and f[0] is ", f[0]
                                state = 6
                        elif f[0] == '$CODES' :
                                #print "breaking"
                                break


                        if state == 1:
                                source, t, stations = f[0], f[4], f[9] 
                                num_stations = len(stations)/2
                                offset = 9 + num_stations
                                durations = f[offset+2:]
                                stations = list(stations)
                                stations = [ stations[i] for i in range(0,
                                    len(stations)-1, 2) ]
                                for i in range(num_stations):
                                        t_l = list(t)
                                        yy = t[0:2]
                                        ddd = int(t[2:5])
                                        hh = int(t[5:7])
                                        mm = int(t[7:9])
                                        ss = int(t[9:11])

                                        # USE START TIME OF YYYYDDDHHMMSS
                                        start_time = str(2000+int(yy)) + t[2:11]
                                        scans.append( Scan(experiment_name, source, stations[i], start_time, int(durations[i]), ddd, 'noname')  )
                                        cnt += 1

                        elif state == 2:
                                cnt += 1
                                pass

                        elif state == 3:
                                if f[0] == 'A':
                                        code = f[1]
                                        name = f[2]
                                        station_dict[code] = name
                                cnt += 1
                                
                        elif state == 4:
                                #print "match SCHED state 4"
                                #print "l = ", l
                                #print "f = ", f
                                endscan = 0
                                sname = 'non-scan'
                                #print "endscan %d" % ( endscan)
                                while not endscan:
                                        #print "in while loop state 4 for cnt = %d" % cnt
                                        #print f[0]
                                        if f[0] ==  "endscan;":
                                                endscan = 1
                                                #print "setting endscan to 1"
                                                
                                        else:
                                                if f[0] == "scan":
                                                        sname = f[1].rstrip(';')
                                                        duration = 0
                                                        equivdur = 0
                                                elif not f[0] ==  "*":
                                                        #print "len of f is %d" % len(f)
                                                        for j in range (0, len(f),1):
                                                                #print f[j]
                                                                val = f[j][:f[j].find('=')]
                                                                if val == "start":
                                                                        #print "found start time ", f[j][f[j].find('=')+1:]
                                                                        t = f[j][f[j].find('=')+1:]
                                                                        start_time = parse_time(t)

                                                                        #print "starttime set to ", start_time
                                                                        print("At", start_time, end=' ')

                                                                        ddd = t[t.find("y")+1:t.find("d")]
                                                                        #print "(DOY %s)" % (ddd),
                                                                        
                                                                elif val == "source":
                                                                        #print "found source", f[j][f[j].find('=')+1:]
                                                                        #print "on", f[j][f[j].find('=')+1:-1],
                                                                        source = f[j][f[j].find('=')+1:-1]
                                                                        print("on %-10s" % (source), end=' ')
                                                                elif val == "station":
                                                                        #print "found station while looking for ", st
                                                                        proc_st = f[j][f[j].find('=')+1:f[j].find(':')]
                                                                        try:
                                                                            equivst = Station.equiv_map[proc_st]
                                                                        except:
                                                                            equivst = 'no-such-station'

                                                                        if proc_st == st:
                                                                                #print "Processing for %s station" % (proc_st),
                                                                                #print "at site %s" % (proc_st),
                                                                                #print "line is ", f[3]
                                                                                duration = int(f[3])
                                                                                #print "duration of recording is ", duration,
                                                                                #print "for %ss." % duration
                                                                                print("for %ss at %s." % (duration,proc_st))
                                                                                
                                                                        elif equivst == st:
                                                                                equivdur = f[3]
                                                                                print("for %ss at %s." % (equivdur,equivst))
                                                                
                                                #else:
                                                #       print "do nothing"
                                                        
                                                # --- INCREMENT THE i BY 1
                                                #print "i is %d" % (cnt)
                                                cnt += 1
                                                #print "len -dlist-y is %d" % len(dlist)
                                                
                                                if cnt < len(dlist):                                            
                                                        l = dlist[cnt]
                                                        l = l.strip()
                                                        f = l.split()                                           
                                                        #print "endscan line is %s" %f
                                                else:
                                                        endscan =1
                                                        #print "cnt execeeded list len, setting endscan to break out"
                                        
                                #source = f[0]
                                #t  = f[4]
                                #stations = f[9]
                                #print "end of while loop"
                                cnt += 1
                                if (duration > 0):
                                    scans.append( Scan(experiment_name, source, st, start_time, duration, ddd, sname) )
                                elif (equivdur > 0):
                                    scans.append( Scan(experiment_name, source, st, start_time, equivdur, ddd, sname) )
                                else:
                                    print("No duration for scan %s at %s" % (sname,start_time))

                        elif state == 5:
                                #print "station is %s state 5" % (st)
                                #print "l = ", l
                                #print "f = ", f
                                #if not f[0] ==  "*":
                                        #print "STATIONS:"
                                #else:
                                        #print "comment ignore"                         
                                if f[0] == st:
                                        
                                        code = f[1]
                                        name = f[2]
                                        station_dict[code] = name                       
                                cnt += 1
                                state = 0

                        elif state == 6:
                                #print "match EXPER state 6"
                                #print "l = ", l
                                #print "f = ", f
                                enddef = 0
                                #print "enddef %d" % ( enddef)
                                while not enddef:
                                        #print "in while loop state 6 for cnt = %d" % cnt
                                        #print f[0]
                                        if f[0] ==  "enddef;":
                                                enddef = 1
                                                #print "setting enddef to 1"
                                                cnt += 1                                
                                        else:
                                                if not f[0] ==  "*":
                                                        #print "len of f is %d" % len(f)
                                                        for j in range (0, len(f),1):
                                                                #print f[j]
                                                                val = f[j][:f[j].find('=')]
                                                                if val == "exper_name":
                                                                        #print "found start time ", f[j][f[j].find('=')+1:]
                                                                        t = f[j][f[j].find('=')+1:]
                                                                        start_time = ts_parse(t)
                                                                        
                                                                        print("starttime set to ", start_time)

                                                                        ddd = t[t.find("y")+1:t.find("d")]
                                                                        print("ddd is ", ddd)
                                                                        
                                                                elif val == "exper_nominal_start":
                                                                        #print "found nominal_start", f[j][f[j].find('=')+1:]
                                                                        exp_start_time=parse_time(f[j][f[j].find('=')+1:])
                                                                        print("exp_start_time is:", exp_start_time)

                                                                elif val == "exper_nominal_stop":
                                                                        #print "found nominal_stop ",  f[j][f[j].find('=')+1:]
                                                                        exp_end_time=parse_time(f[j][f[j].find('=')+1:])
                                                                        print("exp_end_time is:  ", exp_end_time)
                                                                        print()
                                                                
                                                #else:
                                                #       print "do nothing"
                                                        
                                                # --- INCREMENT THE i BY 1
                                                #print "i is %d" % (cnt)
                                                cnt += 1
                                                if cnt < len(dlist):                                            
                                                        l = dlist[cnt]
                                                        l = l.strip()
                                                        f = l.split()                                           
                                                        #print "enddef line is %s" %f
                                                else:
                                                        enddef=1
                                        
                                #source = f[0]
                                #t  = f[4]
                                #stations = f[9]
                                #print "end of while loop"
                                state = 0

                        else:
                                cnt +=1
                                state = 0
                        
                st_scans = [ s for s in scans]
                experiment_file = open(experiment_file_name, 'w')

                exp_st = '<experiment name="' + experiment_name
                exp_st += '" station="' +st + '" start="' +exp_start_time + '" '
                exp_st += ' end="' + exp_end_time +'"> \n'
                experiment_file.write(exp_st)
                try:
                    rdbe_ip = os.environ['rdbe']
                except:
                    rdbe_ip = "192.52.61.191"
                try:
                    mk5c_ip = os.environ['mk5c']
                except:
                    mk5c_ip = "192.52.61.132"
                config_st = "<config personality=PFBG_1_4.bin, "
                config_st+= "ioch=1:0-15, rdbe_ip=" + rdbe_ip
                config_st+= ",mark5c_ip=" + mk5c_ip + " />"
                #experiment_file.write('\t' + config_st + '\n')
                #commented out for EHT run Jan 2015
                for s in st_scans:
                        experiment_file.write('\t' + str(s) + '\n')
                experiment_file.write('</experiment>\n')

if __name__ == '__main__':

        helpstring = """
        Usage: vex2xml.py [options]

        where the options are:
          -f <file>     the vex file from which to create a schedule
          -s <XX>       the two letter station code to schedule
          -n <string>   site name of this station code
          -e <YY>       declares XX equivalent to YY

        Normally,

          vex2xml.py -f expt.vex -s XX

        is sufficient to schedule XX assuming it was in the expt.vex plan.
        However, if you want to schedule something not in the vex file:

          vex2xml.py -f expt.vex -s ZZ -n SLEEPY -e XX

        will schedule ZZ as if it was in the vex file as XX is.  For
        testing,

          vex2xml.py -f apr04b.new -s Az -e AZ

        should recreate apr04b.xml
        """

        parms = {'-f':"test.vex", '-s': 'Xx', '-n':"site-name", '-e':"Yy"}
        try:
                opts, pargs = getopt.getopt(sys.argv[1:], "f:s:n:e:")
        except getopt.GetoptError as msg:
                sys.exit(msg)
                
        for o,v in opts:
                parms[o] = v

        input_fn = str(parms['-f'])
        input_st = str(parms['-s'])
        input_sn = str(parms['-n'])
        input_eq = str(parms['-e'])

        # --- VERIFY STATION EXISTS IN STATION LIST
        if input_st in Station.station_dict:
                station = input_st
                print("Processing station -> %s" % (station))            
        else:
                Station.station_dict.update({input_st : input_sn})
                station = input_st
                print("Adding&using station -> %s (%s)" % (station, input_sn))

        # --- ADD Equivalence for input station
        if input_eq in Station.station_dict:
                Station.equiv_map.update({input_eq : input_st})
                print("Treating %s like %s" % (input_eq,Station.equiv_map[input_eq]))
        else:
                print("Unable to treat %s like %s" % (input_eq,input_st))

        # --- test if file exists
        if os.path.isfile(input_fn):
                start_pos = input_fn.rfind("/")
                exp = input_fn[start_pos+1:input_fn.find(".")]
                fn_out = input_fn[:input_fn.find(".")] + ".xml"
                print("Output filename is %s" % (fn_out))

                # --- GET EXPERIMENT NAME

                print("Parsing VEX file %s for %s at %s.\n" % (input_fn, exp, station))
                sp = ScheduleParser(input_fn, fn_out, exp, station)
        else:
                print("Input file %s does not exist" % (input_fn))
                print(helpstring)
                exit

#
# eof
#
