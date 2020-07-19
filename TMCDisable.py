# Author: ybendre, jijumonv, jparappurath
# Test: tmc_disable
# This is TMC Disable Workflow

import json
import json
import argparse
from TMCHandler import TMC
from WCPFetcher import WCPFetcher
import time

def workflow(vc, username, password, tmc_url, api_token, org_id, lcp_prefix, monitor_time_in_min, yaml_action, force_delete):
    tmc_workflow = TMCWorkFlow(vc, username, password, tmc_url, api_token, org_id, lcp_prefix, yaml_action)
    tmc_workflow.fillInfo()
    tmc_workflow.deregister_cluster()
    tmc_workflow.monitor_deregistration(monitor_time_in_min)
    tmc_workflow.delete_lcp(force_delete)



class TMCWorkFlow:

    def __init__(self, vc, username, password, tmc_url, api_token, org_id, lcp_prefix, yaml_action):
        self.vc = vc
        self.username = username
        self.password = password
        self.tmc_url = tmc_url
        self.api_token = api_token
        self.org_id = org_id
        self.lcp_prefix = lcp_prefix
        self.yaml_action = yaml_action
        self.tmc_handler = TMC(self.tmc_url, self.api_token, self.org_id)
        self.wcp_fetcher = WCPFetcher(self.vc, self.username, self.password)
        self.wcp_info = self.wcp_fetcher.wcp_info
        print("WCP Clusters: ")
        print(self.wcp_info)
        print("Initialized successfully")

    def fillInfo(self):
        for w in self.wcp_info:
            print("Cluster: "+w)
            try:
                lcp_name = lcp_prefix + "-vc-" + self.vc.replace(".", "-") + "-w-" + self.wcp_info[w]["IP"].replace(".", "-") + "lcp"
                self.wcp_info[w]["lcp_name"] = lcp_name
                print("LCP: "+lcp_name)

            except Exception as e:
                print(str(e))

        print("Completed")


    def delete_lcp(self, force=True):
        for w in self.wcp_info:
            print("Cluster: "+w)
            try:
                print("Deleting LCP for "+self.wcp_info[w]["IP"])
                print("")
                lcp_name = lcp_prefix + "-vc-" + self.vc.replace(".", "-") + "-w-" + self.wcp_info[w]["IP"].replace(".", "-") + "lcp"
                myinfo = self.tmc_handler.delete_local_control_plane(lcp_name, force)
                self.wcp_info[w]["lcp"] = myinfo
                self.wcp_info[w]["lcp_name"] = lcp_name
                print("Completed")
            except Exception as e:
                print(str(e))

    def deregister_cluster(self):
        for w in self.wcp_info:
            print("Cluster: "+w)
            try:
                print("Deregistering for " + self.wcp_info[w]["IP"])
                print("Get Domain: ")
                domain = w.split(":")[0].split("domain-")[1]
                print(domain)
                if 'apply' in self.yaml_action:
                    cmd0 = 'kubectl delete agentinstall tmc-agent-installer-config -n svc-tmc-'+domain
                    self.wcp_fetcher.run_command_on_wcp(w, cmd0)
                    print("Sleeping for 5 sec.")
                    time.sleep(5)

                cmd1 = 'curl -k -X GET "https://raw.githubusercontent.com/yogeshbendre/ytmc/master/tmc_deregistration_template.yaml" -o /root/tmc_deregistration_template.yaml'
                self.wcp_fetcher.run_command_on_wcp(w, cmd1)
                time.sleep(1)

                cmd2 = "cat /root/tmc_deregistration_template.yaml | sed 's/<namespace>/svc-tmc-"+domain+"/g' > /root/tmc_deregister.yaml"
                self.wcp_fetcher.run_command_on_wcp(w,cmd2)
                time.sleep(1)
                print("Generated YAML for TMC Registration")

                cmd3 = "cat  /root/tmc_deregister.yaml"
                self.wcp_fetcher.run_command_on_wcp(w, cmd3)
                time.sleep(1)
                if 'apply' in self.yaml_action:
                    cmd4 = "kubectl apply -f  /root/tmc_deregister.yaml"
                    self.wcp_fetcher.run_command_on_wcp(w, cmd4)
                    time.sleep(1)
                print("Completed")
            except Exception as e:
                print(str(e))


    def is_lcp_healthy(self, lcp_name):
        myresp = self.tmc_handler.get_local_control_plane(lcp_name)
        try:
            lcp_info = myresp.json()
            if("healthy" in lcp_info["localcontrolplane"]["status"]["health"].lower()):
                print("LCP: "+lcp_name+" seems to be healthy.")
                return True
            else:
                print("LCP: " + lcp_name + " seems to be unhealthy.")
                return False
        except Exception as e:
            print("Health check for "+lcp_name+" failed with "+str(e))
            return False



    def monitor_deregistration(self, monitor_time_in_min = 5):
        print("Monitoring deregistration for "+str(monitor_time_in_min)+" minutes...")
        t = 0
        areAllHealthy = False
        healthStates = {}
        while t <= monitor_time_in_min:
            areAllHealthy = False
            for w in self.wcp_info:
                try:
                    print("Check disconnection of "+self.wcp_info[w]["lcp_name"])
                    myhealth = self.is_lcp_healthy(self.wcp_info[w]["lcp_name"])
                    areAllHealthy = areAllHealthy or myhealth
                    healthStates[self.wcp_info[w]["lcp_name"]] = not myhealth
                except Exception as e:
                    healthStates[self.wcp_info[w]["lcp_name"]] = False
            if(not areAllHealthy):
                print("All the control planes are in disconnected states.")
                for lcp in healthStates.keys():
                    print("LCP: "+lcp+" Disconnected: "+str(healthStates[lcp]))
                break
            else:
                print("Some LCP are still healthy. Sleeping for 1 min. Remaining Time: "+str(monitor_time_in_min-t)+" min")
                time.sleep(60)
                t = t + 1

        if(not areAllHealthy):
            return True
        print("Monitoring Time Out and still few LCPs are healthy.")
        for lcp in healthStates.keys():
            print("LCP: " + lcp + " Disconnected: " + str(healthStates[lcp]))
        return False


