import sys
import os
import json
import requests
import argparse
import logging
from dataclasses import dataclass

@dataclass
class Cluster:
    base_url: str
    client_id: str
    client_secret: str
    cluster_id: str

    def generate_api_token(self):
        payload = {"grantType": "app_token", "AppId": self.client_id, "AppSecret": self.client_secret}
        headers = {'content-type': "application/json"}
        url = f"{self.base_url}/api/v1/token"
        try:
            response = requests.post(url=url, json=payload, headers=headers)
            response.raise_for_status()
            response_json = response.json()
            if "accessToken" not in response_json:
                raise SystemExit(f"failed to get access token from response. response body={response_json}")

            return response_json["accessToken"]

        except requests.exceptions.HTTPError as err:
            logging.info(f"failed to get api token. err={err} \n message={err.response.text}" )
            raise SystemExit(err)
        except requests.exceptions.JSONDecodeError as err:
            logging.info(f"failed to decode json response. err={err}")
            raise SystemExit(err)



def write_json_to_file(file_name,json_data):
    with open(file_name, "w", encoding='utf-8') as file:
        json.dump(json_data,file,ensure_ascii=False, indent=4)


if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="Import Runai resources into a new cluster from json files")

    # Add arguments
    parser.add_argument('-url','--base_url', type=str, help='Base url of the cluster (e.g. https://test.run.ai)')
    parser.add_argument('-i','--client_id', type=str, help='Client ID of the application you created in the Runai UI')
    parser.add_argument('-s','--client_secret', type=str, help='Client Secret of the application you created in the Runai UI')
    parser.add_argument('-c','--cluster_id', type=str, help='Cluster ID for the new Runai cluster')
    parser.add_argument('-l', '--log_level', type=str, help="Log level (INFO,WARN,DEBUG,etc)", default="INFO")

    args=parser.parse_args()

    logging.basicConfig(level=args.log_level, format='%(levelname)s: %(message)s\n')
    if args.log_level=="DEBUG":
        logging.getLogger("urllib3").setLevel("WARNING")   #Set Requests level to warning to avoid clogging logs with useless messages

    cluster = Cluster(
        base_url=args.base_url,
        client_id=args.client_id,
        client_secret=args.client_secret,
        cluster_id=args.cluster_id
    )

    token = cluster.generate_api_token()
    headers = {"authorization": f"Bearer {token}", 'content-type': "application/json"}

    ##### NodePools #####
    node_pools_map={}

    response = requests.get(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/node-pools", headers=headers)
    response.raise_for_status()

    node_pools = response.json()

    ##### Departments #####
    old_departments_map={}

    response = requests.get(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/departments", headers=headers)
    response.raise_for_status()
    departments=response.json()

    ##### Projects #####
    response = requests.get(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/projects", headers=headers)
    response.raise_for_status()
    projects=response.json()

    ##### Node Types #####
    #This is only relevant if you have created a Node Type for a given project as part of a Node Affinity rule
    response = requests.get(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/nodetypes", headers=headers)
    response.raise_for_status()
    nodetypes=response.json()

    #### Access Rules ####
    response = requests.get(f"{cluster.base_url}/api/v1/authorization/access-rules", headers=headers)
    response.raise_for_status()
    access_rules = response.json()

    #### Compute Assets ####
    response = requests.get(f"{cluster.base_url}/api/v1/asset/compute", headers=headers)
    response.raise_for_status()
    compute_assets = response.json()

    #### Environment Assets ####
    response = requests.get(f"{cluster.base_url}/api/v1/asset/environment", headers=headers)
    response.raise_for_status()
    environment_assets = response.json()

    #### Workload Template Assets ####
    response = requests.get(f"{cluster.base_url}/api/v1/asset/workload-template", headers=headers)
    response.raise_for_status()
    workload_templates = response.json()

    #### Datasources ####
    response = requests.get(f"{cluster.base_url}/api/v1/asset/datasource", headers=headers)
    response.raise_for_status()
    datasources = response.json()

    #### Policies ####
    response = requests.get(f"{cluster.base_url}/api/v1/policy", headers=headers)
    response.raise_for_status()
    policyList=response.json()

    policies={"entries": []}
    # if "policies" in policyList:
    #     for entry in policyList["policies"]:
    #         type=entry["type"]
    #         scope=entry["meta"]["scope"]
    #         params=f"scope={scope}"
    #         if scope=="project":
    #             params=f"{params}&projectId={entry["meta"]["projectId"]}"
    #         elif scope=="department":
    #             params=f"{params}&departmentId={entry["meta"]["departmentId"]}"
    #         response = requests.get(f"{cluster.base_url}/api/v1/policy/{type}", headers=headers, params=params)
    #         response.raise_for_status()
    #         policies["entries"].append(response.json())
    #     workloadPolicy = policies

    #### Interactive Workloads ####
    response = requests.get(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/workspaces", headers=headers)
    response.raise_for_status()
    iws = response.json()

    #### Training Workloads ####
    response = requests.get(f"{cluster.base_url}/v1/k8s/clusters/{cluster.cluster_id}/trainings", headers=headers)
    response.raise_for_status()
    tws = response.json()

    #### Users ####
    params="filter=runai.is_local:true" #Only get local users, since SSO users will be regenerated once SSO is connected
    response = requests.get(f"{cluster.base_url}/api/v1/users", headers=headers, params=params)
    response.raise_for_status()
    users = response.json()

    #### Credentials ####
    response = requests.get(f"{cluster.base_url}/api/v1/asset/credentials", headers=headers)
    response.raise_for_status()
    credentials = response.json()

    directory_name="2.16_cluster_json"
    try:
        os.mkdir(directory_name)
        logging.info(f"Directory '{directory_name}' created successfully.")
    except FileExistsError:
        logging.info(f"Directory '{directory_name}' already exists.")

    logging.info("Writing resources to files")
    logging.debug(f"Node Pools: {node_pools}")
    write_json_to_file(f"{directory_name}/node_pool.json",node_pools)
    logging.debug(f"Departments: {departments}")
    write_json_to_file(f"{directory_name}/department.json",departments)
    logging.debug(f"Projects: {projects}")
    write_json_to_file(f"{directory_name}/project.json",projects)
    logging.debug(f"Node Types: {nodetypes}")
    write_json_to_file(f"{directory_name}/nodetypes.json",nodetypes)
    logging.debug(f"Access Rules: {access_rules}")
    write_json_to_file(f"{directory_name}/access_rule.json",access_rules)
    logging.debug(f"Compute Assets: {compute_assets}")
    write_json_to_file(f"{directory_name}/compute.json",compute_assets)
    logging.debug(f"Environment Assets: {environment_assets}")
    write_json_to_file(f"{directory_name}/environment.json",environment_assets)
    logging.debug(f"Workload Templates: {workload_templates}")
    write_json_to_file(f"{directory_name}/workload-template.json",workload_templates)
    logging.debug(f"Datasources: {datasources}")
    write_json_to_file(f"{directory_name}/datasource.json",datasources)
    logging.debug(f"Policies: {policies}")
    write_json_to_file(f"{directory_name}/policy.json",policies)
    logging.debug(f"Interactive Workloads: {iws}")
    write_json_to_file(f"{directory_name}/iw.json",iws)
    logging.debug(f"Training Workloads: {tws}")
    write_json_to_file(f"{directory_name}/tw.json",tws)
    logging.debug(f"Local Users: {users}")
    write_json_to_file(f"{directory_name}/users.json",users)
    logging.debug(f"Credentials: {credentials}")
    write_json_to_file(f"{directory_name}/credentials.json",credentials)