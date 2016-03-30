__author__ = 'natelawrence'

import boto3
import ssh
import time
import numpy as np
from tqdm import tqdm

class instances(object):
    def __init__(self,puts,cmds,gets,numInstance = 15, sleeptime=30):
        self.numInstance = numInstance
        self.sleeptime = sleeptime #time to pause after every loop over instances
        self.instanceList = [None] * numInstance
        #self.currentState = ['empty'] * numInstance
        self.sshList = [None] * numInstance
        self.cmdIndList = []
        self.instanceCmds = [None] * numInstance
        self.isRunning = [0] * numInstance

        # Old code not planning to use
        #states = ['empty','pending','running','executing','finished','killing','terminated']
        #actions = ['launch','wait','create ssh copy and execute','check if complete','copy files stop ssh and kill','wait','remove inst']
        #self.stateActions = OrderedDict(zip(states,actions))

        self.nextActionList = [self.launch] * numInstance

        # info for AWS ec2
        self.ec2 = boto3.resource('ec2')
        self.ImageId = 'ami-f7433e97'
        self.KeyName = 'KeyPair150805'
        self.InstanceType = 't1.micro'
        self.SecurityGroupIds = ['sg-d0bcaeb5']
        self.key = '~/.ssh/KeyPair150805.pem'
        self.username = 'ubuntu'

        # lists of files to copy to and from remote on each server. Each element can be a list of files
        self.puts = puts
        self.gets = gets
        # list of commands to run on remote server
        self.cmds = cmds
        self.runTimeList = [[]] * len(cmds)

        assert len(puts) == len(gets)
        assert len(puts) == len(cmds)
        self.instanceCmds = [None] * len(cmds)

    def check_instance_states(self):
        for num, inst in enumerate(self.instanceList):
            if not(inst):
                self.currentState[num] = 'empty'
                continue
            else:
                # update instance object from ec2
                inst = self.ec2.Instance(id = inst.id)
                self.instanceList[num] = inst
                state = inst.state['Name']

            if state == 'pending':
                self.currentState[num] = 'pending'
            elif state == 'terminated':
                self.currentState[num] = 'terminated'
            elif state == 'running' and not(self.sshList[num]):
                self.currentState[num] = 'running'
            elif state == 'shutting-down' and self.sshList[num]:
                self.currentState[num] = 'killing'

    def runCmds(self):
        # loop over list of instances starting each one and advancing each
        if len(self.cmds) == 0 and sum(self.isRunning) == 0: # if no commands left and nothing running
            return
        for num in range(0, self.numInstance):
            action = self.nextActionList[num]
            action(num)
            print 'Instance number {} has next action {}'.format(num,action)
        time.sleep(self.sleeptime)
        self.runCmds()

    def launch(self,num):
        # launch a single instance and put details into the 'num'th element of list
        if len(self.puts)>0:
            self.instanceCmds[num] = (self.puts.pop(0), self.cmds.pop(0), self.gets.pop(0))
        else:
            return
        instance = self.ec2.create_instances(ImageId=self.ImageId, MinCount=1, MaxCount=1,
                                            KeyName=self.KeyName,
                                            InstanceType=self.InstanceType,
                                            SecurityGroupIds=self.SecurityGroupIds)
        self.instanceList[num] = instance[0]
        #self.currentState[num] = 'pending'
        self.nextActionList[num] = self.wait_while_pending
        self.isRunning[num] = 1

    def wait_while_pending(self,num):
        # check if instance still pending
        inst = self.instanceList[num]
        inst = self.ec2.Instance(id=inst.id)
        self.instanceList[num] = inst

        if inst.state['Name'] == 'running':
            # check status to see if initialization passed
            instanceStatus = self.ec2.meta.client.describe_instance_status()['InstanceStatuses']
            initStatus = [item[u'InstanceStatus'][u'Status'] for item in instanceStatus if item[u'InstanceId'] == inst.id][0]
            if initStatus == 'ok':
                self.nextActionList[num] = self.create_ssh_and_execute


    def create_ssh_and_execute(self,num):
        # to be called once instance is provisioned, create ssh session and execute commands
        inst = self.instanceList[num]
        sshconn = ssh.Connection(inst.public_dns_name,username=self.username,private_key=self.key)
        self.sshList[num] = sshconn

        # copy files to server
        assert isinstance(self.instanceCmds[num][1], str) or isinstance(self.instanceCmds[num][0], list)
        if isinstance(self.instanceCmds[num][0], list):
            for item in self.instanceCmds[num][0]:
                sshconn.put(item)
        elif isinstance(self.instanceCmds[num][0], str):
            sshconn.put(self.instanceCmds[num][0])

        # run commands
        assert isinstance(self.instanceCmds[num][1], str)
        sshconn.execute_nooutput(self.instanceCmds[num][1])

        self.nextActionList[num] = self.check_if_complete

    def check_if_complete(self,num):
        # to be called once code executes, copy files back to local directory, terminated instance
        sshconn = self.sshList[num]
        output = sshconn.execute('ps -u ubuntu | grep python')
        if len(output) == 0:
            self.nextActionList[num] = self.copy_files_stop_ssh_kill
        else:
            temp = output[0].split(':')
            hour, minute, sec = (int(temp[0][-2:]),int(temp[1]),int(temp[2][:2]))
            t = hour*3600+minute*60+sec

    def copy_files_stop_ssh_kill(self,num):
        # to be called once code executes, copy files back to local directory, terminated instance
        sshconn = self.sshList[num]

        # copy files from server
        assert isinstance(self.instanceCmds[num][1], str) or isinstance(self.instanceCmds[num][0], list)
        if isinstance(self.instanceCmds[num][2], list):
            for item in self.instanceCmds[num][2]:
                sshconn.get(item)
        elif isinstance(self.instanceCmds[num][2], str):
            sshconn.get(self.instanceCmds[num][2])

        # close ssh
        sshconn.close()
        self.sshList[num] = None
        # terminate instance
        inst = self.instanceList[num]
        inst.terminate()
        self.nextActionList[num] = self.remove_inst

    def remove_inst(self, num):
        # to be called once instance is terminated, remove from list and set back to beginning state
        inst = self.instanceList[num]
        inst = self.ec2.Instance(id=inst.id)
        self.instanceList[num] = inst

        if inst.state['Name'] == 'terminated':
            self.nextActionList[num] = self.create_ssh_and_execute
            self.instanceList[num] = None
            self.nextActionList[num] = self.launch
            self.isRunning[num] = 0