#Driver code
if __name__ == "__main__":

    vc = None
    username = None
    password = None
    tmc_url = None
    api_token = None
    org_id = None
    lcp_prefix = None
    force = None
    yaml_action = None
    monitor_time_in_min = None
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--vcenter", help="Specify vCenter", type=str)
    parser.add_argument("-u", "--username", type=str, help="Specify vCenter ssh username. Default: root")
    parser.add_argument("-p", "--password", type=str, help="Specify vcenter ssh password. Default: Admin!23")

    parser.add_argument("-t", "--tmcurl", help="Specify TMC Base URL.",type=str)
    parser.add_argument("-a","--apitoken", type=str, help="Specify your api token")
    parser.add_argument("-o","--orgid", type=str, help="Specify org id")
    parser.add_argument("-x", "--lcpprefix", type=str, help="Specify LCP Prefix")
    parser.add_argument("-f", "--force", type=str, help="Specify true/false whether to force delete. Default: true")
    parser.add_argument("-y", "--yamlaction", type=str, help="Specify either apply or generate. Default: apply")
    parser.add_argument("-m", "--monitortime", type=str, help="Specify time in minutes to monitor deregistration. Default: 5")

    args = parser.parse_args()

    if args.vcenter:
        vc = args.vcenter
    else:
        print("No vcenter specified, exiting. Try --help for more info.")
        exit(1)

    if args.username:
        username = args.username
    else:
        print("No ssh username specified. Assuming root")
        username = "root"

    if args.password:
        password = args.password
    else:
        print("No ssh password specified. Assuming Admin!23")
        password = "Admin!23"



    if args.tmcurl:
        tmc_url = str(args.tmcurl)
        tmc_url = tmc_url.replace("https://","")
        tmc_url = tmc_url.replace("http://", "")
        if tmc_url[-1] == '/':
            tmc_url = tmc_url[:-1]
    else:
        print("No tmc url specified, exiting. Try --help for more info.")
        exit(1)

    if args.apitoken:
        api_token = args.apitoken
    else:
        print("No api token specified, exiting. Try --help for more info.")
        exit(1)


    if args.orgid:
        org_id = args.orgid
    else:
        print("No org id specified, exiting. Try --help for more info.")
        exit(1)

    if args.lcpprefix:
        lcp_prefix = args.lcpprefix
        lcp_prefix = lcp_prefix.lower()
    else:
        print("No LCP Prefix specified, exiting. Try --help for more info.")
        exit(1)

    if args.force:
        force = args.force
    else:
        print("No force param specified. Assuming true.")
        force = "true"

    force = force.lower()
    force_delete = True
    if 'false' in force:
        force_delete = False

    if args.yamlaction:
        yaml_action = str(args.yamlaction).lower()
    else:
        print("No yaml action specified. Assuming apply")
        yaml_action = "apply"

    if args.monitortime:
        monitor_time_in_min = int(args.monitortime)
    else:
        print("No monitor time specified. Assuming 5 min.")
        monitor_time_in_min = 5

    workflow(vc, username, password, tmc_url, api_token, org_id, lcp_prefix, monitor_time_in_min, yaml_action,
             force_delete)