import sys
import os
import json
import requests
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
            print(f"failed to get api token. err={err} \n message={err.response.text}" )
            raise SystemExit(err)
        except requests.exceptions.JSONDecodeError as err:
            print(f"failed to decode json response. err={err}")
            raise SystemExit(err)



def write_json_to_file(file_name,json_data):
    with open(file_name, "w", encoding='utf-8') as file:
        json.dump(json_data,file,ensure_ascii=False, indent=4)


if __name__ == "__main__":

    cluster = Cluster(
        base_url="https://cs-bgottfri-jhu-2-16.runailabs-cs.com",
        client_id="migration",
        client_secret="dpwReDT0hHmNk9Qn5Q1r9zNEhc9OEGAH",
        cluster_id="e0a9164c-4ea3-46e1-9af1-23cc1c2f2949"
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
    for entry in policyList["policies"]:
        type=entry["type"]
        scope=entry["meta"]["scope"]
        params=f"scope={scope}"
        if scope=="project":
            params=f"{params}&projectId={entry["meta"]["projectId"]}"
        elif scope=="department":
            params=f"{params}&departmentId={entry["meta"]["departmentId"]}"
        response = requests.get(f"{cluster.base_url}/api/v1/policy/{type}", headers=headers, params=params)
        response.raise_for_status()
        policies["entries"].append(response.json())
    workloadPolicy = policies

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

    directory_name="2.16_cluster_json"
    try:
        os.mkdir(directory_name)
        print(f"Directory '{directory_name}' created successfully.")
    except FileExistsError:
        print(f"Directory '{directory_name}' already exists.")

    print(f"Node Pools: {node_pools}")
    write_json_to_file(f"{directory_name}/node_pool.json",node_pools)
    print(f"Departments: {departments}")
    write_json_to_file(f"{directory_name}/department.json",departments)
    print(f"Projects: {projects}")
    write_json_to_file(f"{directory_name}/project.json",projects)
    print(f"Access Rules: {access_rules}")
    write_json_to_file(f"{directory_name}/access_rule.json",access_rules)
    print(f"Compute Assets: {compute_assets}")
    write_json_to_file(f"{directory_name}/compute.json",compute_assets)
    print(f"Environment Assets: {environment_assets}")
    write_json_to_file(f"{directory_name}/environment.json",environment_assets)
    print(f"Workload Templates: {workload_templates}")
    write_json_to_file(f"{directory_name}/workload-template.json",workload_templates)
    print(f"Datasources: {datasources}")
    write_json_to_file(f"{directory_name}/datasource.json",datasources)
    print(f"Policies: {policies}")
    write_json_to_file(f"{directory_name}/policy.json",policies)
    print(f"Interactive Workloads: {iws}")
    write_json_to_file(f"{directory_name}/iw.json",iws)
    print(f"Training Workloads: {tws}")
    write_json_to_file(f"{directory_name}/tw.json",tws)
    print(f"Local Users: {users}")
    write_json_to_file(f"{directory_name}/users.json",users)