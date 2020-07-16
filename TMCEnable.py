# Author: ybendre, jijumonv, jparappurath
# Test: tmc_handler
# This is TMC Wprlflow

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
                cmd1 = 'curl -k -X GET "https://10.199.56.1/LI/tmc_registration_template.yaml" -o /root/tmc_registration_template.yaml'
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
    parser = argparse.ArgumentParser()
    parser.add_argument("-v", "--vcenter", help="Specify vCenter", type=str)
    parser.add_argument("-u", "--username", type=str, help="Specify vCenter ssh username. Default: root")
    parser.add_argument("-p", "--password", type=str, help="Specify vcenter ssh password. Default: Admin!23")

    parser.add_argument("-t", "--tmcurl", help="Specify TMC Base URL.",type=str)
    parser.add_argument("-a","--apitoken", type=str, help="Specify your api token")
    parser.add_argument("-o","--orgid", type=str, help="Specify org id")
    parser.add_argument("-x", "--lcpprefix", type=str, help="Specify LCP Prefix")
    parser.add_argument("-y", "--yamlaction", type=str, help="Specify either apply or generate. Default: apply")

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


tmc_workflow = TMCWorkFlow(vc, username, password, tmc_url, api_token, org_id, lcp_prefix)
tmc_workflow.create_lcp()
tmc_workflow.register_cluster()