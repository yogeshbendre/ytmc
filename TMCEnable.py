# Author: ybendre, jijumonv, jparappurath
# Test: tmc_enabler
# This is TMC Enable Workflow

import json
import json
import argparse
from TMCHandler import TMC
from WCPFetcher import WCPFetcher
import time

class TMCWorkFlow:

    def __init__(self, vc, username, password, tmc_url, api_token, org_id, lcp_prefix):
        self.vc = vc
        self.username = username
        self.password = password
        self.tmc_url = tmc_url
        self.api_token = api_token
        self.org_id = org_id
        self.lcp_prefix = lcp_prefix
        self.tmc_handler = TMC(self.tmc_url, self.api_token, self.org_id)
        self.wcp_fetcher = WCPFetcher(self.vc, self.username, self.password)
        self.wcp_info = self.wcp_fetcher.wcp_info
        print("WCP Clusters: ")
        print(self.wcp_info)
        print("Initialized successfully")

    def create_lcp(self):
        for w in self.wcp_info:
            print("Cluster: "+w)
            try:
                print("Creating LCP for "+self.wcp_info[w]["IP"])
                print("")
                lcp_name = lcp_prefix + "-vc-" +self.vc.replace(".","-") + "-w-" + self.wcp_info[w]["IP"].replace(".","-") + "lcp"
                myinfo = self.tmc_handler.create_local_control_plane(lcp_name)
                self.wcp_info[w]["lcp"] = myinfo
                self.wcp_info[w]["lcp_name"] = lcp_name
                print("Completed")
            except Exception as e:
                print(str(e))

    def register_cluster(self):
        for w in self.wcp_info:
            print("Cluster: "+w)
            try:
                print("Registering for " + self.wcp_info[w]["IP"])
                print("Get Domain: ")
                domain = w.split(":")[0].split("domain-")[1]
                print(domain)
                print("Registraion Link: ")
                reg_link = self.wcp_info[w]["lcp"]["localcontrolplane"]["status"]["registrationUrl"]
                print(reg_link)
                cmd1 = 'curl -k -X GET "https://raw.githubusercontent.com/yogeshbendre/ytmc/master/tmc_registration_template.yaml" -o /root/tmc_registration_template.yaml'
                self.wcp_fetcher.run_command_on_wcp(w,cmd1)
                time.sleep(1)
                reg_link = reg_link.replace("/","\/").replace("?","\?").replace("&","\&")
                cmd2 = "cat /root/tmc_registration_template.yaml | sed 's/<namespace>/svc-tmc-"+domain+"/g' | sed 's/<registration_link>/"+reg_link+"/g' > /root/tmc_register.yaml"
                self.wcp_fetcher.run_command_on_wcp(w,cmd2)
                time.sleep(1)
                print("Generated YAML for TMC Registration")
                cmd3 = "cat  /root/tmc_register.yaml"
                self.wcp_fetcher.run_command_on_wcp(w, cmd3)
                time.sleep(1)
                if yaml_action == 'apply':
                    cmd4 = "kubectl apply -f  /root/tmc_register.yaml"
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



    def monitor_registration(self, monitor_time_in_min = 5):
        print("Monitoring registration for "+str(monitor_time_in_min)+" minutes...")
        t = 0
        areAllHealthy = True
        healthStates = {}
        while t <= monitor_time_in_min:
            areAllHealthy = True
            for w in self.wcp_info:
                try:
                    print("Check health of "+self.wcp_info[w]["lcp_name"])
                    myhealth = self.is_lcp_healthy(self.wcp_info[w]["lcp_name"])
                    areAllHealthy = areAllHealthy and myhealth
                    healthStates[self.wcp_info[w]["lcp_name"]] = myhealth
                except Exception as e:
                    healthStates[self.wcp_info[w]["lcp_name"]] = False
            if(areAllHealthy):
                print("All the control planes are in healthy states.")
                for lcp in healthStates.keys():
                    print("LCP: "+lcp+" Healthy: "+str(healthStates[lcp]))
                break
            else:
                print("Some LCP are still not healthy. Sleeping for 1 min. Remaining Time: "+str(monitor_time_in_min-t)+" min")
                time.sleep(60)
                t = t + 1

        if(areAllHealthy):
            return True
        print("Monitoring Time Out and still few LCPs are not healthy.")
        for lcp in healthStates.keys():
            print("LCP: " + lcp + " Healthy: " + str(healthStates[lcp]))
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
    parser.add_argument("-y", "--yamlaction", type=str, help="Specify either apply or generate. Default: apply")
    parser.add_argument("-m", "--monitortime", type=str, help="Specify time in minutes to monitor registration. Default: 5")

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

    if args.yamlaction:
        yaml_action = args.yamlaction
    else:
        print("No yaml action specified. Assuming apply")
        yaml_action = "apply"

    if args.monitortime:
        monitor_time_in_min = int(args.monitortime)
    else:
        print("No monitor time specified. Assuming 5 min.")
        monitor_time_in_min = 5


tmc_workflow = TMCWorkFlow(vc, username, password, tmc_url, api_token, org_id, lcp_prefix)
tmc_workflow.create_lcp()
tmc_workflow.register_cluster()
tmc_workflow.monitor_registration(monitor_time_in_min)