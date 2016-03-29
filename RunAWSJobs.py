__author__ = 'natelawrence'

import boto3
import ssh
import numpy as np
import time
import csv
from collections import OrderedDict

class instances(object):
    def __init__(self,numInstance = 15):
        self.numInstance = numInstance
        self.instanceList = []
        states = ['terminated','provisioning','running','sshed','executing','finished','killing']
        actions = ['launch','wait','create ssh','copy and execute','wait','copy and kill','wait']
        self.stateActions = OrderedDict(zip(states,actions))
        self.ec2 = boto3.resource('ec2')
        self.ImageId = 'ami-5583f535'
        self.KeyName = 'KeyPair150805'
        self.InstanceType = 't1.micro'
        self.SecurityGroupIds = ['sg-76170113']
        self.key = '~/.ssh/KeyPair150805.pem'

    def launch(self,num):
        #launch a single instance and put details into the 'num'th element of list
        instance = self.ec2.create_instances(ImageId=self.ImageId, MinCount=1, MaxCount=1,
                                            KeyName = self.KeyName,
                                            InstanceType=self.InstanceType,
                                            SecurityGroupIds = self.SecurityGroupIds)
        self.instanceList[num] = instance

def main():

    numInstance = 15

    ec2 = boto3.resource('ec2')

    instanceList = ec2.create_instances(ImageId='ami-5583f535', MinCount=numInstance, MaxCount=numInstance,
                                        KeyName = 'KeyPair150805',
                                        InstanceType='t1.micro',
                                        SecurityGroupIds = ['sg-76170113'])

    dnsList = []
    for status in ec2.meta.client.describe_instance_status()['InstanceStatuses']:
        inst = ec2.Instance(id = status['InstanceId'])
        dnsList.append(inst.public_dns_name)

    blockLimits = [0,30]
    step = (blockLimits[1]-blockLimits[0])/float(numInstance)
    blockStart = list(np.round(np.arange(blockLimits[0],blockLimits[1]-step+.001,step)).astype(int))
    blockStop = list(np.round(np.arange(blockLimits[0]+step,blockLimits[1]+.001,step)).astype(int))

    key = '~/.ssh/KeyPair150805.pem'
    mysshList = []
    for dns in dnsList:
        connection = dns
        mysshList.append(ssh.Connection(connection,username='ubuntu',private_key=key))

    BizFilename = lambda start,stop: 'YelpBusinessList5_{}_{}.csv'.format(start,stop)
    ReviewFilename = lambda start,stop: 'YelpReviewList5_{}_{}.csv'.format(start,stop)
    outputFilename = lambda start,stop: 'output5_{}_{}.txt'.format(start,stop)

    for bb in range(0,numInstance):
        myssh = mysshList[bb]
        myssh.put('ScrapeYelp.py')
        start = blockStart[bb]
        stop = blockStop[bb]
        myssh.execute_nooutput('python ScrapeYelp.py {} {} {} {} >> {} 2>&1'.format(start,stop,BizFilename(start,stop),
                                                                                         ReviewFilename(start,stop),
                                                                                        outputFilename(start,stop)))
    # list of running python processes to check when code finishes
    tList = [0]*numInstance
    finished = [0]*numInstance
    while min(finished) == 0:
        for bb in range(0,numInstance):
            myssh = mysshList[bb]
            output = myssh.execute('ps -u ubuntu | grep python')
            if len(output) == 0:
                finished[bb] = 1
            else:
                temp = output[0].split(':')
                hour, minute, sec = (int(temp[0][-2:]),int(temp[1]),int(temp[2][:2]))
                tList[bb] = hour*3600+minute*60+sec
        with open('TimeFile.txt','a') as timefile:
            writer = csv.writer(timefile, delimiter=' ')
            writer.writerow(tList)
        time.sleep(30)

    for bb in range(0,numInstance):
        myssh = mysshList[bb]
        start = blockStart[bb]
        stop = blockStop[bb]
        try:
            myssh.get(outputFilename(start,stop))
        except:
            print 'Cant find file {}'.format(outputFilename(start,stop))
        try:
            myssh.get(BizFilename(start,stop))
        except:
            print 'Cant find file {}'.format(BizFilename(start,stop))
        try:
            myssh.get(ReviewFilename(start,stop))
        except:
            print 'Cant find file {}'.format(ReviewFilename(start,stop))
        myssh.close()


if __name__ == "__main__":
    main()