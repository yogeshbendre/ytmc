# Author: ybendre, jijumonv, jparappurath
# Test: tmc_handler
# This is TMC Helper Class

import json
import os
import requests
from requests.packages.urllib3.exceptions import InsecureRequestWarning
import argparse


requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

mysession = requests.Session()
mysession.verify = False

class TMC:

    def __init__(self, tmc_url, api_token, org_id):
        self.tmc_url = tmc_url
        self.api_token = api_token
        self.org_id = org_id
        self.access_token = None
        self.mysession = mysession

        # Function to get the vCenter server session

    def generate_access_token(self):
        try:
            #curl -s -X POST https://console-stg.cloud.vmware.com/csp/gateway/am/api/auth/api-tokens/authorize\?refresh_token\=$CSP_TOKEN
            myurl = "https://console-stg.cloud.vmware.com/csp/gateway/am/api/auth/api-tokens/authorize?refresh_token=" + self.api_token
            myresp = self.mysession.post(myurl)
            print(myresp.text)
            self.access_token = json.loads(myresp.text)["access_token"]
            print("Your Access Token:")
            print(self.access_token)
        except Exception as e:
            print(str(e))



    def create_local_control_plane(self, lcp_name, defaultClusterGroup = "default", k8sprovider = "KUBERNETES_PROVIDER_UNSPECIFIED"):
        self.generate_access_token()
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + self.access_token}
        print(headers)
        body = {"localcontrolplane": {"fullName": {"orgId": str(self.org_id), "name": str(lcp_name)},
                                      "spec": {"kubernetesProvider": k8sprovider,
                                               "defaultClusterGroup": defaultClusterGroup}}}
        url = "https://" + self.tmc_url + "/v1alpha1/localcontrolplanes"
        print("url : " + url)
        print("body : " + str(body))
        resp = self.mysession.post(url, data=json.dumps(body), headers=headers)
        print(resp.status_code)
        print(resp.json())
        return resp.json()

    def delete_local_control_plane(self, lcp_name, force=True):
        #curl -X DELETE \
        #'https://<tmc_url>/v1alpha1/localcontrolplanes/<lcp_name>?fullName.orgId=<org_id>&force=true' \
        #-H 'Authorization: Bearer <auth_token>'
        self.generate_access_token()
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + self.access_token}
        print(headers)
        url = "https://" + self.tmc_url + "/v1alpha1/localcontrolplanes/"+lcp_name+"?fullName.orgId="+self.org_id+"&force=" + str(force).lower()
        print("url : " + url)
        resp = self.mysession.delete(url, headers=headers, timeout=60)
        print(resp.status_code)
        print(resp.json())
        return resp.json()

    def get_local_control_plane(self, lcp_name):
        #curl -X GET \
        #https://<tmc_url>/v1alpha1/localcontrolplanes/<lcp_name> \
        #-H 'Authorization: Bearer <auth_token>'
        self.generate_access_token()
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + self.access_token}
        print(headers)
        url = "https://" + self.tmc_url + "/v1alpha1/localcontrolplanes/" + lcp_name
        print("url : " + url)
        resp = self.mysession.get(url, headers=headers)
        print(resp.status_code)
        print(resp.json())
        return resp

    def list_local_control_planes(self):
        #curl -X GET \
        #https://<tmc_url>/v1alpha1/localcontrolplanes/ \
        #-H 'Authorization: Bearer <auth_token>'
        self.generate_access_token()
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + self.access_token}
        print(headers)
        url = "https://" + self.tmc_url + "/v1alpha1/localcontrolplanes"
        print("url : " + url)
        resp = self.mysession.get(url, headers=headers)
        print(resp.status_code)
        print(resp.json())
        return resp.json()



#Driver code
if __name__ == "__main__":

    tmc_url = None
    api_token = None
    org_id = None

    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--tmcurl", help="Specify TMC Base URL.",type=str)
    parser.add_argument("-a","--apitoken", type=str, help="Specify your api token")
    parser.add_argument("-o","--orgid", type=str, help="Specify org id")

    args = parser.parse_args()

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

    #mytmc = TMC(tmc_url, api_token, org_id)
    #mytmc.create_local_control_plane("mylcpm", defaultClusterGroup='')