#!/bin/python

#  PRA.py
#  
#
#  Created by MIMIFIR Pierre-Jacques on 10/04/2019.
#  Purpose : The purpose of this script is make all required actions
#
#

import sys
import paramiko

def update_pure_host_wwn(lpar_name,wwn)
    

def getLpars(hmc,hmc_user,hmc_password,sys,excluded_lpar):
    sshclient=SSHClient()
    sshclient.load_systm_host_keys()
    try:
        sshclient.connect(hmc,username=hmc_user,password=hmc_passwor)
        stdin, stdout, stderr = client.exec_command('lsyscfg -r sys -F name')
        for system in stdout.read():
            stdin, stdout, stderr = client.exec_command('lshwres -r virtualio --rsubtype fc --level lpar -m ' + system + " -F 'lpar_name;wwpns'")
            for line in stdout.read():
                array=line.split(";")
                if len(array) > 0:
                    lpar_name = array[0]
                    array = array[1].split(',')
                    wwn1  = array[0]
                    wwn2  = array[1]
                    update_pure_host_wwn(lpar_name,wwn1)
                    update_pure_host_wwn(lpar_name,wwn2)

except paramiko.ssh_exception.SSHException:
    print "Erreur de connexion à la hmc %s",hmc_user

def help():
    print 'PRA.py -H hmc -u hmc-user -w hmc-password -P purestorage-array-ip -s purestorage-array-user -p purestorage-array-password'
    sys.exit(2)

def main(argv):
    hmc=''
    hmc_user=''
    hmc_password=''
    pure=''
    pure_user=''
    pure_password=''
    sys=''
    
    try:
        opts, args = getopt.getopt(argv,"hpwsPH",["hmc=","hmc-user=","hmc-password="])
    
    except getopt.GetoptError:
        help()
        exit -1
    for opt, arg in opts:
        if opt == '-h':
            help()
        elif opt in ("-H", "--hmc"):
            hmc = arg
        elif opt in ("-u", "--hmc-user"):
            hmc_user=arg
        elif opt in ("-w", "--hmc-password"):
            hmc_password=arg
        elif opt in ("-P", "--purestorage"):
           pure = arg
        elif opt in ("-s", "--purestorage-user"):
            pure_user=arg
        elif opt in ("-p", "--purestorage-password"):
            pure_password-password=arg

    lpars=getLpars(hmc,hmc_user,hmc_passwor,sys,excluded_lpar)