def main():

    # # test method with AWSTest.py
    # numInstance = 2
    # puts = ['AWSTest.py'] * 5
    # cmds = ['python AWSTest.py File{}.txt'.format(str(i)) for i in range(1,6)]
    # gets = ['File{}.txt'.format(str(i)) for i in range(1,6)]
    # inst = instances(puts, cmds, gets, numInstance=numInstance)
    # inst.runCmds()

    # Run jobs to scrape business names
    # numInstance = 1
    # puts = ['ScrapeYelp.py']
    # cmds = ['python ScrapeYelp.py 37.2 38 -122.031 -122.03 BusinessListTest.csv >> output.txt 2>&1']
    # gets = ['BusinessListTest.csv']
    # inst = instances(puts, cmds, gets, numInstance=numInstance)
    # inst.runCmds()
    #
    # #get business names for bay area
    numInstance = 15
    latbounds = [37.2,38]
    longbounds = [-122.6,-121.7]
    longstep = .01

    cmds =[]
    gets = []
    for ind, lstart in enumerate(np.arange(longbounds[0],longbounds[1],longstep)):
        cmds.append('python ScrapeYelp.py {} {} {} {} BizNames{}.csv >> output{}.txt 2>&1'.format(latbounds[0],latbounds[1],
                                                                                            lstart,lstart+longstep,
                                                                                            ind,ind))
        gets.append(['BizNames{}.csv'.format(ind),'output{}.txt'.format(ind)])
    puts = ['ScrapeYelp.py'] * len(gets)
    inst = instances(puts, cmds, gets, numInstance=numInstance)
    inst.runCmds()

if __name__ == "__main__":
    main()